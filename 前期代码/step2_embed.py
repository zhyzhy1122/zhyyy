import json
from langchain_siliconflow import SiliconFlowEmbeddings



CONFIG_PATH = "../配置文件/config.json"  # 项目根目录下的 config.json
API_URL = "https://api.siliconflow.cn/v1/embeddings"
MODEL_NAME = "BAAI/bge-m3"


# def load_config(path):
#     """读取 config.json，返回整个配置字典"""
#     # 你的代码
#     with open("D:/python/宠物店rag项目（后续langchain加langgraph）/config.json",encoding="utf-8")as f:
#        config = json.load(f)
#     return config
#
#
#
# def embed_texts(texts):
#     config = load_config(CONFIG_PATH)
#     api_key = config["siliconflow_api_key"].strip()
#
#     headers = {
#         "Authorization": f"Bearer {api_key}",
#         "Content-Type": "application/json"
#     }
#
#     payload = {
#         "model": MODEL_NAME,
#         "input": texts,
#         "encoding_format": "float"
#     }
#
#     response = requests.post(API_URL, json=payload, headers=headers)
#     response.raise_for_status()
#
#     data = response.json()
#     embeddings = [item["embedding"] for item in data["data"]]
#     return embeddings

def get_embeddings():
    with open("../配置文件/config.json", encoding="utf-8")as f:
        config = json.load(f)
        api_key = config["siliconflow_api_key"].strip()
        return SiliconFlowEmbeddings(
            siliconflow_api_key=api_key,
            model="BAAI/bge-m3",
            base_url = "https://api.siliconflow.cn/v1",
        )


if __name__ == "__main__":
    embeddings = get_embeddings()

    # 批量测试
    vectors = embeddings.embed_documents(["猫咪多久洗一次澡", "宠物寄养的价格怎么算"])
    print(f"共 {len(vectors)} 个向量")
    print(f"每个向量维度: {len(vectors[0])}")

    # 单条测试
    single = embeddings.embed_query("测试文本")
    print(f"单条向量维度: {len(single)}")