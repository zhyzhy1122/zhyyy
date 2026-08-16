from langchain_chroma import Chroma
from 前期代码.step1_load import load_document,convert_to_documents,split_docs,KB_PATH
from 前期代码.step2_embed import get_embeddings
def build_vectorstore():
    docs = load_document(KB_PATH)
    lc_docs = convert_to_documents(docs)
    chunks = split_docs(lc_docs)
    embeddings =get_embeddings()

    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory="./chroma_db",
        collection_name="pet_shop"
    )
    print(f"成功存入{len(chunks)}记录")
    return vectorstore

if __name__ == '__main__':
    build_vectorstore()
