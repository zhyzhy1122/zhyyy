import json
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter


KB_PATH = r"D:\python\宠物店rag项目（后续langchain加langgraph）\knowledge_base\pet_shop_docs.jsonl"

def load_document(path):
    docs = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            l = json.loads(line)
            docs.append(l)
    return docs

def convert_to_documents(docs):
    return [
        Document(
            page_content=doc["content"],
            metadata={
                "doc_id": doc["id"],
                "title": doc["title"],
                **doc["metadata"]
            }
        )
        for doc in docs
    ]

def split_docs(documents):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=400,
        chunk_overlap=80,
        separators=["\n\n", "\n", "。", "！", "？", "；", "，", " ", ""],
    )

    return splitter.split_documents(documents)