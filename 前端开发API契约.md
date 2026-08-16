# 萌宠之家 RAG 项目 — 前端开发 API 契约 v1.3

> **v1.3 变更（2026-08-15）**：SSE 来源事件已实现——`/ask/stream` 支持 `show_sources` 参数与 `source` 事件（见 3.3 / 4.7）。
> **v1.2 变更（2026-08-15）**：`POST/PUT /documents` 请求格式从 query string 改为 **JSON body**（正文不再受 URL 16KB 限制）；缺失必填字段时后端返回 422。坑 3/6/7 已按后端现状更新。

> **文档用途**：作为 AI 编程助手（Cursor / Claude Code / Copilot 等）开发前端时的输入契约，防止 Agent 自行发明接口。
> **后端基线**：FastAPI + LangChain + **LangGraph 智能体**（意图路由：rag/chat）+ Chroma + SQLite，端口 **8000**。
> **接口状态标注**：✅ = 已实现，前端直接对接；🔶 = 建议新增（v2），前端可先按契约开发，后端随后补齐。

---

## 0. 技术栈（前端 Agent 必须遵守）

| 项 | 选型 | 说明 |
|---|---|---|
| 框架 | **Vue 3**（组合式 API + `<script setup>`）+ **Vite** + **TypeScript** | 必须 TS |
| 状态管理 | **Pinia** | chatStore 管理流式状态 |
| 路由 | **Vue Router** | 用户端/管理端懒加载 |
| UI 组件库 | **Element Plus** | 管理端表格/表单/弹窗 |
| HTTP | **axios**（普通请求）+ **fetch**（SSE 流式） | ⚠️ axios 不支持流式解析 |
| Markdown | **markdown-it + DOMPurify** | 渲染 AI 回答，**必须防 XSS** |
| 代码高亮 | highlight.js（可选） | |

---

## 1. 开发环境约定

- 后端服务：`http://localhost:8000`
- 前端开发服务器：`http://localhost:5173`（后端 CORS 已放行此来源）
- 推荐用 Vite 代理避免跨域，`vite.config.ts`：

```ts
export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    proxy: {
      '/api': { target: 'http://localhost:8000', changeOrigin: true },
      '/ask': { target: 'http://localhost:8000', changeOrigin: true },
      '/documents': { target: 'http://localhost:8000', changeOrigin: true },
    },
  },
})
```

> 注意：现有接口路径没有 `/api` 前缀（如 `/ask`），代理时按实际路径配置；新增的 v2 接口统一加 `/api` 前缀。

---

## 2. 统一约定

### 2.1 响应风格

现有后端**未使用统一包装**，直接返回业务 JSON；出错时返回 `{"error": "..."}`（HTTP 状态仍为 200）。

前端 axios 响应拦截器统一处理：

```ts
service.interceptors.response.use(
  (res) => {
    if (res.data && res.data.error) return Promise.reject(new Error(res.data.error))
    return res.data
  },
  (err) => Promise.reject(new Error('网络异常，请稍后重试'))
)
```

### 2.2 session_id 约定（重要）

- 前端**首次访问时生成 UUID v4** 作为 `session_id`，存入 localStorage
- 后续所有聊天请求携带同一个 `session_id`（多轮对话记忆依赖它）
- 生成方式：`crypto.randomUUID()`（现代浏览器内置）

---

## 3. 已实现接口（✅ 直接对接，不要自行发明）

### 3.1 健康检查

```
GET /
```
响应：
```json
{ "message": "萌宠之家 RAG 系统已启动" }
```

### 3.2 非流式问答

```
POST /ask?question={问题}&session_id={会话ID}
```
- 请求参数在 **query string** 中（当前实现如此，前端照做）
- `session_id` 缺省为 `default`

响应：
```json
{
  "question": "猫咪多久洗一次澡",
  "answer": "建议每 1-2 个月洗一次……"
}
```

### 3.3 流式问答（SSE）

```
POST /ask/stream?question={问题}&session_id={会话ID}&show_sources=true
```
- `show_sources`（可选，默认 `true`）：是否输出参考资料（source 事件）；前端设置开关可传 `false` 关闭

**SSE 协议**：
- `Content-Type: text/event-stream`
- 可能收到两种事件：文本块 `{"content": "..."}` 和来源事件 `{"type": "source", ...}`（格式详见 4.7）
- 每个数据块（增量文本）：
```
data: {"content": "猫咪"}

data: {"content": "多久"}

data: {"content": "洗一次"}
```
- 结束标记（最后一行）：
```
data: [DONE]

```

**⚠️ 前端实现要点**：
- `EventSource` 只支持 GET，**此处是 POST，必须用 `fetch` + `ReadableStream`** 解析
- 标准解析骨架：

```ts
export async function streamChat(question: string, sessionId: string,
                                 onToken: (t: string) => void, signal: AbortSignal) {
  const url = `/ask/stream?question=${encodeURIComponent(question)}&session_id=${encodeURIComponent(sessionId)}`
  const resp = await fetch(url, { method: 'POST', signal })
  if (!resp.ok || !resp.body) throw new Error('流式请求失败')

  const reader = resp.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })

    // SSE 事件以空行分隔
    const lines = buffer.split('\n\n')
    buffer = lines.pop() ?? ''

    for (const event of lines) {
      const line = event.trim()
      if (!line.startsWith('data:')) continue
      const data = line.slice(5).trim()
      if (data === '[DONE]') return          // 结束
      try {
        const parsed = JSON.parse(data)
        if (typeof parsed.content === 'string') onToken(parsed.content)
      } catch { /* 忽略无法解析的行 */ }
    }
  }
}
```

### 3.4 文档列表（管理端-知识库）

```
GET /documents
```
响应：
```json
[
  { "id": 1, "title": "猫咪洗澡指南", "source": "手动录入", "created_at": "2026-08-15 10:00:00", "updated_at": "2026-08-15 10:00:00" }
]
```

### 3.5 文档详情

```
GET /documents/{doc_id}
```
成功：
```json
{ "id": 1, "title": "猫咪洗澡指南", "content": "……全文……", "source": "手动录入", "created_at": "...", "updated_at": "..." }
```
失败：
```json
{ "error": "文档不存在" }
```

### 3.6 新增文档

```
POST /documents
```
请求体（JSON）：
```json
{ "title": "猫咪洗澡指南", "content": "……正文……", "source": "手动录入" }
```
- `title`、`content` 必填；`source` 可选，默认 `"手动录入"`
- 缺失必填字段时后端返回 **422**（FastAPI 自动校验）
响应：
```json
{ "message": "文档已添加", "doc_id": 3 }
```
> 后端逻辑：写入 SQLite 后同步切分 → 向量化 → 存入 Chroma。

### 3.7 修改文档

```
PUT /documents/{doc_id}
```
请求体（JSON）：
```json
{ "title": "猫咪洗澡指南", "content": "……修改后的正文……" }
```
响应：
```json
{ "message": "文档已更新", "doc_id": 3 }
```
失败：`{"error": "文档不存在"}`

### 3.8 删除文档

```
DELETE /documents/{doc_id}
```
响应：
```json
{ "message": "文档已删除", "doc_id": 3 }
```
失败：`{"error": "文档不存在"}`
> 后端逻辑：删除 SQLite 记录并同步删除 Chroma 中对应向量。

---

## 4. 建议新增接口（🔶 v2，前端可先按此契约开发）

### 4.1 会话列表（用户端侧边栏）

```
GET /api/sessions
```
响应：
```json
{
  "sessions": [
    { "session_id": "uuid-xxx", "title": "猫咪多久洗一次澡", "message_count": 12, "updated_at": "2026-08-15 10:30:00" }
  ]
}
```
> title = 该会话第一条用户消息（后端取最新一条消息的会话即可）。

### 4.2 会话消息记录（历史加载）

```
GET /api/sessions/{session_id}/messages
```
响应：
```json
{
  "messages": [
    { "id": 1, "role": "user", "content": "猫咪多久洗一次澡", "created_at": "..." },
    { "id": 2, "role": "assistant", "content": "建议每 1-2 个月……", "created_at": "..." }
  ]
}
```

### 4.3 回答反馈（👍👎，商业化闭环关键）

```
POST /api/feedback
```
请求体（JSON）：
```json
{ "message_id": 2, "rating": 1, "comment": "回答很准确" }
```
- `rating`：`1` = 点赞，`-1` = 点踩；`comment` 可选
- `message_id` 对应 4.2 接口返回的消息 id

### 4.4 管理员登录（JWT）

```
POST /api/admin/login
```
请求体（JSON）：
```json
{ "username": "admin", "password": "xxx" }
```
成功：
```json
{ "token": "eyJhbGciOi...", "expires_in": 7200 }
```
失败：`{"error": "用户名或密码错误"}`

### 4.5 管理端鉴权约定

- 登录后前端将 token 存 localStorage，axios 请求拦截器统一加头：

```ts
service.interceptors.request.use((config) => {
  const token = localStorage.getItem('admin_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})
```

- 路由守卫：未登录访问管理端页面 → 跳转登录页
- 🔶 建议后续给 `/documents` 系列接口也加上鉴权（v3），当前先保持可用

### 4.6 数据看板（管理端首页）

```
GET /api/admin/stats
```
响应：
```json
{
  "total_messages": 1234,
  "today_messages": 56,
  "total_documents": 8,
  "hot_questions": [ { "question": "寄养价格", "count": 23 } ],
  "feedback": { "up": 80, "down": 20 }
}
```

### 4.7 来源事件（✅ 已实现，前端直接对接）

流式响应支持输出"回答参考了哪篇文档"，用于前端渲染**来源卡片**。

**控制参数 `show_sources`**（可选，默认 `true`）：
- 不传或 `true`：回答文本之前会收到一条 source 事件
- `false`：不发 source 事件（前端"显示参考资料"开关可控制此参数）

**source 事件格式**（在回答文本块之前发出）：

```
data: {"type": "source", "sources": [{"doc_id": 1, "title": "猫咪洗澡指南", "snippet": "建议每1-2个月……"}]}

data: {"content": "建议"}
data: {"content": "每1-2个月"}
...
data: [DONE]

```

- `sources` 数组每项：`doc_id`（文档ID）、`title`（文档标题）、`snippet`（正文前100字预览）
- **解析要点**：遇到 `type === "source"` 时**不要追加到正文**，保存到当前消息对象，等回答结束后渲染来源卡片

**前端解析补充**（在 3.3 的解析骨架里加）：

```ts
if (parsed.type === 'source') {
  message.sources = parsed.sources   // 存起来，别追加进正文
} else if (typeof parsed.content === 'string') {
  onToken(parsed.content)            // 普通文本块
}
```

这是 RAG 项目区分度最大的前端功能——回答有出处、可核验，建议必做。
---

## 5. 前端功能清单（交付验收标准）

### 5.1 用户端（聊天页）

- [ ] 聊天窗口：消息气泡（用户右/assistant 左）、Markdown 渲染、流式打字机效果
- [ ] 输入框：发送、Enter 快捷发送、发送中禁用、停止生成（AbortController）
- [ ] 侧边栏：会话列表（4.1）、新建会话、切换会话、删除会话（🔶）
- [ ] 加载历史：进入会话拉取 4.2
- [ ] 来源卡片：回答底部展示参考文档（4.7，🔶）
- [ ] 反馈按钮：每条 AI 回答下方 👍👎（4.3）
- [ ] 推荐问题：首屏展示几个预置问题，点击即发送
- [ ] 空态 / loading / 错误态 / 断流重试提示

### 5.2 管理端

- [ ] 登录页（4.4）+ 路由守卫
- [ ] 知识库管理：文档表格（3.4）、新增（3.6）、编辑（3.7）、删除（3.8，含确认弹窗）
- [ ] 数据看板（4.6）：指标卡片 + ECharts 柱状图（热门问题）
- [ ] （🔶）会话记录浏览、反馈列表

---

## 6. 给 Agent 的提示词模板（可直接复制使用）

````text
你是一名资深前端工程师。请为"萌宠之家 AI 宠物客服"项目开发前端。

技术栈（必须遵守）：
- Vue 3（组合式 API + <script setup>）+ Vite + TypeScript + Pinia + Vue Router
- Element Plus 组件库；axios 普通请求；SSE 流式必须用 fetch + ReadableStream
- markdown-it + DOMPurify 渲染 AI 回答

API 契约：<将本文档第 3、4 节粘贴到这里>

开发要求：
1. 先实现用户聊天页（含 SSE 流式输出），本地跑通后再实现管理端
2. 页面：用户聊天页 / 管理登录 / 知识库管理 / 数据看板，路由懒加载
3. 会话 ID：首次访问用 crypto.randomUUID() 生成并存 localStorage
4. 每个关键函数写中文注释；组件拆分合理（MessageBubble、ChatInput、SourceCard 等）
5. 完整错误处理：网络异常、后端 {"error": "..."}、流式中断都要有用户可读提示
6. 管理端接口先按契约第 4 节对接（后端尚未实现的接口，前端做好调用封装即可，页面暂用模拟数据占位）
7. 先给目录结构和关键接口封装（api/ 目录）设计，确认后再写页面
````

---

## 7. 常见坑（写代码时避开）

1. **axios 不能解析 SSE**——流式必须 `fetch + ReadableStream`，且 `EventSource` 不支持 POST。
2. **Markdown 渲染必须配 DOMPurify**——AI 输出可能包含 `<script>`，直接 `v-html` 有 XSS 风险。
3. **`/documents` 系列已改用 JSON body**（中文原文传输，无需编码）；`/ask`、`/ask/stream` 仍是 query string——中文必须 `encodeURIComponent`，问题文本建议控制在 2KB 内（超长可后续改 body）。
4. **CORS 只放行了 `http://localhost:5173`**——前端 dev 端口别改；生产部署用 Nginx 同源反代，不需要 CORS。
5. **`[DONE]` 行没有 JSON 结构**——解析时先判断 `data === '[DONE]'` 再 `JSON.parse`。
6. **流式中断**：用户停止生成时 `abort()`；后端已做 `try/finally` 兜底——断连后已生成部分会回填数据库（可能残留 `content=''` 的空消息，前端渲染时过滤即可）。
7. **会话历史顺序**：后端已按 `id` 倒序查询再反转，顺序稳定，前端按返回顺序渲染即可。
