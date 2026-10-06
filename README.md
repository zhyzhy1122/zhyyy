# 萌宠之家 AI 客服系统

> 基于 **RAG 混合检索 + LangGraph ReAct 智能体** 的全栈 AI 客服系统。支持知识库问答、联网搜索、网页抓取、精确价格计算、SSE 流式输出，Docker 一键部署。

![Python](https://img.shields.io/badge/Python-3.11-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.14x-green)
![LangGraph](https://img.shields.io/badge/LangGraph-ReAct-orange)
![Vue](https://img.shields.io/badge/Vue-3-42b883)
![Docker](https://img.shields.io/badge/Docker-compose-2496ed)
![Tests](https://img.shields.io/badge/tests-21%20passed-brightgreen)
![License](https://img.shields.io/badge/License-MIT-yellow)

---

## 一句话定位

**让智能体自己决定"该查库还是该上网"的宠物店客服。** 不写死意图路由，而是把知识库检索、联网搜索、网页抓取、价格计算注册成工具，由 LLM 通过 function calling 自主规划调用顺序。

---

## 项目亮点

### 1. ReAct 智能体：不硬编码意图路由

```
用户提问 → agent_node（LLM 思考）→ 要调工具吗？
                                   ├─ 是 → execute_tools → 回到 agent_node（循环）
                                   └─ 否 → END（输出最终回答）
```

实际行为举例：

| 用户提问 | 智能体自主决策的调用链 |
|---|---|
| "猫咪深度洗护多少钱？" | `query_knowledge_base` → `calculate_price` |
| "今天有什么新闻？" | `search` → 可能再 `fetch` 抓取具体网页 |
| "这个价格和市场价比怎么样？" | `search`（网络）+ `query_knowledge_base`（店内）→ 综合对比 |

### 2. MCP 协议接入外部工具

通过 `services/mcp_service.py` 桥接 MCP 协议，把 DuckDuckGo 搜索与网页抓取转成 LangChain `StructuredTool` 注册进 `TOOL_MAP`。容器内通过代理解决国内访问问题；检索侧配额耗尽时按 **Tavily → DuckDuckGo → 友好降级** 兜底。

### 3. 混合检索：权重是扫出来的，不是拍脑袋定的

`BM25（jieba 中文分词）+ Chroma 向量检索`，用 `EnsembleRetriever` 融合。中文场景直接用默认 `text.split()` 会让 BM25 分词退化，因此改用 jieba 分词。

**混合权重经实测扫描确定，见下方评测表。**

### 4. Redis 短期记忆 + 自动降级

最近 10 条对话缓存进 Redis（TTL 3600s），优先读缓存、未命中回源 SQLite 并回写，删除会话时同步清理缓存键。

**关键设计：Redis 是加速层而不是唯一数据源。** 连接失败时自动降级读 SQLite，问答链路不受影响——这一点有单元测试覆盖（见 `tests/test_redis_fallback.py`）。

### 5. 工程化

- **SSE 流式输出**：打字机效果，nginx 关闭 `proxy_buffering` 保证真流式
- **来源引用卡片**：回答附参考文档标题 + 片段，降低幻觉
- **完整会话管理**：列表 / 重命名 / 置顶 / 删除 / 点赞点踩
- **Docker Compose**：后端 + Redis + Nginx + 前端一键起，配置与数据用数据卷挂载，密钥不进镜像
- **健康检查**：镜像内置 `HEALTHCHECK`，compose 用 Redis 健康检查控制后端启动顺序

---

## 检索评测（任何人 clone 后可复现）

```bash
python run_retrieval_eval.py
```

评测集 **30 条**（`expected_doc` 为人工标注的正确文档标题），指标为 **Top-3 命中率**。
评测向量库**每次从 `knowledge_base/pet_shop_docs.jsonl` 重建**，不读取本地 `chroma_db/`，因此结果可复现（本地向量库会被管理端上传的文档持续污染，用它评测数字会漂）。

| 检索方式 | Top-3 命中率 |
|---|---|
| 纯向量（Chroma） | 30/30 = 100.0% |
| 纯关键词（BM25 + jieba） | 26/30 = 86.7% |
| 混合 0.5/0.5（LangChain 默认） | 29/30 = 96.7% |
| **混合 0.3/0.7（当前配置）** | **30/30 = 100.0%** |
| 混合 0.2/0.8 | 30/30 = 100.0% |
| 混合 0.1/0.9 | 30/30 = 100.0% |

完整结果（含未命中明细、评测元信息）见 [`retrieval_eval_result.json`](./retrieval_eval_result.json)。

**结论与边界**：默认 0.5/0.5 时 BM25 的噪声会在短文档场景挤出正确结果（`猫咪打疫苗一般几针？` 未命中），把权重调到 0.3/0.7 后满分。同时必须诚实说明：**纯向量在本评测集上已是 100%**，所以混合检索的价值不在"分数更高"，而在于保留关键词精确匹配（型号、专有名词、短查询）的能力，避免向量检索在长尾查询上失效。评测集偏简单是已知局限，下一步计划见文末。

---

## 系统架构

```
浏览器 (Vue 3 + Element Plus)
   │  /ask  /documents  /api
   ▼
Nginx ──静态托管 + API 反代(SSE 关闭缓冲)──▶ FastAPI (main.py)
                                               │
                                               ▼
                              ┌──────────────────────────────┐
                              │  LangGraph ReAct 智能体       │
                              │  agent_node ⇄ execute_tools  │
                              └──────────────┬───────────────┘
                                             │ 工具
        ┌────────────────┬───────────────────┼──────────────────┐
        ▼                ▼                   ▼                  ▼
  query_knowledge   calculate_price      search(MCP)      fetch(MCP)
        │                │                   │                  │
        ▼                ▼                   └──── DuckDuckGo ───┘
  混合检索            config.json
  BM25+向量           价目表
        │
   ┌────┴─────┐
   ▼          ▼
Chroma     jieba+BM25
   │
   ▼
Redis(短期记忆, TTL 3600s) ──降级──▶ SQLite(会话/文档/反馈)
```

---

## 技术栈

| 层 | 技术 | 说明 |
|----|------|------|
| Web 框架 | FastAPI + SSE | 流式问答接口 |
| 智能体 | LangGraph `StateGraph` | ReAct 循环、工具调用 |
| 大模型 | DeepSeek（OpenAI 兼容协议） | 对话与工具决策 |
| Embedding | SiliconFlow `BAAI/bge-m3` | 向量化 |
| 向量库 | Chroma | 持久化到 `chroma_db/` |
| 关键词检索 | `rank_bm25` + jieba | 中文分词，与向量混合 |
| 工具协议 | MCP（`langchain-mcp-adapters`） | DuckDuckGo 搜索、网页抓取 |
| 缓存 | Redis | 短期记忆，失败自动降级 |
| 存储 | SQLite | 会话、文档、反馈、会话元信息 |
| 前端 | Vue 3 + TS + Vite + Pinia + Element Plus | 用户端 + 管理端 |
| 部署 | Docker Compose + Nginx | 后端 / Redis / 前端编排 |

---

## 快速开始

### 方式一：Docker 部署（推荐）

```bash
git clone https://github.com/zhyzhy1122/zhyyy.git
cd zhyyy

# 1. 准备配置（含 API Key，已被 .gitignore 排除）
mkdir -p config
cp config.example.json config/config.json
# 编辑 config/config.json，填入 DeepSeek 与 SiliconFlow 的 Key

# 2. 一键启动（后端 + Redis + Nginx + 前端）
docker compose up -d --build

# 3. 打开 http://localhost:8080
```

**关于代理**：容器内访问 DuckDuckGo 需要代理，默认走宿主机 Clash 的 `47890` 端口。如果你不用代理或端口不同，在项目根目录建 `.env` 覆盖：

```env
DOCKER_HTTP_PROXY=http://host.docker.internal:7890
DOCKER_HTTPS_PROXY=http://host.docker.internal:7890
```

> `NO_PROXY` 中必须保留 `api.deepseek.com`、`api.siliconflow.cn`、`redis`，否则大模型接口和 Redis 会被代理拦掉。Docker 部署只在 nginx 同源下服务前端，无需额外 CORS 配置。

**端口冲突排查**：日常入口是 `http://localhost:8080`（nginx，同源且已反代 API）。若本机 8000 端口已被别的程序占用，`docker compose up` 不会报错，但 `http://localhost:8000` 会被那个程序抢答——此时前端仍可正常使用，直接访问后端请改用其他主机端口：

```bash
# 查看 8000 被谁占用（Windows）
Get-NetTCPConnection -LocalPort 8000 -State Listen
# 或把 compose 里的 "8000:8000" 改成 "8001:8000"
```

### 方式二：本地开发

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS / Linux

pip install -r requirements.txt

mkdir -p config
cp config.example.json config/config.json   # 填 Key

# 可选：本机 Redis（不启动也能跑，会自动降级到 SQLite）
docker run -d --name pet_redis -p 6379:6379 redis:7-alpine

python main.py                  # http://localhost:8000
```

前端开发模式：

```bash
cd frontend
npm install
npm run dev                     # http://localhost:5173
```

---

## API 接口

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/ask/stream` | 流式问答（SSE） |
| GET | `/api/sessions` | 会话列表 |
| GET | `/api/sessions/{id}/messages` | 会话消息 |
| PUT | `/api/sessions/{id}` | 重命名会话 |
| PUT | `/api/sessions/{id}/pin` | 置顶 / 取消置顶 |
| DELETE | `/api/sessions/{id}` | 删除会话（同步清缓存） |
| POST | `/api/feedback` | 点赞 / 点踩 |
| GET | `/documents` | 知识库文档列表 |
| POST | `/documents` | 新增文档 |
| POST | `/documents/upload` | 上传文件（PDF / Word / TXT） |
| PUT | `/documents/{id}` | 修改文档 |
| DELETE | `/documents/{id}` | 删除文档（同步删向量） |

后端启动后访问 `http://localhost:8000/docs` 查看交互式文档。

---

## 项目结构

```
.
├── main.py                       # FastAPI 入口与路由
├── run_retrieval_eval.py         # 可复现的检索评测脚本
├── retrieval_eval_result.json    # 评测结果（简历数字的实测口径）
├── services/
│   ├── agent_service.py          # LangGraph ReAct 智能体
│   ├── vectorstore_service.py    # 混合检索（BM25 + 向量，权重常量在此）
│   ├── rag_service.py            # RAG 链与知识库工具
│   ├── mcp_service.py            # MCP 工具桥接
│   ├── redis_service.py          # 短期记忆缓存（含 SQLite 降级）
│   ├── price_tool.py             # 价格计算工具（结构化数据）
│   ├── database.py               # SQLite：会话/文档/反馈
│   ├── document_service.py       # 文档加载与切分
│   ├── embedding_service.py      # SiliconFlow Embedding
│   └── file_parser.py            # PDF / Word / TXT 解析
├── config/                       # config.json（已忽略）+ 配置目录
├── knowledge_base/               # 初始知识库 75 条 jsonl
├── frontend/                     # Vue 3 前端（用户端 + 管理端）
├── tests/                        # 离线单元测试
│   └── manual/                   # 需要真实 API Key 的手工冒烟脚本
├── scripts/                      # 调试脚本（容器内自检）
├── legacy/                       # 早期学习阶段的脚本，保留以记录演进
├── Dockerfile / docker-compose.yml / frontend/nginx.conf
└── requirements.txt / requirements-dev.txt
```

---

## 测试

```bash
pip install -r requirements-dev.txt
python -m pytest tests -q
```

当前：**21 passed**。测试全部离线运行（不调 LLM、不调 Embedding、不连 Redis、不写真实数据库），覆盖：

| 文件 | 覆盖内容 |
|---|---|
| `tests/test_retrieval_config.py` | 混合权重常量、按权重构造检索器、缓存键包含 `(k, weights)` |
| `tests/test_redis_fallback.py` | Redis 不可用时降级 SQLite、limit 生效、删除会话同步清缓存 |
| `tests/test_price_tool.py` | 价目表读取、多项目合计、未知服务提示、空白字符容错 |
| `tests/test_eval_set.py` | 评测集与知识库一致、权重出自扫描范围、结果文件与代码一致 |

`tests/manual/` 下是需要真实 API Key 的冒烟脚本，已被 `pytest.ini` 的 `norecursedirs` 排除。

---

## 设计取舍与已知限制

诚实记录，避免过度包装：

1. **评测集偏简单**：30 条问题多为文档标题的近义改写，纯向量已达 100%。计划补 10~15 条真实口语句式与多跳问题（如"寄养三天加一次深度洗护一共多少钱"），并把命中标准从"标题命中"升级为"答案要点命中"。
2. **混合检索未上 rerank**：当前用 `EnsembleRetriever` 做加权融合。引入 Cross-Encoder rerank 会显著提升 Top-1 精度，但会带来延迟与模型部署成本，需先有更大的评测集支撑判断。
3. **切分策略固定**：`chunk_size=400 / overlap=80` 是按当前知识库规模手调的，未做参数敏感性实验。
4. **SQLite 的并发上限**：单文件库适合演示与中小流量；高并发写入需要换 PostgreSQL。
5. **Redis 只做短期记忆**：没有做语义缓存（相似问题复用答案），也没有做分布式锁，多副本部署时需重新设计。
6. **本地向量库会被管理端污染**：这是评测脚本必须从源文件重建的原因；生产环境应把"知识库源"作为唯一真相来源，向量库视为可重建的派生数据。

---

## License

MIT
