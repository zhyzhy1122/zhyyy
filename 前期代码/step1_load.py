import json
import os
from langchain_core.documents import Document
from langchain_text_splitters import CharacterTextSplitter
KB_PATH = r"/knowledge_base/pet_shop_docs.jsonl"

def load_document(path):
    docs = []
    with open(r"/knowledge_base/pet_shop_docs.jsonl", encoding="utf-8", )as f:
        for line in f:
            l = json.loads(line)
            docs.append(l)
        return docs



# def chunk_text(text,chunk_size = 400,overlap = 80):
#     chunks = []
#     start = 0
#     while start < len(text):
#         end = start+chunk_size
#         chunk = text[start:end]
#         chunks.append(chunk)
#         start = start + (chunk_size - overlap)
#
#     return chunks
# def chunk_all_documents(docs,chunk_size = 400,overlap= 80):
#     all_chunks = []
#     for doc in docs:
#         chunks = chunk_text(doc["content"],chunk_size = 400,overlap = 80)
#         for chunk_index ,chunk_textstr in enumerate(chunks):
#             chunk_dict = {
#                 "doc_id":doc["id"],
#                 "title":doc["title"],
#                 "chunk_index":chunk_index,
#                 "text":chunk_textstr,
#                 "metadata":doc["metadata"],
#
#             }
#             all_chunks.append(chunk_dict)
#
#     return all_chunks
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
    splitter = CharacterTextSplitter(
        chunk_size=400,
        chunk_overlap=80,
        separator="",
    )
    return splitter.split_documents(documents)

if __name__ == "__main__":
    docs = load_document(KB_PATH)
    lc_docs = convert_to_documents(docs)
    chunks = split_docs(lc_docs)
    print(f"加载完成：{len(lc_docs)} 篇文档")
    print(f"切分完成：共 {len(chunks)} 个 chunk")
    # 打印示例 chunk 看看效果
    print(chunks[0])





