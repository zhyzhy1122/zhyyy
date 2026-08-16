import json
import os
from langchain_siliconflow import SiliconFlowEmbeddings
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(BASE_DIR, "配置文件", "config.json")
def get_embeddings():
    with open(CONFIG_PATH, encoding="utf-8") as f:
        config = json.load(f)
    api_key = config["siliconflow_api_key"].strip()
    return SiliconFlowEmbeddings(
        siliconflow_api_key=api_key,
        model="BAAI/bge-m3",
        base_url="https://api.siliconflow.cn/v1",
    )