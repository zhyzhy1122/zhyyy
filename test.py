# # from services.redis_service import get_recent_history, set_recent_history
# # print(get_recent_history("default", 10))   # 第一次走 SQLite 并预热
# # print(get_recent_history("default", 10))   # 第二次应命中 Redis 缓存
#
#
#
# # # 临时自测（可放文件底部 __main__）
# # from services.mcp_service import get_mcp_tools
# # tools = get_mcp_tools()
# # for t in tools:
# #     print(t.name, "能同步invoke:", callable(t.invoke))
# # out = tools[0].invoke({"url": "https://example.com", "max_length": 100})
# # print("同步invoke结果:", str(out)[:150])
# # 临时自测
# from services.agent_service import ask_agent
# print(ask_agent("请用联网工具抓取 https://example.com 的标题和正文", session_id="mcp_test"))
from services.agent_service import ask_agent_stream
answer = "".join(ask_agent_stream("请用联网工具抓取 https://example.com 的标题和正文", session_id="mcp_test2"))
print(answer)