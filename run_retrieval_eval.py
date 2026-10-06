# -*- coding: utf-8 -*-
"""检索评测 · 可复现版

为什么要有这个脚本
------------------
简历上"Top-3 命中率"这类数字，必须**任何人 clone 下来都能复现**，否则就是不可验证的自述。
这个脚本做到了这一点：

1. 评测用的向量库**从版本控制内的知识库源文件重建**（`knowledge_base/pet_shop_docs.jsonl`），
   不读取本地 `chroma_db/`——因为本地向量库会被管理端上传的文档持续污染，
   用它评测的结果无法复现（同一个脚本两次跑出来的数字会不一样）。
2. 一次跑完「纯向量 / 纯 BM25 / 混合检索多组权重」，结果全部落盘到
   `retrieval_eval_result.json`，并且带上评测集规模、知识库规模、时间戳等元信息。
3. 混合检索权重由此扫描确定，选定值写在 `services/vectorstore_service.py` 的
   `HYBRID_WEIGHTS` 常量里，两者保持一致。

用法
----
    python run_retrieval_eval.py

前提：`config/config.json` 里 `siliconflow_api_key` 有效（需要调用 Embedding 服务）。
评测过程只调用 Embedding 接口，不会调用 LLM，因此不消耗对话额度。
"""
import json
import os
import shutil
import sys
import tempfile
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

import jieba
from langchain_chroma import Chroma
from langchain_community.retrievers import BM25Retriever

from services.document_service import KB_PATH, convert_to_documents, load_document, split_docs
from services.embedding_service import get_embeddings
from services.vectorstore_service import build_hybrid_retriever

TOP_K = 3
# 权重扫描范围：[BM25 权重, 向量权重]
WEIGHT_CONFIGS = [(0.5, 0.5), (0.4, 0.6), (0.3, 0.7), (0.2, 0.8), (0.1, 0.9)]
# 最终选定的权重，需与 services/vectorstore_service.py 的 HYBRID_WEIGHTS 一致
SELECTED_WEIGHTS = (0.3, 0.7)
OUT_PATH = os.path.join(BASE_DIR, "retrieval_eval_result.json")

# ============ 评测集：30 条，全部基于知识库真实文档标题 ============
# 说明：`expected_doc` 是人工标注的"正确答案应命中的文档标题"。
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


def build_eval_store(persist_dir: str):
    """从知识库源文件重建一个临时向量库（评测专用，与本地 chroma_db 隔离）。"""
    chunks = split_docs(convert_to_documents(load_document(KB_PATH)))
    store = Chroma.from_documents(
        documents=chunks,
        embedding=get_embeddings(),
        persist_directory=persist_dir,
        collection_name="pet_shop_eval",
    )
    return store, chunks


def evaluate(retriever, k: int = TOP_K):
    """返回 (命中数, 未命中问题列表)"""
    hits, misses = 0, []
    for case in EVAL_SET:
        docs = retriever.invoke(case["question"])[:k]
        titles = [str(d.metadata.get("title", "")) for d in docs]
        if any(case["expected_doc"] in t for t in titles):
            hits += 1
        else:
            misses.append(case["question"])
    return hits, misses


def main():
    total = len(EVAL_SET)
    print(f"评测集：{total} 条 · Top-{TOP_K} 命中率")
    print(f"知识库：{KB_PATH}")

    tmp_dir = tempfile.mkdtemp(prefix="pet_eval_chroma_")
    try:
        store, chunks = build_eval_store(tmp_dir)
        print(f"评测向量库已重建：{len(chunks)} 个 chunk（临时目录，不污染 chroma_db）\n")

        vector_retriever = store.as_retriever(search_kwargs={"k": TOP_K})
        bm25_retriever = BM25Retriever.from_documents(
            chunks, k=TOP_K, preprocess_func=lambda t: jieba.lcut(t)
        )

        results, misses = {}, {}

        for name, retriever in (("vector_only", vector_retriever), ("bm25_only", bm25_retriever)):
            hits, miss = evaluate(retriever)
            results[name] = {"hit": hits, "total": total, "rate": round(hits / total * 100, 1)}
            misses[name] = miss

        for w_bm25, w_vec in WEIGHT_CONFIGS:
            key = f"hybrid_{w_bm25}/{w_vec}"
            retriever = build_hybrid_retriever(
                chunks, store, k=TOP_K, weights=[w_bm25, w_vec]
            )
            hits, miss = evaluate(retriever)
            results[key] = {"hit": hits, "total": total, "rate": round(hits / total * 100, 1)}
            misses[key] = miss

        # ---------- 打印 ----------
        print("===== 检索方式对比 =====")
        for name, r in results.items():
            mark = "  ← 当前线上配置" if name == f"hybrid_{SELECTED_WEIGHTS[0]}/{SELECTED_WEIGHTS[1]}" else ""
            print(f"  {name:<20} {r['hit']:>2}/{r['total']}  {r['rate']:>5.1f}%{mark}")

        print("\n===== 未命中明细（判断是问题写得怪，还是检索真有问题）=====")
        for name, miss in misses.items():
            if miss:
                print(f"  [{name}]")
                for q in miss:
                    print(f"    - {q}")

        payload = {
            "meta": {
                "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
                "eval_set_size": total,
                "top_k": TOP_K,
                "kb_source": os.path.relpath(KB_PATH, BASE_DIR).replace("\\", "/"),
                "kb_chunks": len(chunks),
                "weights_swept": [f"{a}/{b}" for a, b in WEIGHT_CONFIGS],
                "weights_selected": f"{SELECTED_WEIGHTS[0]}/{SELECTED_WEIGHTS[1]}",
                "reproducible": True,
                "method": (
                    "评测向量库每次从 knowledge_base/pet_shop_docs.jsonl 重建，"
                    "不读取本地 chroma_db，因此任何人 clone 后可复现同一组数字"
                ),
                "hit_criterion": "Top-K 返回的 chunk 标题中，包含标注的 expected_doc 即算命中",
            },
            "results": results,
            "misses": {k: v for k, v in misses.items() if v},
        }
        with open(OUT_PATH, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        print(f"\n>>> 结果已写入 {os.path.relpath(OUT_PATH, BASE_DIR)}")
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
