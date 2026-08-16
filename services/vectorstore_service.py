from langchain_chroma import Chroma
from  langchain_core.documents import Document
from services.document_service import load_document, convert_to_documents, split_docs, KB_PATH
from services.embedding_service import get_embeddings


def build_vectorstore():
    docs = load_document(KB_PATH)
    lc_docs = convert_to_documents(docs)
    chunks = split_docs(lc_docs)
    embeddings = get_embeddings()

    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory="./chroma_db",
        collection_name="pet_shop"
    )
    print(f"成功存入 {len(chunks)} 记录")
    return vectorstore


def get_vectorstore():
    embeddings = get_embeddings()
    return Chroma(
        persist_directory="./chroma_db",
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

def get_docs_with_scores(question: str, k: int = 3):
    # 定义函数：入参 question（问题文本）、k（返回几条，默认3）；返回 [(文档, 相似度分数), ...]
    """检索并返回带相似度分数的文档列表 [(Document, score), ...]"""
    # 文档字符串：说明返回格式，调用方靠它知道怎么用
    vectorstore = get_vectorstore()
    # 连接向量库（Chroma），复用已有的连接函数
    docs_with_scores = vectorstore.similarity_search_with_relevance_scores(
        # 检索并带分数：返回 [(Document, score), ...]；retriever.invoke() 不带分数，只有这个方法给
        question,
        # 要检索的问题文本
        k=k,
        # 返回条数，默认 3
    )
    return docs_with_scores
    # 返回 [(文档对象, 分数), ...]；分数越大越相关（约 0~1）

