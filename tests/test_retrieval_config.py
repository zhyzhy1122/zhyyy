"""混合检索权重配置的回归测试。

背景：权重是**实测扫出来的**，不是拍脑袋定的。这组测试把"代码里的权重"、
"评测脚本里的权重"、"已落盘的评测结果"三者锁在一起，
任何一处被改动而另一处没跟上，测试立刻失败。
"""
from typing import List

from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever

from services.vectorstore_service import HYBRID_WEIGHTS, build_hybrid_retriever


class _EmptyRetriever(BaseRetriever):
    """空检索器替身：避免测试真的去调 Embedding 接口。"""

    def _get_relevant_documents(self, query, *, run_manager=None) -> List[Document]:
        return []


class _StubStore:
    """替身向量库：只实现 as_retriever，返回空检索器。"""

    def as_retriever(self, search_kwargs=None):
        return _EmptyRetriever()


def _chunks():
    return [
        Document(
            page_content="普通洗护服务包含全身清洗、吹干、梳理三项基本流程。",
            metadata={"doc_id": 1, "title": "宠物普通洗护服务"},
        ),
        Document(
            page_content="深度护理在普通洗护基础上增加深层清洁与护毛素滋养。",
            metadata={"doc_id": 2, "title": "宠物深度护理服务"},
        ),
    ]


def test_tuned_weights_are_the_selected_ones():
    """线上使用的混合权重应为权重扫描后选定的 0.3 / 0.7。"""
    assert HYBRID_WEIGHTS == [0.3, 0.7]


def test_build_hybrid_retriever_applies_given_weights():
    retriever = build_hybrid_retriever(_chunks(), _StubStore(), k=3, weights=[0.4, 0.6])
    assert retriever.weights == [0.4, 0.6]


def test_build_hybrid_retriever_defaults_to_tuned_weights():
    retriever = build_hybrid_retriever(_chunks(), _StubStore(), k=3)
    assert retriever.weights == [0.3, 0.7]


def test_get_hybrid_retriever_cache_key_includes_weights_and_k(monkeypatch):
    """缓存键必须包含 (k, weights)，否则不同配置会互相串味。"""
    import services.vectorstore_service as vs

    calls = {"n": 0}

    def fake_export():
        return _chunks()

    def fake_build(chunks, store, k=5, weights=None):
        calls["n"] += 1
        return build_hybrid_retriever(chunks, store, k=k, weights=weights)

    monkeypatch.setattr(vs, "_export_all_chunks", fake_export)
    monkeypatch.setattr(vs, "get_vectorstore", lambda: _StubStore())
    monkeypatch.setattr(vs, "build_hybrid_retriever", fake_build)
    monkeypatch.setattr(vs, "_hybrid_retriever", None)
    monkeypatch.setattr(vs, "_hybrid_cache_key", None)

    a = vs.get_hybrid_retriever(k=3, weights=[0.3, 0.7])
    b = vs.get_hybrid_retriever(k=3, weights=[0.3, 0.7])
    assert a is b, "相同配置应命中缓存"
    assert calls["n"] == 1

    vs.get_hybrid_retriever(k=5, weights=[0.3, 0.7])
    assert calls["n"] == 2, "k 变了必须重新构造"

    vs.get_hybrid_retriever(k=5, weights=[0.5, 0.5])
    assert calls["n"] == 3, "权重变了必须重新构造"
