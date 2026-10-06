import json
from langchain_chroma import Chroma
from langchain_deepseek import ChatDeepSeek
from openai import api_key, responses

from step2_embed import get_embeddings
COLLECTION_NAME ="pet_shop"
CHROMA_PATH = "../chroma_db"
TOP_k = 3
def get_vectorstore():
    embeddings = get_embeddings()
    vectorstore = Chroma(
        persist_directory=CHROMA_PATH,
        embedding_function=embeddings,
        collection_name=COLLECTION_NAME,
    )
    return vectorstore

def retrieve(vectorstore,query):
    retrieve =vectorstore.as_retiever(
        search_type="similarity",
        search_kwargs = {"k":TOP_k}

    )
    docs = retrieve.invoke(query)

    return docs
def generate_answer(query,docs):
    with open("../config.json", encoding="utf-8")as f:
        config = json.load(f)
    api_key = config["deepseek_api_key"].strip()
    context = "\n\n.join([doc,page_content for doc in docs])"
    llm = ChatDeepSeek(
        api_key = api_key,
        model="deepseek-v4-flash",
        temperature = 0.3
    )
    messages = [
        ("system","你是萌宠之家的客服ai智能助手，请根据检索到的内容准确回答客户问题"),
        ("human",f"参考资料：\n{context}\n\n用户问题：{query}"),

    ]
    responses = llm.invoke(messages)
    return responses.content

if __name__ == "__main__":
    vectorstore = get_vectorstore()
    # 启动时连接一次数据库，避免每次提问都重新连接

    print("萌宠之家智能客服已启动，输入 quit 退出")
    while True:
        query = input("\n请输入你的问题：")
        # 等用户输入

        if query.strip().lower() == "quit":
        # 输入 quit 退出
            break

        docs = retrieve(vectorstore, query)
        # 检索

        print(f"\n检索到 {len(docs)} 个相关片段：")
        for doc in docs:
            print(f"  - {doc.metadata['title']}")
            # 打印命中片段的标题，方便你肉眼检查检索得准不准

        answer = generate_answer(query, docs)
        # 生成回答

        print(f"\n回答：{answer}")