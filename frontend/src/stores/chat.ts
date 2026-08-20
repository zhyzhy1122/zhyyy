// 聊天状态管理（Pinia）
import { defineStore } from 'pinia'
import { ref } from 'vue'
import {
  streamChat,
  fetchSessions,
  fetchMessages,
  renameSession as renameSessionApi,
  deleteSession as deleteSessionApi,
  pinSession as pinSessionApi,
  type ChatMessage,
  type SessionItem,
} from '@/api/chat'

export const useChatStore = defineStore('chat', () => {
  // 会话列表（侧边栏）
  const sessions = ref<SessionItem[]>([])
  // 当前会话 ID（localStorage 持久化，刷新不丢）
  const sessionId = ref(localStorage.getItem('session_id') ?? crypto.randomUUID())
  // 当前会话的消息列表
  const messages = ref<ChatMessage[]>([])
  // 是否正在生成（用于禁用输入框/按钮）
  const streaming = ref(false)

  // 保存会话 ID 到 localStorage
  function saveSessionId() {
    localStorage.setItem('session_id', sessionId.value)
  }

  // 加载会话列表
  async function loadSessions() {
    sessions.value = await fetchSessions()
  }

  // 切换/加载某个会话的历史
  async function loadSession(id: string) {
    sessionId.value = id
    saveSessionId()
    messages.value = await fetchMessages(id)
  }

  // 新建会话
  function newSession() {
    sessionId.value = crypto.randomUUID()
    saveSessionId()
    messages.value = []
  }

  // 删除会话（删当前会话时自动新建）
  async function removeSession(id: string) {
    await deleteSessionApi(id)
    if (sessionId.value === id) {
      newSession()
    }
    loadSessions()
  }

  // 重命名会话
  async function renameSession(id: string, title: string) {
    await renameSessionApi(id, title)
    loadSessions()
  }

  // 置顶/取消置顶
  async function togglePin(s: SessionItem) {
    await pinSessionApi(s.session_id, !s.is_pinned)
    loadSessions()
  }

  // 发送问题（流式输出）
  async function send(question: string) {
    // 用户消息立即显示
    messages.value.push({ role: 'user', content: question })
    // 占位 AI 消息
    messages.value.push({ role: 'assistant', content: '' })
    // ★ 关键：从数组里取引用（push 后数组里是 reactive 代理）
    // 直接修改代理的属性才能触发 Vue 更新；如果修改原始对象，界面不会刷新
    // ! 非空断言：刚 push 过，最后一项必然存在
    const aiMsg = messages.value[messages.value.length - 1]!
    streaming.value = true

    const controller = new AbortController()
    try {
      await streamChat(
        question,
        sessionId.value,
        (t) => {
          aiMsg.content += t // 通过代理修改 → 触发流式渲染
        },
        controller.signal,
      )
    } catch (e) {
      if (!controller.signal.aborted) {
        aiMsg.content = (aiMsg.content || '') + '（出错了，请重试）'
      }
    } finally {
      streaming.value = false
      // 刷新会话列表 + 重新拉取历史（让消息带上 id，反馈按钮才可用）
      loadSessions()
      loadSession(sessionId.value)
    }
  }

  return {
    sessions,
    sessionId,
    messages,
    streaming,
    loadSessions,
    loadSession,
    newSession,
    removeSession,
    renameSession,
    togglePin,
    send,
  }
})
