import os
os.chdir('/app')

from services.database import list_documents
docs = list_documents()
print(f'数据库文档数: {len(docs)}')
for d in docs[-5:]:
    print(f'  ID={d["id"]} | {d["title"]} | 创建:{d["created_at"]}')

print()
print('--- 测试检索 ---')
from services.vectorstore_service import get_docs_with_scores
test_queries = ['宠物店有什么服务', '猫咪洗护', '上传的文档']
for q in test_queries:
    results = get_docs_with_scores(q)
    print(f'\n问题: {q}')
    print(f'找到 {len(results)} 条结果')
    for doc, score in results:
        print(f'  [{score:.3f}] {doc.page_content[:60]}... | doc_id={doc.metadata.get("doc_id")}')
