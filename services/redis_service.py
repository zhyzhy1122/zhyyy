import json
import os

import redis


REDIS_HOST = os.environ.get("REDIS_HOST", "127.0.0.1")
REDIS_PORT  = 6379
REDIS_DB = 0
SHORT_MEMORY_TTL = 3600
HISTORY_LIMIT = 10
_client = None
def get_client():
    global _client
    if _client is not None:
        return _client
    _client = redis.Redis(
        host = REDIS_HOST,
        port = REDIS_PORT,
        db = REDIS_DB,
        decode_responses= True,
    )
    return _client

def get_recent_history(session_id:str,limit:int = HISTORY_LIMIT):
    key = f"chat:{session_id}:short"
    cache = get_client()
    raw = cache.get(key)
    if raw is not None:
        cache.expire(key,SHORT_MEMORY_TTL)
        msgs = json.loads(raw)
        return msgs[-limit:]

    from services.database import get_chat_history
    history  = get_chat_history(session_id,limit)

    if history :
        set_recent_history(session_id,history,limit)
    return history

def set_recent_history(session_id:str,messages:list,limit:int = HISTORY_LIMIT):
    cache = get_client()
    data = json.dumps(messages[-limit:],ensure_ascii=False)
    cache.set(
        f"chat:{session_id}:short",
        data,
        ex=SHORT_MEMORY_TTL,
    )
def clear_short_memory(session_id:str):
    get_client().delete(f"chat:{session_id}:short")
