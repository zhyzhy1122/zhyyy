# ④ 验证脚本：比价问题，观察 LLM 是否先搜索网络、再回查知识库组合决策
from services.agent_service import get_agent_instance, TOOL_MAP
from langchain_core.messages import HumanMessage, ToolMessage

agent = get_agent_instance()
q = "店里猫咪深度洗护是 108 元，这个价位在同类宠物店中算偏高还是偏低？"

print(f"===== 提问：{q} =====\n")
for chunk in agent.stream({"messages": [HumanMessage(content=q)]}, stream_mode="updates"):
    for node, upd in chunk.items():
        print(f"[节点: {node}]")
        if "messages" in upd:
            for m in upd["messages"]:
                if isinstance(m, ToolMessage):
                    print(f"   ├─ 工具调用结果 ({m.tool_call_id[:8]}): {str(m.content)[:150]}")
                elif m.tool_calls:
                    for tc in m.tool_calls:
                        print(f"   └─ ✦ LLM 决定调用工具 -> {tc['name']}({tc['args']})")
        else:
            # updates 模式下其它键可能直接是状态
            pass
print("\n===== 全过程结束 =====")