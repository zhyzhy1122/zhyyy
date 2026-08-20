from langchain_chroma import Chroma
import os
import jieba

from services.document_service import load_document, convert_to_documents, split_docs, KB_PATH
from services.embedding_service import get_embeddings
from langchain_community.retrievers import BM25Retriever
from langchain_classic.retrievers import EnsembleRetriever
from langchain_core.documents import Document

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHROMA_DIR = os.path.join(BASE_DIR, "chroma_db")

def build_vectorstore():
    docs = load_document(KB_PATH)
    lc_docs = convert_to_documents(docs)
    chunks = split_docs(lc_docs)
    embeddings = get_embeddings()

    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=CHROMA_DIR,
        collection_name="pet_shop"
    )
    print(f"成功存入 {len(chunks)} 记录")
    return vectorstore


def get_vectorstore():
    embeddings = get_embeddings()
    return Chroma(
        persist_directory=CHROMA_DIR,
        embedding_function=embeddings,
        collection_name="pet_shop",
    )
def add_document_to_vectorstore(doc_id,title,content):
    """新增文档：切分-向量化-存入chroma"""
    vectorstore = get_vectorstore()
    doc = Document(page_content=content, metadata={"doc_id": doc_id, "title": title})
    chunks = split_docs([doc])
    for chunk in chunks:
        chunk.metadata["doc_id"] = doc_id
    vectorstore.add_documents(chunks)
    print(f"文档{doc_id}已向量化，共{len(chunks)}个chunk")

def delete_document_from_vectorstore(doc_id):
    """删除文档"""
    vectorstore = get_vectorstore()
    vectorstore._collection.delete(where = {"doc_id":doc_id})
    print(f"文档{doc_id}的向量已被删除")

def update_document_in_vectorstore(doc_id,title,content):
    """修改文档，：先删除向量，再加新向量"""
    delete_document_from_vectorstore(doc_id)
    add_document_to_vectorstore(doc_id,title,content)
    print(f"文档{doc_id}已经更新")

_hybrid_retriever = None
def _export_all_chunks():
    vectorstore = get_vectorstore()
    data = vectorstore._collection.get(include=["documents","metadatas"])
    docs = []
    for content,meta in zip(data["documents"],data["metadatas"]):
        docs.append(Document(page_content=content,metadata= meta))
    return docs

def get_hybrid_retriever(k:int=5):
    global _hybrid_retriever
    if _hybrid_retriever is not None:
        return _hybrid_retriever
    chunks = _export_all_chunks()
    vectorstore = get_vectorstore()
    bm25 = BM25Retriever.from_documents(chunks,
                                        k=k,
                                        preprocess_func = lambda t:jieba.lcut(t),
    )
    vector_retriever = vectorstore.as_retriever(search_kwargs= {"k":k})
    _hybrid_retriever = EnsembleRetriever(
        retrievers=[bm25,vector_retriever],
        weights=[0.5,0.5]
    )
    return _hybrid_retriever
def get_docs_with_scores(question: str, k: int = 3):
    # 定义函数：入参 question（问题文本）、k（返回几条，默认3）；返回 [(文档, 相似度分数), ...]
    """检索并返回带相似度分数的文档列表 [(Document, score), ...]"""
    # 文档字符串：说明返回格式，调用方靠它知道怎么用
    vectorstore = get_vectorstore()
    # 连接向量库（Chroma），复用已有的连接函数
    retriever = get_hybrid_retriever(k = k*2)
    docs = retriever.invoke(question)[:k]
    return [(d,1.0 - i*1e-4)for i ,d in enumerate(docs)]
    # 返回 [(文档对象, 分数), ...]；分数越大越相关（约 0~1）

if __name__ == "__main__":
    for doc, score in get_docs_with_scores("猫咪深度洗护包含哪些步骤"):
        print(doc.page_content[:50], "|", doc.metadata)