# legacy — 早期学习阶段代码（保留以记录演进）

这里是从零开始学 RAG 时的分步脚本，**不是当前运行链路的一部分**，`services/` 下的实现已经把它们全部取代。
保留下来是为了让项目演进过程可追溯：从"一步步手写"到"分层服务化"。

| 文件 | 说明 | 被谁取代 |
|------|------|----------|
| `step1_load.py` | 读 jsonl 知识库 → 转 LangChain `Document` | `services/document_service.py` |
| `step2_embed.py` | 调 SiliconFlow 做 Embedding | `services/embedding_service.py` |
| `step3_store.py` | 切分 + 写入 Chroma | `services/vectorstore_service.py` |
| `step4_retrieve.py` | 命令行检索问答循环 | `services/rag_service.py` |
| `container_agent_service.py` | 早期版本的单体 Agent 实现（含被注释掉的意图路由方案） | `services/agent_service.py` |

⚠️ 这些脚本按"在 `legacy/` 目录下直接运行"的假设写相对路径（如 `../config/config.json`），
只能用于阅读参考，不建议直接执行。当前可用入口请回到项目根目录看 README。
