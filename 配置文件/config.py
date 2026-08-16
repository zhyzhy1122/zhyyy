"""
配置管理模块
集中管理所有配置项，避免硬编码
"""
import json
import os

# 项目根目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 知识库路径
KB_PATH = os.path.join(BASE_DIR, "../knowledge_base", "pet_shop_docs.jsonl")

# ChromaDB 配置
CHROMA_PATH = os.path.join(BASE_DIR, "../chroma_db")
COLLECTION_NAME = "pet_shop"

# 检索配置
TOP_K = 3

# 模型配置
EMBEDDING_MODEL = "BAAI/bge-m3"
LLM_MODEL = "deepseek-v4-flash"

# API 地址
SILICONFLOW_BASE_URL = "https://api.siliconflow.cn/v1"


def load_config():
    """从 config.json 加载 API 密钥"""
    config_path = os.path.join(BASE_DIR, "config.json")
    with open(config_path, encoding="utf-8") as f:
        config = json.load(f)
    return {
        "siliconflow_api_key": config["siliconflow_api_key"].strip(),
        "deepseek_api_key": config["deepseek_api_key"].strip(),
    }
