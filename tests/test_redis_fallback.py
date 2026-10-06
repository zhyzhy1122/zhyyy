"""Redis 短期记忆缓存的降级行为测试。

README 声称"优先读 Redis，降级 SQLite 并回写"。这组测试就是在验证这句承诺：
Redis 连不上时，问答链路必须依然可用，而不是抛异常把接口打挂。
"""
import pytest


def _unreachable(*args, **kwargs):
    raise ConnectionError("redis 不可达（测试替身）")


def test_client_returns_none_when_redis_is_down(redis_reset, monkeypatch):
    monkeypatch.setattr(redis_reset.redis, "Redis", _unreachable)

    assert redis_reset.get_client() is None
    assert redis_reset.redis_available() is False


def test_history_falls_back_to_sqlite_when_redis_is_down(redis_reset, isolated_db, monkeypatch):
    isolated_db.save_message("sess-1", "user", "猫咪洗护多少钱？")
    isolated_db.save_message("sess-1", "assistant", "普通洗护 68 元。")
    monkeypatch.setattr(redis_reset.redis, "Redis", _unreachable)

    history = redis_reset.get_recent_history("sess-1", 10)

    assert history == [
        {"role": "user", "content": "猫咪洗护多少钱？"},
        {"role": "assistant", "content": "普通洗护 68 元。"},
    ]


def test_history_respects_limit(redis_reset, isolated_db, monkeypatch):
    for i in range(5):
        isolated_db.save_message("sess-2", "user", f"第{i}条")
    monkeypatch.setattr(redis_reset.redis, "Redis", _unreachable)

    history = redis_reset.get_recent_history("sess-2", 2)

    assert [m["content"] for m in history] == ["第3条", "第4条"]


def test_write_and_clear_are_noop_without_redis(redis_reset, monkeypatch):
    """Redis 不可用时，写入/清理必须是安全的空操作，不能把调用方带崩。"""
    monkeypatch.setattr(redis_reset.redis, "Redis", _unreachable)

    redis_reset.set_recent_history("sess-3", [{"role": "user", "content": "x"}])
    redis_reset.clear_short_memory("sess-3")  # 不应抛异常


def test_delete_session_also_clears_cache(redis_reset, isolated_db, monkeypatch):
    """删除会话时要同步清理缓存键，否则会读到已删除的上下文。"""
    cleared = []
    isolated_db.save_message("sess-4", "user", "hi")

    import services.redis_service as rs

    monkeypatch.setattr(rs, "clear_short_memory", lambda sid: cleared.append(sid))

    isolated_db.delete_session("sess-4")

    assert cleared == ["sess-4"]
    assert isolated_db.get_session_messages("sess-4") == []
