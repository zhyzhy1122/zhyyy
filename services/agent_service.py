from langgraph.graph import StateGraph, START, END
from typing_extensions import TypedDict
from langchain_deepseek import ChatDeepSeek
from langchain_core.messages import HumanMessage, AIMessage
from services.rag_service import get_rag_chain
from services.vectorstore_service import get_docs_with_scores
from services.database import save_message, get_chat_history, init_db,update_last_message
import json
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(BASE_DIR, "配置文件", "config.json")
init_db()
_llm = None

def get_llm():
    global _llm
    if _llm is not None:
        return _llm
    with open(CONFIG_PATH, encoding="utf-8") as f:
        config = json.load(f)
    api_key = config["deepseek_api_key"].strip()
    _llm = ChatDeepSeek(api_key=api_key, model="deepseek-v4-flash")
    return _llm

class AgentState(TypedDict):
    question: str
    chat_history: list
    intent: str
    answer: str
    sources:list
    rewritten_question:str

def route_node(state:AgentState)->AgentState:
    question = state["question"]
    chat_history = state["chat_history"]
    llm = get_llm()
    route_prompt = f"""请判断用户问题的意图，只回复一个词：
    - 如果问题需要查询知识库（宠物店的服务、价格、套餐、预约、养护知识，以及用户上传的文档如简历、PDF、Word、TXT 等），回复：rag

    - 如果是闲聊、感谢、问候、告别（如"谢谢"、"你好"、"再见"）或者与上传的知识库无关的话题，回复：chat
    用户问题：{question}
    历史对话：{chat_history}
    只回复 rag 或 chat，不要回复其他内容。"""
    response = llm.invoke(route_prompt)
    intent = response.content.strip().lower()

    if "rag" in intent:
        intent = "rag"
    else:
        intent = "chat"
    return {"intent":intent}
def rewrite_node(state: AgentState) -> AgentState:
    # 定义函数：查询改写节点；把依赖上下文的模糊问题改写成完整独立问题
    """查询改写：结合对话历史补全问题，提升检索质量"""
    # 文档字符串
    question = state["question"]
    # 原始问题
    chat_history = state["chat_history"]
    # 对话历史
    llm = get_llm()
    # 复用 LLM 单例
    history_text = "\n".join(
        # 消息对象转纯文本（提示词不能直接拼对象）
        f"{'用户' if isinstance(m, HumanMessage) else 'AI'}: {m.content}"
        # 每条：角色+内容
        for m in chat_history[-6:]
        # 只取最近 6 条
    )
    rewrite_prompt = f"""请根据对话历史，把用户当前的问题改写成一句完整、独立的问题，用于知识库检索。
    要求：
    - 补全指代词（这个、它、那）和省略的内容
    - 不要编造历史里没有的信息
    - 只输出改写后的问题，不要解释
    对话历史：
    {history_text}
    用户当前问题：{question}
    改写后的问题："""
    # 改写提示词
    response = llm.invoke(rewrite_prompt)
    # 调 LLM
    rewritten = response.content.strip()
    # 取结果去空格
    return {"rewritten_question": rewritten}
    # 写回状态（rag_node 用它检索）

def rag_node(state:AgentState)->AgentState:
    # 定义函数：LangGraph 的 RAG 生成节点；入参 state（状态字典），返回更新后的状态
    question = state["question"]
    # 从状态字典取问题
    chat_history = state["chat_history"]
    search_question = state.get("rewritten_question") or question
    # 从状态字典取历史
    docs_with_scores = get_docs_with_scores(search_question)
    # 检索知识库（第 1 步的函数）：返回 [(文档, 分数), ...]
    docs = [doc for doc, _ in docs_with_scores]
    # 提取文档列表（分数这里不用）
    sources = [
        {
            "doc_id":doc.metadata.get("doc_id"),
            "title":doc.metadata.get("title",""),
            "snippet":doc.page_content[:100],

        }
        for doc, _ in docs_with_scores
    ]
    rag_chain = get_rag_chain()
    # 获取生成链（已不含检索）
    answer = rag_chain.invoke(
        # 调用链生成回答
        {"question": question,
         # 问题
         "chat_history": chat_history,
         # 历史
         "docs": docs,
         # ★ 新增：传检索结果（链用它拼 context）
         }
    )
    return {"answer":answer,"source":sources}
    # 把回答写回状态字典（LangGraph 会传给 END）

def chat_node(state:AgentState)->AgentState:
    question = state["question"]
    chat_history = state["chat_history"]
    llm = get_llm()
    chat_prompt = f"""你是萌宠之家的客服AI智能助手。请直接回应用户，不需要检索知识库。

    历史对话：{chat_history}
    用户问题：{question}
    请简洁回答。"""
    response = llm.invoke(chat_prompt)
    return {"answer": response.content}

def route_decision(state:AgentState)->str:
    if state["intent"] =="rag":
        return "rag_node"
    else:
        return "chat_node"

def get_agent():
    graph = StateGraph(AgentState)
    graph.add_node("route_node",route_node)
    graph.add_node("rewrite_node",rewrite_node)
    graph.add_node("rag_node",rag_node)
    graph.add_node("chat_node",chat_node)
    graph.add_edge(START,"route_node")
    graph.add_conditional_edges(
        "route_node",
        route_decision,
    {"rag_node":"rewrite_node",
     "chat_node":"chat_node"
    }
    )
    graph.add_edge("rewrite_node","rag_node")
    graph.add_edge("rag_node",END)
    graph.add_edge("chat_node",END)
    return graph.compile()
_agent = None
def get_agent_instance():
    global _agent
    if _agent is not None:
        return _agent
    _agent = get_agent()
    return _agent

def ask_agent(question:str,session_id:str = "default"):
    history = get_chat_history(session_id,limit=10)
    save_message(session_id,"user",question)
    chat_history = []
    for msg in history:
        if msg["role"] == "user":
            chat_history.append(HumanMessage(content=msg["content"]))
        elif msg["role"]=="assistant":
            chat_history.append(AIMessage(content=msg["content"]))
    agent = get_agent_instance()
    result = agent.invoke({
        "question":question,
        "chat_history":chat_history,
    })
    answer = result["answer"]
    save_message(session_id,"assistant",answer)
    return answer
def ask_agent_stream(question: str, session_id: str = "default", show_sources: bool = True):
    # 定义函数：走 LangGraph 图的流式问答；产出 str（文本块）或 dict（source 事件）
    history = get_chat_history(session_id, limit=10)
    # 取历史
    save_message(session_id, "user", question)
    # 存用户消息
    save_message(session_id, "assistant", "")
    # 存空回答（断流兜底用）
    chat_history = []
    # 准备 LangChain 消息列表
    for msg in history:
        # 遍历历史
        if msg["role"] == "user":
            # 用户消息
            chat_history.append(HumanMessage(content=msg["content"]))
            # 转成 HumanMessage
        elif msg["role"] == "assistant":
            # AI 消息
            chat_history.append(AIMessage(content=msg["content"]))
            # 转成 AIMessage
    agent = get_agent_instance()
    # ★ 获取编译好的图（走完整图，加节点自动生效）
    full_answer = ""
    # 累积完整回答（finally 回填用）
    try:
        # 捕获异常/断流，保证 finally 执行
        for chunk in agent.stream(
            # ★ 核心改动：用图的流式（替代手动 route_node + 手动分支）
            {"question": question, "chat_history": chat_history},
            # 图输入（sources 由节点返回，不用传）
            stream_mode=["messages", "updates"],
            # ★ 双模式：messages=token流，updates=节点状态
        ):
            mode, data = chunk
            # 解包：chunk 是 (模式名, 数据) 元组
            if mode == "messages":
                # 是 token 流
                msg_chunk, metadata = data
                # 解包：消息块 + 元数据
                node = metadata.get("langgraph_node")
                # 取当前是哪个节点在产出
                if node in ("rag_node", "chat_node") and msg_chunk.content:
                    # 只取生成节点的 token（过滤 route_node 的意图判断 token）
                    full_answer += msg_chunk.content
                    # 累积
                    yield msg_chunk.content
                    # 输出文本块
            else:
                # 是节点状态更新（updates 模式）
                updates = data
                # 形如 {"rag_node": {"answer": "...", "sources": [...]}}
                if "rag_node" in updates and show_sources:
                    # rag 节点完成且有来源、开关打开
                    src = updates["rag_node"].get("sources") or []
                    # 取来源列表
                    if src:
                        # 非空才发
                        yield {"type": "source", "sources": src}
                        # 发 source 事件（前端存起来渲染来源卡片）
    finally:
        # 无论正常结束还是断开都执行
        if full_answer:
            # 有内容才回填
            update_last_message(session_id, "assistant", full_answer)
            # 回填完整回答



if __name__ == "__main__":
    while True:
        question = input("请输入你的问题或者输入quit离开：")
        if question == "quit":
            break
        print(ask_agent(question))

