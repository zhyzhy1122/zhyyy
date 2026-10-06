# tests/manual — 手工冒烟脚本

这里的脚本**不是单元测试**，它们会真的调用大模型 / 联网 / Redis，需要先配好
`config/config.json` 里的 API Key。因此被 `pytest.ini` 的 `norecursedirs` 排除，
不会被 `pytest tests` 收集。

单元测试在上一层 `tests/*.py`，全部离线可跑：

```bash
python -m pytest tests -q
```

| 脚本 | 用途 |
|------|------|
| `smoke_agent_stream.py` | 跑一次流式问答，肉眼确认 SSE 输出正常 |
| `smoke_agent_live.py` | 跑一次完整 Agent 链路（含工具调用） |
| `smoke_compare_prompts.py` | 对比不同提示词下的回答质量 |
| `smoke_mcp_ddg.py` | 验证 DuckDuckGo MCP 工具是否可用（需要代理） |
| `smoke_integration.py` | 端到端集成冒烟：建库 → 检索 → 问答 |

运行方式（在项目根目录）：

```bash
python tests/manual/smoke_agent_stream.py
```
