// 后端接口封装（契约 v1.3）
// 注意：API key 全部在后端 config.json，前端不接触任何密钥

export interface SourceItem {
  doc_id: number
  title: string
  snippet: string
}

export interface ChatMessage {
  id?: number
  role: 'user' | 'assistant'
  content: string
  sources?: SourceItem[]
  created_at?: string
}

export interface SessionItem {
  session_id: string
  title: string
  message_count: number
  updated_at: string
  is_pinned: boolean
}

// 流式问答：fetch + ReadableStream 解析 SSE
// onToken：每收到一个文本块回调；onSources：收到来源事件回调
export async function streamChat(
  question: string,
  sessionId: string,
  showSources: boolean,
  onToken: (t: string) => void,
  onSources: (s: SourceItem[]) => void,
  signal: AbortSignal,
): Promise<void> {
  const url = `/ask/stream?question=${encodeURIComponent(question)}&session_id=${encodeURIComponent(sessionId)}&show_sources=${showSources}`
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
      if (data === '[DONE]') return // 结束标记
      try {
        const parsed = JSON.parse(data)
        if (parsed.type === 'source' && Array.isArray(parsed.sources)) {
          // 来源事件：存起来，不要追加进正文
          onSources(parsed.sources)
        } else if (typeof parsed.content === 'string') {
          // 普通文本块
          onToken(parsed.content)
        }
      } catch {
        /* 忽略无法解析的行 */
      }
    }
  }
}

// 会话列表（侧边栏）
export async function fetchSessions(): Promise<SessionItem[]> {
  const res = await fetch('/api/sessions')
  const data = await res.json()
  return data.sessions ?? []
}

// 会话消息历史
export async function fetchMessages(sessionId: string): Promise<ChatMessage[]> {
  const res = await fetch(`/api/sessions/${encodeURIComponent(sessionId)}/messages`)
  const data = await res.json()
  return data.messages ?? []
}

// 重命名会话
export async function renameSession(sessionId: string, title: string) {
  const res = await fetch(`/api/sessions/${encodeURIComponent(sessionId)}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title }),
  })
  return res.json()
}

// 删除会话（含全部消息）
export async function deleteSession(sessionId: string) {
  const res = await fetch(`/api/sessions/${encodeURIComponent(sessionId)}`, {
    method: 'DELETE',
  })
  return res.json()
}

// 置顶/取消置顶会话
export async function pinSession(sessionId: string, pinned: boolean) {
  const res = await fetch(`/api/sessions/${encodeURIComponent(sessionId)}/pin`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ pinned }),
  })
  return res.json()
}

// 提交反馈（1=点赞，-1=点踩）
export async function submitFeedback(messageId: number, rating: 1 | -1, comment = '') {
  const res = await fetch('/api/feedback', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message_id: messageId, rating, comment }),
  })
  return res.json()
}
