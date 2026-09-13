"""
检索评测 · 单文件版（评测集已内置，放到项目根目录直接跑）
用法：把本文件覆盖项目根目录的 run_retrieval_eval.py，然后：
    python run_retrieval_eval.py
前提：项目能正常启动（配置文件/config.json 两个 api_key 有效、chroma_db 已构建）
"""
import json
from collections import defaultdict

from services.vectorstore_service import get_vectorstore, get_hybrid_retriever, _export_all_chunks
from langchain_community.retrievers import BM25Retriever
import jieba

K = 3

# ============ 评测集：30 条，全部基于知识库真实文档标题 ============
EVAL_SET = [
    {"question": "猫咪普通洗护多少钱？", "expected_doc": "宠物普通洗护服务"},
    {"question": "深度护理和普通洗护有什么区别？", "expected_doc": "宠物深度护理服务"},
    {"question": "宠物SPA水疗都包含什么项目？", "expected_doc": "宠物SPA水疗服务"},
    {"question": "什么情况下宠物需要做药浴？", "expected_doc": "宠物药浴服务"},
    {"question": "寄养期间一天喂几顿？", "expected_doc": "宠物寄养服务"},
    {"question": "猫咪打疫苗一般几针？", "expected_doc": "疫苗接种服务"},
    {"question": "体内驱虫多久做一次？", "expected_doc": "体内驱虫服务"},
    {"question": "绝育手术前后要注意什么？", "expected_doc": "绝育手术服务"},
    {"question": "洗牙服务怎么做？", "expected_doc": "牙齿清洁与洗牙服务"},
    {"question": "猫咪几个月大可以洗澡？", "expected_doc": "猫咪多大可以洗澡？"},
    {"question": "狗狗打完疫苗几天可以洗澡？", "expected_doc": "狗狗打完疫苗几天可以洗澡？"},
    {"question": "寄养需要自带猫砂吗？", "expected_doc": "寄养需要自带猫砂吗？"},
    {"question": "会员卡可以借给朋友用吗？", "expected_doc": "会员卡可以转借给别人使用吗？"},
    {"question": "节假日洗护寄养会涨价吗？", "expected_doc": "节假日寄养和洗护价格如何？"},
    {"question": "驱虫之后隔多久才能洗澡？", "expected_doc": "驱虫后多久不能洗澡？"},
    {"question": "只洗耳朵不全身洗可以吗？", "expected_doc": "可以只洗耳朵不全身洗吗？"},
    {"question": "想退款怎么操作？", "expected_doc": "退款规则"},
    {"question": "怎么预约到店服务？", "expected_doc": "预约流程说明"},
    {"question": "金毛平时应该怎么喂？", "expected_doc": "金毛寻回犬喂养指南"},
    {"question": "柯基一天吃多少狗粮？", "expected_doc": "柯基犬喂养指南"},
    {"question": "布偶猫吃什么比较好？", "expected_doc": "布偶猫喂养指南"},
    {"question": "猫咪身上有猫藓怎么办？", "expected_doc": "猫藓（皮肤真菌病）识别与处理"},
    {"question": "狗狗得细小的症状是什么？", "expected_doc": "犬细小病毒病识别与预防"},
    {"question": "猫咪应激反应有哪些表现？", "expected_doc": "猫咪应激反应识别与处理"},
    {"question": "夏天怎么防止宠物中暑？", "expected_doc": "夏季宠物防暑指南"},
    {"question": "老年猫护理要注意什么？", "expected_doc": "老年宠物护理指南"},
    {"question": "狗子太胖了怎么减肥？", "expected_doc": "宠物肥胖管理指南"},
    {"question": "小狗老是自己在家叫怎么办？", "expected_doc": "狗狗分离焦虑识别与训练"},
    {"question": "猫咪喝水少会不会得尿路病？", "expected_doc": "猫咪泌尿系统疾病预防"},
    {"question": "VIP洗护套餐里都有什么？", "expected_doc": "洗护VIP套餐"},
]

# ============ 三种检索器 ============
_bm25_cache = None

def build_bm25_only(k: int = K):
    """纯 BM25（jieba 分词），与项目 get_hybrid_retriever 里做法一致"""
    global _bm25_cache
    if _bm25_cache is None:
        _bm25_cache = BM25Retriever.from_documents(
            _export_all_chunks(),
            k=k,
            preprocess_func=lambda t: jieba.lcut(t),
        )
    return _bm25_cache


def build_vector_only(k: int = K):
    """纯向量检索"""
    return get_vectorstore().as_retriever(search_kwargs={"k": k})


def build_hybrid(k: int = K):
    """混合检索（项目原样）"""
    return get_hybrid_retriever(k=k)


RETRIEVERS = {
    "vector(纯向量)": build_vector_only,
    "bm25(纯关键词)": build_bm25_only,
    "hybrid(混合)":   build_hybrid,
}


def main():
    stats = defaultdict(lambda: {"hit": 0, "total": 0, "miss": []})
    for c in EVAL_SET:
        expected = c["expected_doc"]
        for name, build in RETRIEVERS.items():
            retr = build()
            docs = retr.invoke(c["question"])[:K]
            titles = [str(d.metadata.get("title", "")) for d in docs]
            stats[name]["total"] += 1
            if any(expected in t for t in titles):
                stats[name]["hit"] += 1
            else:
                stats[name]["miss"].append(c["question"])

    print(f"\n===== 检索评测（{len(EVAL_SET)} 条 · Top-{K} 命中率）=====")
    result = {}
    for name, s in stats.items():
        rate = s["hit"] / s["total"] * 100
        result[name] = {"hit": s["hit"], "total": s["total"], "rate": round(rate, 1)}
        print(f"{name}: {s['hit']}/{s['total']} = {rate:.0f}%")

    print("\n----- 未命中的问题（判断是问题写得怪，还是检索真有问题）-----")
    for name, s in stats.items():
        if s["miss"]:
            print(f"[{name}]")
            for q in s["miss"]:
                print("  -", q)

    out = "retrieval_eval_result.json"
    json.dump(result, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"\n>>> 结果已存档到 {out}，这就是简历数字的实测口径")
from langchain_classic.retrievers import EnsembleRetriever

def build_hybrid_w(w_bm25, w_vec, k=K):
    bm25 = BM25Retriever.from_documents(_export_all_chunks(), k=k,
                                        preprocess_func=lambda t: jieba.lcut(t))
    vec = get_vectorstore().as_retriever(search_kwargs={"k": k})
    return EnsembleRetriever(retrievers=[bm25, vec], weights=[w_bm25, w_vec])

print("\n===== 混合权重扫描 =====")
for w in [(0.5, 0.5), (0.3, 0.7), (0.2, 0.8), (0.1, 0.9)]:
    r = build_hybrid_w(*w)
    hits = sum(1 for c in EVAL_SET
               if any(c["expected_doc"] in str(d.metadata.get("title", ""))
                      for d in r.invoke(c["question"])[:K]))
    print(f"BM25:{w[0]} 向量:{w[1]} -> {hits}/{len(EVAL_SET)}")


if __name__ == "__main__":
    main()
