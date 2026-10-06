"""pytest 共享配置与 fixture。

这些测试全部离线运行：不调用 LLM、不调用 Embedding、不连 Redis、不写真实的
chat_history.db。需要外部服务的地方一律用 monkeypatch 替换成替身。
"""
import os
import sys

import pytest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)


@pytest.fixture
def isolated_db(monkeypatch, tmp_path):
    """把 SQLite 路径指向临时文件，避免污染真实的 services/chat_history.db。"""
    import services.database as db

    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "test_chat_history.db"))
    db.init_db()
    return db


@pytest.fixture
def redis_reset(monkeypatch):
    """重置 redis_service 的模块级连接缓存，保证每个用例从干净状态开始。"""
    import services.redis_service as rs

    monkeypatch.setattr(rs, "_client", None)
    monkeypatch.setattr(rs, "_available", None)
    return rs
