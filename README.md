# 萌宠之家 AI 客服系统

基于 RAG（检索增强生成）的智能客服系统，支持知识库问答、文件上传、流式输出、来源引用等功能。

## 项目亮点

- **LangGraph 流式架构**：使用 LangGraph 构建智能体，支持流式输出和查询改写
- **RAG 检索增强**：基于 Chroma 向量数据库，支持 PDF/Word/TXT 文件上传和知识库管理
- **全栈实现**：FastAPI 后端 + Vue 3 前端，前后端分离
- **完整会话管理**：支持会话列表、右键菜单（重命名/置顶/删除）、多轮对话
- **来源引用**：AI 回答时展示参考来源，支持开关控制

## 技术栈

### 后端
- **FastAPI**：Web 框架
- **LangChain + LangGraph**：智能体编排，支持流式输出和查询改写
- **Chroma**：向量数据库
- **SQLite**：会话历史和文档存储
- **DeepSeek**：大语言模型
- **SiliconFlow**：Embedding 服务

### 前端
- **Vue 3** + **TypeScript** + **Vite**
- **Pinia**：状态管理
- **Element Plus**：UI 组件库
- **markdown-it**：Markdown 渲染

## 功能特性

### 用户端
- 流式问答（打字机效果）
- 来源引用卡片（展示参考文档）
- 会话列表管理
- 右键菜单（重命名/置顶/删除会话）
- 点赞/点踩反馈

### 管理端
- 知识库文档管理（增删改查）
- 文件上传（PDF/Word/TXT）
- 自动切分和向量化

## 快速开始

### 1. 克隆项目

```bash
git clone <your-repo-url>
cd 宠物店rag项目
```

### 2. 后端配置

```bash
# 创建虚拟环境
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/Mac

# 安装依赖
pip install fastapi uvicorn langchain langgraph chromadb deepseek python-docx pypdf

# 配置 API Key
cp config.example.json config.json
# 编辑 config.json，填入你的 API Key
```

### 3. 启动后端

```bash
python main.py
```

后端运行在 `http://localhost:8000`

### 4. 前端配置

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

前端运行在 `http://localhost:5173`

## 项目结构

```
.
├── main.py                 # FastAPI 入口
├── services/               # 后端服务层
│   ├── agent_service.py    # LangGraph 智能体
│   ├── rag_service.py      # RAG 检索服务
│   ├── vectorstore_service.py  # 向量库服务
│   ├── database.py         # SQLite 数据库
│   └── file_parser.py      # 文件解析（PDF/Word/TXT）
├── frontend/               # Vue 3 前端
│   ├── src/
│   │   ├── api/            # API 调用
│   │   ├── stores/         # Pinia 状态管理
│   │   ├── components/     # 组件
│   │   └── views/          # 页面
│   └── package.json
├── config.json             # API Key 配置（不提交）
└── config.example.json     # 配置模板
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

## 开发日志

- 2026-08-16：完成 LangGraph 流式架构，支持查询改写
- 2026-08-16：实现文件上传功能（PDF/Word/TXT）
- 2026-08-16：完成会话右键菜单（重命名/置顶/删除）
- 2026-08-16：实现来源引用卡片，支持开关控制

## License

MIT
