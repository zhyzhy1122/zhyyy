"""评测集自身的完整性测试。

评测集如果和知识库对不上，"命中率"这个指标就失去意义了——
这一组测试就是防止评测集悄悄失效（改了知识库却忘了改评测集）。
"""
import json
import os

from run_retrieval_eval import EVAL_SET, SELECTED_WEIGHTS, TOP_K, WEIGHT_CONFIGS
from services.document_service import KB_PATH, load_document

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_eval_set_has_expected_size():
    assert len(EVAL_SET) == 30


def test_eval_questions_are_unique():
    questions = [case["question"] for case in EVAL_SET]
    assert len(questions) == len(set(questions))


def test_every_expected_doc_exists_in_knowledge_base():
    """评测集标注的 expected_doc 必须能在知识库里找到，否则该题永远不可能命中。"""
    titles = [doc["title"] for doc in load_document(KB_PATH)]

    missing = [
        case["expected_doc"]
        for case in EVAL_SET
        if not any(case["expected_doc"] in title for title in titles)
    ]

    assert missing == []


def test_selected_weights_come_from_the_sweep():
    assert tuple(SELECTED_WEIGHTS) in [tuple(weights) for weights in WEIGHT_CONFIGS]


def test_committed_result_matches_current_config():
    """已落盘的评测结果必须与代码里的评测集/权重一致，否则简历数字就没有依据。"""
    with open(os.path.join(BASE_DIR, "retrieval_eval_result.json"), encoding="utf-8") as f:
        result = json.load(f)

    meta = result["meta"]
    assert meta["eval_set_size"] == len(EVAL_SET)
    assert meta["top_k"] == TOP_K
    assert meta["weights_selected"] == f"{SELECTED_WEIGHTS[0]}/{SELECTED_WEIGHTS[1]}"

    key = f"hybrid_{meta['weights_selected']}"
    assert key in result["results"]
    assert result["results"][key]["hit"] == len(EVAL_SET), "选定的权重应达到满分命中"


def test_config_example_contains_every_required_key():
    """新人 clone 后复制 config.example.json 应当就能跑通，不能缺字段。"""
    with open(os.path.join(BASE_DIR, "config.example.json"), encoding="utf-8") as f:
        config = json.load(f)

    assert {"deepseek_api_key", "siliconflow_api_key", "price_map"} <= set(config)
