# 萌宠之家 AI 客服系统

基于 RAG（检索增强生成）+ ReAct 智能体的全栈 AI 客服系统，支持知识库问答、联网搜索、网页抓取、价格计算、流式输出、Docker 一键部署。

## 项目亮点

- **ReAct 智能体架构**：基于 LangGraph 的 ReAct 循环，智能体自主决策调用工具（知识库/搜索/价格计算），无需硬编码路由
- **MCP 工具接入**：通过 MCP 协议接入 DuckDuckGo 搜索（联网实时信息）和 fetch（网页抓取），扩展智能体能力边界
- **混合检索**：BM25（jieba 中文分词）+ Chroma 向量检索，混合排序提升召回质量
- **Redis 短期记忆**：最近 10 条对话缓存到 Redis（TTL 3600s），加速上下文加载
- **Docker 一键部署**：docker-compose 编排后端 + Redis + Nginx + 前端，开箱即用
- **流式输出 + 跳动点动画**：SSE 流式推送，前端三个跳动点指示"正在生成"
- **来源引用**：AI 回答时展示参考来源，支持开关控制
- **完整会话管理**：会话列表、右键菜单（重命名/置顶/删除）、多轮对话

## 技术栈

### 后端
- **FastAPI**：Web 框架
- **LangChain + LangGraph**：智能体编排，ReAct 循环 + 流式输出 + 查询改写
- **Chroma**：向量数据库
- **SQLite**：会话历史和文档存储
- **Redis**：短期记忆缓存（最近 10 条对话，TTL 3600s）
- **DeepSeek**：大语言模型
- **SiliconFlow**：Embedding 服务（BAAI/bge-m3）
- **MCP**：Model Context Protocol，接入 DuckDuckGo 搜索和网页抓取
- **jieba + BM25**：中文分词 + 关键词检索，与向量检索混合排序

### 前端
- **Vue 3** + **TypeScript** + **Vite**
- **Pinia**：状态管理
- **Element Plus**：UI 组件库
- **markdown-it**：Markdown 渲染
- **Nginx**：静态文件托管 + API 反向代理

### 部署
- **Docker** + **docker-compose**：一键编排后端、Redis、Nginx、前端
- **代理配置**：容器内走加速器代理，访问 DuckDuckGo 等被墙服务

## 功能特性

### 用户端
- 流式问答（打字机效果 + 跳动点动画）
- 来源引用卡片（展示参考文档）
- 会话列表管理
- 右键菜单（重命名/置顶/删除会话）
- 点赞/点踩反馈
- 多轮对话（查询改写补全上下文）

### 智能体能力（ReAct 工具）
- **query_knowledge_base**：查询店内知识库（服务/价格/套餐/养护知识）
- **calculate_price**：精确价格计算（结构化数据，非向量检索）
- **search**：DuckDuckGo 联网搜索（实时信息/最新新闻/市场价对比）
- **fetch**：抓取指定网页内容（文章/文档/网站信息）

### 管理端
- 知识库文档管理（增删改查）
- 文件上传（PDF/Word/TXT）
- 自动切分和向量化

## 快速开始

### 方式一：Docker 部署（推荐）

```bash
# 克隆项目
git clone https://github.com/zhyzhy1122/zhyyy.git
cd zhyyy

# 配置 API Key
cp config.example.json config.json
# 编辑 config.json，填入 DeepSeek 和 SiliconFlow API Key

# 启动所有服务
docker-compose up -d
```

访问 `http://localhost:8080` 即可使用。

**注意：** 如果需要 DuckDuckGo 搜索功能，需要在 `docker-compose.yml` 配置加速器代理（HTTP_PROXY/HTTPS_PROXY）。

### 方式二：本地开发

```bash
# 1. 克隆项目
git clone https://github.com/zhyzhy1122/zhyyy.git
cd zhyyy

# 2. 后端配置
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/Mac

pip install -r requirements.txt

# 配置 API Key
cp config.example.json config.json
# 编辑 config.json，填入 API Key

# 3. 启动 Redis（Docker）
docker run -d --name pet_redis -p 6379:6379 redis:7-alpine

# 4. 启动后端
python main.py
# 后端运行在 http://localhost:8000

# 5. 启动前端（开发模式）
cd frontend
npm install
npm run dev
# 前端运行在 http://localhost:5173
```

## 项目结构

```
.
├── main.py                       # FastAPI 入口
├── services/                     # 后端服务层
│   ├── agent_service.py          # LangGraph ReAct 智能体
│   ├── rag_service.py            # RAG 检索服务
│   ├── vectorstore_service.py    # 混合检索（BM25 + 向量）
│   ├── mcp_service.py            # MCP 工具桥接（DuckDuckGo 搜索、网页抓取）
│   ├── redis_service.py          # Redis 短期记忆缓存
│   ├── price_tool.py             # 价格计算工具（结构化数据）
│   ├── database.py               # SQLite 数据库
│   └── file_parser.py            # 文件解析（PDF/Word/TXT）
├── frontend/                     # Vue 3 前端
│   ├── src/
│   │   ├── api/                  # API 调用
│   │   ├── stores/               # Pinia 状态管理
│   │   ├── components/           # 组件（MessageBubble 跳动点动画）
│   │   └── views/                # 页面
│   └── package.json
├── Dockerfile                    # 后端 Docker 镜像
├── docker-compose.yml            # Docker 编排（后端 + Redis + Nginx + 前端）
├── nginx.conf                    # Nginx 配置（静态托管 + API 代理）
├── config.json                   # API Key 配置（不提交）
└── config.example.json           # 配置模板
```

## API 接口

### 用户端
- `POST /ask/stream`：流式问答（SSE）
- `GET /api/sessions`：会话列表
- `GET /api/sessions/{id}/messages`：会话消息
- `PUT /api/sessions/{id}`：重命名会话
- `DELETE /api/sessions/{id}`：删除会话
- `PUT /api/sessions/{id}/pin`：置顶/取消置顶
- `POST /api/feedback`：点赞/点踩

### 管理端
- `GET /documents`：文档列表
- `POST /documents`：新增文档
- `POST /documents/upload`：上传文件
- `PUT /documents/{id}`：修改文档
- `DELETE /documents/{id}`：删除文档

## 架构说明

### ReAct 智能体工作流

```
用户提问 → agent_node（LLM 思考）→ 是否调用工具？
                                    ├─ 是 → execute_tools → 回到 agent_node（循环）
                                    └─ 否 → END（输出最终回答）
```

智能体根据用户问题自主决策调用哪个工具，无需硬编码路由。例如：
- "猫咪深度洗护多少钱？" → 调用 `query_knowledge_base` + `calculate_price`
- "今天新闻有什么？" → 调用 `search` → 可能再调 `fetch` 抓取具体网页
- "这个价格和市场价比怎么样？" → 调用 `search`（网络）+ `query_knowledge_base`（店内）

### MCP 工具接入

通过 `mcp_service.py` 桥接 MCP 协议，将 DuckDuckGo 搜索和网页抓取工具转为 LangChain StructuredTool，注册到智能体的 TOOL_MAP。

- **DuckDuckGo**：免费、无需 API Key，但国内需加速器
- **fetch**：抓取指定 URL 的网页内容

### 混合检索

BM25（jieba 中文分词）+ Chroma 向量检索，通过 EnsembleRetriever 混合排序，提升中文场景召回质量。

## 开发日志

- 2026-08-20：接入 DuckDuckGo 搜索 MCP 工具，支持联网实时搜索
- 2026-08-20：Docker 代理配置，容器内走加速器访问被墙服务
- 2026-08-20：前端流式输出跳动点动画（CSS ::after 伪元素）
- 2026-08-20：BM25 检索改用 jieba 中文分词，解决中文分词退化问题
- 2026-08-16：完成 LangGraph ReAct 智能体架构，支持查询改写
- 2026-08-16：实现 MCP 工具接入（fetch 网页抓取）
- 2026-08-16：实现 Redis 短期记忆缓存
- 2026-08-16：实现价格计算工具（结构化数据）
- 2026-08-16：完成 Docker 一键部署（docker-compose）
- 2026-08-16：实现文件上传功能（PDF/Word/TXT）
- 2026-08-16：完成会话右键菜单（重命名/置顶/删除）
- 2026-08-16：实现来源引用卡片，支持开关控制

## License

MIT
