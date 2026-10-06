"""Redis 短期记忆缓存。

设计原则：**Redis 是加速层，不是唯一数据源**。
- 命中 Redis → 直接返回（快）
- Redis 不可用 / 取值异常 → 自动降级到 SQLite，并尝试回写缓存
- 删除会话时同步清理缓存键

这样即使没有部署 Redis（或 Redis 抖动、容器名解析失败），整个问答链路依然可用，
只是退化为每次都读 SQLite。
"""
import json
import os

import redis


REDIS_HOST = os.environ.get("REDIS_HOST", "127.0.0.1")
REDIS_PORT = int(os.environ.get("REDIS_PORT", 6379))
REDIS_DB = int(os.environ.get("REDIS_DB", 0))
SHORT_MEMORY_TTL = 3600
HISTORY_LIMIT = 10

_client = None
_available = None          # None=未探测  True=可用  False=已确认不可用


def _key(session_id: str) -> str:
    return f"chat:{session_id}:short"


def get_client():
    """返回可用的 Redis 客户端；不可用时返回 None（调用方降级到 SQLite）。"""
    global _client, _available
    if _available is False:
        return None
    if _client is not None:
        return _client
    try:
        client = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            db=REDIS_DB,
            decode_responses=True,
            socket_connect_timeout=0.5,
            socket_timeout=1.0,
        )
        client.ping()
    except Exception as exc:                        # 连接失败只记一次，不阻断主流程
        print(f"[redis] 不可用（{exc.__class__.__name__}），短期记忆降级为 SQLite")
        _available = False
        return None
    _client = client
    _available = True
    return _client


def redis_available() -> bool:
    """供健康检查 / 评测使用：当前 Redis 是否可用。"""
    return get_client() is not None


def get_recent_history(session_id: str, limit: int = HISTORY_LIMIT):
    """取最近 limit 条对话：优先 Redis，未命中或异常则回源 SQLite 并回写缓存。"""
    cache = get_client()
    if cache is not None:
        try:
            raw = cache.get(_key(session_id))
            if raw is not None:
                cache.expire(_key(session_id), SHORT_MEMORY_TTL)
                return json.loads(raw)[-limit:]
        except Exception:
            pass                                    # 缓存异常不影响返回结果

    from services.database import get_chat_history
    history = get_chat_history(session_id, limit)
    if history:
        set_recent_history(session_id, history, limit)
    return history


def set_recent_history(session_id: str, messages: list, limit: int = HISTORY_LIMIT):
    """写入短期记忆（带 TTL）。Redis 不可用时静默跳过。"""
    cache = get_client()
    if cache is None:
        return
    try:
        cache.set(
            _key(session_id),
            json.dumps(messages[-limit:], ensure_ascii=False),
            ex=SHORT_MEMORY_TTL,
        )
    except Exception:
        pass


def clear_short_memory(session_id: str):
    """删除会话时同步清理缓存，保证与 SQLite 一致。"""
    cache = get_client()
    if cache is None:
        return
    try:
        cache.delete(_key(session_id))
    except Exception:
        pass
