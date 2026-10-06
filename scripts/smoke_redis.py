# -*- coding: utf-8 -*-
"""Redis 短期记忆自检脚本（用于容器内或本机排查）。

作用：确认 Redis 缓存链路真的通了——写入、命中、TTL、清理。
如果 Redis 不可用，脚本会告诉你它是否按设计降级到了 SQLite。

用法：
    # 容器内
    docker exec pet_shop_backend python scripts/smoke_redis.py

    # 本机（需先启动 Redis）
    python scripts/smoke_redis.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.redis_service import (  # noqa: E402
    SHORT_MEMORY_TTL,
    clear_short_memory,
    get_client,
    get_recent_history,
    redis_available,
    set_recent_history,
)

SESSION = "__smoke_test__"
KEY = f"chat:{SESSION}:short"
SAMPLE = [{"role": "user", "content": "自检：猫咪洗护多少钱？"}]


def main() -> int:
    print(f"REDIS_HOST = {os.environ.get('REDIS_HOST', '127.0.0.1')}")
    if not redis_available():
        print("结果：Redis 不可用 —— 短期记忆会按设计降级为每次读 SQLite（服务仍可用）")
        return 1

    client = get_client()
    client.delete(KEY)

    set_recent_history(SESSION, SAMPLE)
    assert client.exists(KEY), "写入后 key 不存在"
    print(f"写入成功：{KEY}")

    ttl = client.ttl(KEY)
    print(f"TTL = {ttl}s（预期 <= {SHORT_MEMORY_TTL}s）")

    got = get_recent_history(SESSION, 10)
    assert got == SAMPLE, f"读回内容不一致：{got}"
    print(f"读回一致：{got}")

    clear_short_memory(SESSION)
    assert not client.exists(KEY), "清理后 key 仍存在"
    print("清理成功")

    print("结果：Redis 短期记忆链路正常 ✅")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
