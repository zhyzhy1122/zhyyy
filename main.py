from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from services.agent_service import ask_agent,ask_agent_stream
import json
from pydantic import BaseModel
from typing import Literal



from services.database import (
    save_document,get_document,list_documents,update_document,delete_document,
    list_sessions,get_session_messages,message_exists,save_feedback,
    delete_session,rename_session,set_session_pinned,
)

from services.vectorstore_service import (
    add_document_to_vectorstore,
    delete_document_from_vectorstore,
    update_document_in_vectorstore,
)
from services.file_parser import extract_text
class DocumentCreate(BaseModel):
    title: str
    content: str
    source: str = "手动录入"

class DocumentUpdate(BaseModel):
    title: str
    content: str

class FeedbackCreate(BaseModel):
    # 定义反馈请求的 JSON 结构，FastAPI 自动解析和校验
    message_id: int
    # 被反馈的消息ID（来自接口2），必填
    rating: Literal[1, -1]
    # 评价：只允许 1 或 -1，填别的值自动 422
    comment: str = ""
    # 补充意见：可选，缺省空字符串

class SessionRename(BaseModel):
    # 会话重命名请求体
    title: str
    # 新标题

class SessionPin(BaseModel):
    # 会话置顶请求体
    pinned: bool
    # 是否置顶


app = FastAPI(title="萌宠之家 RAG 系统", version="1.0.0")
app.add_middleware(
    CORSMiddleware,# type: ignore
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"message": "萌宠之家 RAG 系统已启动"}

# @app.post("/ask")
# def ask_question(question: str,session_id:str = "default"):
#     """
#     问答接口：传入问题，返回回答
#     """
#     try:
#         answer = ask_agent(question,session_id)
#         return {"question": question, "answer": answer}
#     except Exception as e:
#         return {"error": str(e)}
@app.post("/ask/stream")
def ask_question_stream(question: str, session_id: str = "default"):
    # 路由：流式问答接口
    # 参数：question（问题，必填）、session_id（会话ID，可缺省）
    # 说明：原 show_sources 参数及其 source 事件逻辑已移除——
    #       业务层(ask_agent_stream)现在只产出字符串文本块，不产出字典，故统一按文本块包装
    def stream_generator():
        # 定义 SSE 生成器：把业务层产出的每个文本块包装成 SSE 的 data 行
        try:
            # 捕获异常，保证断开时能发错误事件、结尾能发 [DONE]
            for event in ask_agent_stream(question, session_id):
                # 遍历事件流：ask_agent_stream 逐个 yield 字符串文本块
                data = json.dumps({"content": event}, ensure_ascii=False)
                # 统一包成 {"content": ...} 格式（前端解析器已兼容）
                yield f"data: {data}\n\n"
                # 按 SSE 协议输出：data：前缀 + JSON + 空行
        except Exception as e:
            # 出错时
            error_data = json.dumps({"error": str(e)}, ensure_ascii=False)
            # 错误信息转 JSON
            yield f"data: {error_data}\n\n"
            # 发错误事件
        yield "data: [DONE]\n\n"
        # 结束标记（前端靠它停止解析）
    return StreamingResponse(stream_generator(), media_type="text/event-stream")
    # 返回 SSE 响应


@app.get("/documents")
def api_list_document():
    return list_documents()

@app.get("/documents/{doc_id}")
def api_get_document(doc_id:int):
    doc = get_document(doc_id)
    if doc is None:
        return {"error":"文档不存在"}
    return doc
@app.post("/documents")
def api_create_document(doc: DocumentCreate):
    doc_id = save_document(doc.title, doc.content, doc.source)
    add_document_to_vectorstore(doc_id, doc.title, doc.content)
    return {"message": "文档已添加", "doc_id": doc_id}

@app.post("/documents/upload")
async def api_upload_document(file: UploadFile = File(...), source: str = Form("文件上传")):
    """上传文件（PDF/Word/TXT）作为知识库文档；解析文本后走和手打一致的入库流程"""
    content = await file.read()
    # 读取上传的文件字节（await：UploadFile 是异步的）
    if len(content) > 10 * 1024 * 1024:
        # 10MB 上限
        return {"error": "文件超过 10MB 限制"}
    try:
        text = extract_text(file.filename, content)
        # 按扩展名解析成纯文本（pdf/docx/txt）
    except ValueError as e:
        # 不支持的文件类型
        return {"error": str(e)}
    if not text.strip():
        # 提取不到文字（如扫描图片型 PDF）
        return {"error": "未能从文件中提取到文本（可能是扫描件图片型 PDF）"}
    title = file.filename
    # 文档标题默认用文件名
    doc_id = save_document(title, text, source)
    # 存 SQLite（复用现有函数）
    add_document_to_vectorstore(doc_id, title, text)
    # 切分+向量化入库（复用现有函数）
    return {"message": "文档已添加", "doc_id": doc_id, "title": title, "char_count": len(text)}
    # 返回结果（char_count 给前端展示提取了多少字）

@app.put("/documents/{doc_id}")
def api_update_document(doc_id: int, doc: DocumentUpdate):
    if get_document(doc_id) is None:
        return {"error": "文档不存在"}
    update_document(doc_id, doc.title, doc.content)
    update_document_in_vectorstore(doc_id, doc.title, doc.content)
    return {"message": "文档已更新", "doc_id": doc_id}

@app.delete("/documents/{doc_id}")
def api_delete_document(doc_id:int):
    if get_document(doc_id) is None:
        return {"error":"文档不存在"}
    delete_document(doc_id)
    delete_document_from_vectorstore(doc_id)
    return {"message":"文档已删除","doc_id":doc_id}

@app.get("/api/sessions")
def api_list_sessions():
    """会话列表：前端侧边栏使用"""
    return {"sessions": list_sessions()}

@app.get("/api/sessions/{session_id}/messages")
def api_get_session_messages(session_id: str):
    """获取某会话的全部聊天记录"""
    return {"messages": get_session_messages(session_id)}

@app.put("/api/sessions/{session_id}")
def api_rename_session(session_id: str, body: SessionRename):
    """重命名会话"""
    rename_session(session_id, body.title)
    return {"message": "会话已重命名"}

@app.delete("/api/sessions/{session_id}")
def api_delete_session(session_id: str):
    """删除会话（含全部消息）"""
    delete_session(session_id)
    return {"message": "会话已删除"}

@app.put("/api/sessions/{session_id}/pin")
def api_pin_session(session_id: str, body: SessionPin):
    """置顶/取消置顶会话"""
    set_session_pinned(session_id, body.pinned)
    return {"message": "已置顶" if body.pinned else "已取消置顶"}

@app.post("/api/feedback")
# 注册路由：POST + JSON body
def api_feedback(fb: FeedbackCreate):
    # 函数：入参 fb（FeedbackCreate 对象，FastAPI 自动从请求体解析）
    if not message_exists(fb.message_id):
        # 校验：消息不存在就给错误提示（商业严谨性，防止前端乱传ID）
        return {"error": "消息不存在"}
        # 返回错误
    feedback_id = save_feedback(fb.message_id, fb.rating, fb.comment)
    # 写反馈；拿到新记录ID
    return {"message": "反馈已保存", "feedback_id": feedback_id}
    # 成功响应




if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)