from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_deepseek import ChatDeepSeek
from services.vectorstore_service import get_docs_with_scores
import json
from langchain_core.messages import  HumanMessage,AIMessage
from services.database import save_message, get_chat_history, init_db
import os
from langchain_core.tools import tool
from pydantic import  BaseModel,Field
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(BASE_DIR, "配置文件", "config.json")
init_db()
_rag_chain = None

RAG_PROMPT = ChatPromptTemplate.from_messages([
    ("system","你是萌宠之家的AI智能助手，可以访问知识库中的全部内容（包括宠物服务资料，以及用户上传的文档如简历、公司资料等）。请根据提供的参考资料准确回答客户问题：参考资料中有相关信息就直接引用回答；没有就如实告知。不要编造信息。"
),
    ("placeholder","{chat_history}"),
    ("human", "参考资料：\n{context}\n\n用户问题：{question}"),

])
class RAGArgs(BaseModel):
    question:str = Field(description = "要检索文档中的知识库中的问题")

def format_docs(docs):
    return "\n\n".join([doc.page_content for doc in docs])


def get_rag_chain():
    # 定义函数：返回 RAG 生成链；链只负责"拼提示词+生成"，不再碰向量库
    global _rag_chain
    # 声明全局变量：链要缓存，避免每次请求重新构建
    if _rag_chain is not None:
        # 已有缓存
        return _rag_chain
        # 直接返回缓存
    with open(CONFIG_PATH, encoding="utf-8") as f:
        # 打开配置文件（CONFIG_PATH 是模块顶部的绝对路径常量）
        config = json.load(f)
        # 读入配置
    api_key = config["deepseek_api_key"].strip()
    # 取出 API key 并去掉首尾空格
    llm = ChatDeepSeek(
        # 创建大模型客户端
        api_key=api_key,
        # 传 API key
        model="deepseek-v4-flash",
        # 模型名
    )
    rag_chain = (
        # 组装 LCEL 链（注意：原来这里创建 vectorstore/retriever 的代码已删除）
        {
            "context": lambda x: format_docs(x["docs"]),
            # ★ 修复：lambda 从输入取 docs 并转成文本；itemgetter 不支持 | 管道，lambda 是标准写法
            "question": lambda x: x["question"],
            # 问题原样传入
            "chat_history": lambda x: x["chat_history"],
            # 历史原样传入
        }
        | RAG_PROMPT
        # 拼提示词
        | llm
        # 调大模型
        | StrOutputParser()
        # 输出转纯文本
    )
    _rag_chain = rag_chain
    # 缓存链
    return _rag_chain
    # 返回链


def ask(question: str, session_id: str = "default"):
    # 1. 获取历史消息
    history = get_chat_history(session_id, limit=10)

    # 2. 保存用户问题
    save_message(session_id, "user", question)

    # 3. 把历史转成 LangChain 消息对象
    # LangChain 需要的是 HumanMessage / AIMessage 对象，不是字典

    chat_history = []
    for msg in history:
        if msg["role"] == "user":
            chat_history.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "assistant":
            chat_history.append(AIMessage(content=msg["content"]))


    # 4. 检索知识库，拿文档（第 1 步的函数：带分数检索）
    docs_with_scores = get_docs_with_scores(question)
    # 调用检索：返回 [(文档, 分数), ...]
    docs = [doc for doc, _ in docs_with_scores]
    # 只要文档列表（分数这步用不到，但检索统一走带分数的函数）
    # 5. 调用 chain，传入 question、chat_history 和 docs
    rag_chain = get_rag_chain()
    # 获取生成链（已不再包含检索）
    answer = rag_chain.invoke({
        # 调用链
        "question": question,
        # 问题
        "chat_history": chat_history,
        # 历史
        "docs": docs,
        # ★ 新增：把检索结果传给链（链用 docs 拼 context，不再自己检索）
    })


    # 5. 保存 AI 回答
    save_message(session_id, "assistant", answer)

    return answer


@tool
def query_knowledge_base(question:str)->str:
    """根据用户问题检索知识库并返回生成的答案。
    使用场景：客户询问知识库服务内容、价格信息、维护知识等在知识库中记载的内容。
    服务名请使用店内的规范名称（猫咪普通洗护、猫咪深度洗护、药浴、剪指甲、体内驱虫）。"""

    docs_with_scores = get_docs_with_scores(question)
    docs = [doc for doc, _ in docs_with_scores]
    rag_chain = get_rag_chain()
    answer = rag_chain.invoke(
        {
            "question":question,
            "chat_history":[],
            "docs":docs,
        }
    )
    return answer

if __name__ == '__main__':
    while True:
        question = input("请输入你的问题或者输入quit离开：")
        if question == "quit":
            break
        print(ask(question))


