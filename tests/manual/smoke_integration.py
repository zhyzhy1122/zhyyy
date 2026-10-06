# 验收脚本：确认 DDG search 已进入 TOOL_MAP，并实跑一次 agent 真实对话
from services.agent_service import TOOL_MAP, ALL_TOOLS, get_agent_instance

print("== TOOL_MAP 现有工具 ==")
for _n, _t in TOOL_MAP.items():
    print(f"  {_n}")

names = [t.name for t in ALL_TOOLS]
print("== ALL_TOOLS ==", names)
assert any(n.endswith("search") for n in names), "search 工具未注册进 ALL_TOOLS！"
print(">> search 已注册成功，链路通畅\n")

# 实跑一段真实对话：问题设计成需要"先搜网 + 再比对店内服务"
from langchain_core.messages import HumanMessage

agent = get_agent_instance()

def run(q: str):
    print(f"\n===== 提问：{q} =====")
    seen_nodes = []
    last_msg = None
    for chunk in agent.stream({"messages": [HumanMessage(content=q)]}, stream_mode="updates"):
        for node, upd in chunk.items():
            seen_nodes.append(node)
            if "messages" in upd:
                last_msg = upd["messages"][-1]
    print("途经节点：" + " -> ".join(seen_nodes))
    print("最终回答片段：" + str(last_msg.content)[:400])

run("猫咪深度洗护包含哪些步骤？和网上常见的洗护流程有什么不同？")