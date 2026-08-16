<script setup lang="ts">
// 聊天页：左侧会话列表（侧边栏），右侧聊天窗口
// 会话项支持右键菜单：置顶 / 重命名 / 删除
import { onMounted, ref, nextTick, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessageBox } from 'element-plus'
import { useChatStore } from '@/stores/chat'
import MessageBubble from '@/components/MessageBubble.vue'
import type { SessionItem } from '@/api/chat'

const chat = useChatStore()
const router = useRouter()
const input = ref('')
const listRef = ref<HTMLElement>()

// 重命名弹窗状态
const renameVisible = ref(false)
const renameTarget = ref<SessionItem | null>(null)
const renameTitle = ref('')

// 进入页面加载会话列表
onMounted(() => {
  chat.loadSessions()
})

// 流式期间消息内容变化时自动滚动到底部
watch(
  () => chat.messages.map((m) => m.content).join(''),
  () => scrollBottom(),
)

// 发送问题
async function send() {
  const q = input.value.trim()
  if (!q || chat.streaming) return
  input.value = ''
  await chat.send(q)
  scrollBottom()
}

// 点击建议问题快捷发送
function sendSuggestion(text: string) {
  input.value = text
  send()
}

// 滚动到消息区底部
function scrollBottom() {
  nextTick(() => {
    listRef.value?.scrollTo({ top: listRef.value.scrollHeight })
  })
}

// 右键菜单命令处理：pin=置顶 / rename=重命名 / delete=删除
async function handleMenu(s: SessionItem, cmd: string) {
  if (cmd === 'pin') {
    await chat.togglePin(s)
  } else if (cmd === 'rename') {
    renameTarget.value = s
    renameTitle.value = s.title
    renameVisible.value = true
  } else if (cmd === 'delete') {
    await ElMessageBox.confirm(`确定删除会话「${s.title}」吗？删除后不可恢复。`, '删除确认', {
      type: 'warning',
    })
    await chat.removeSession(s.session_id)
  }
}

// 确认重命名
async function confirmRename() {
  if (!renameTarget.value || !renameTitle.value.trim()) return
  await chat.renameSession(renameTarget.value.session_id, renameTitle.value.trim())
  renameVisible.value = false
}
</script>

<template>
  <div class="chat-page">
    <!-- ═══ 侧边栏 ═══ -->
    <aside class="sidebar">
      <div class="sidebar-brand">
        <span class="brand-icon">🐾</span>
        <span class="brand-text">萌宠之家</span>
        <el-tooltip content="显示参考资料" placement="bottom">
          <el-switch
            v-model="chat.showSources"
            size="small"
            @change="chat.setShowSources(chat.showSources)"
          />
        </el-tooltip>
      </div>

      <button class="new-chat-btn" @click="chat.newSession()">
        <span class="btn-icon">+</span>
        <span>新建对话</span>
      </button>

      <div class="session-list">
        <el-dropdown
          v-for="s in chat.sessions"
          :key="s.session_id"
          trigger="contextmenu"
          @command="(cmd: string) => handleMenu(s, cmd)"
        >
          <div
            class="session-item"
            :class="{ active: s.session_id === chat.sessionId }"
            @click="chat.loadSession(s.session_id)"
          >
            <span v-if="s.is_pinned" class="pin-icon">📌</span>
            <span class="session-title">{{ s.title }}</span>
            <span class="session-count">{{ s.message_count }}</span>
          </div>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="pin">
                {{ s.is_pinned ? '取消置顶' : '置顶' }}
              </el-dropdown-item>
              <el-dropdown-item command="rename">重命名</el-dropdown-item>
              <el-dropdown-item command="delete" divided>删除会话</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>

      <button class="admin-link" @click="router.push('/admin')">
        <span>⚙️</span>
        <span>管理后台</span>
      </button>
    </aside>

    <!-- ═══ 聊天区 ═══ -->
    <main class="chat-area">
      <div ref="listRef" class="msg-list">
        <!-- 空状态 -->
        <div v-if="chat.messages.length === 0" class="empty-state">
          <div class="empty-mascot">🐱</div>
          <h2 class="empty-title">你好呀，欢迎来到萌宠之家</h2>
          <p class="empty-sub">我是你的 AI 宠物顾问，有什么可以帮你的？</p>
          <div class="suggestion-chips">
            <button class="chip" @click="sendSuggestion('寄养价格是多少？')">💰 寄养价格</button>
            <button class="chip" @click="sendSuggestion('有哪些洗澡美容服务？')"> 洗澡美容</button>
            <button class="chip" @click="sendSuggestion('日常宠物养护有什么建议？')">🐕 养护建议</button>
            <button class="chip" @click="sendSuggestion('怎么预约你们的服务？')">📅 预约方式</button>
          </div>
        </div>

        <MessageBubble v-for="(m, i) in chat.messages" :key="i" :message="m" />

        <!-- 流式加载指示器 -->
        <div v-if="chat.streaming && chat.messages.length > 0 && chat.messages[chat.messages.length - 1]?.content === ''" class="thinking">
          <div class="thinking-avatar">🐾</div>
          <div class="thinking-dots">
            <span></span><span></span><span></span>
          </div>
        </div>
      </div>

      <div class="input-bar">
        <div class="input-wrapper">
          <el-input
            v-model="input"
            placeholder="输入你的问题，Enter 发送…"
            :disabled="chat.streaming"
            @keyup.enter="send"
          />
          <button class="send-btn" :class="{ loading: chat.streaming }" :disabled="chat.streaming || !input.trim()" @click="send">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
              <line x1="22" y1="2" x2="11" y2="13" /><polygon points="22 2 15 22 11 13 2 9 22 2" />
            </svg>
          </button>
        </div>
      </div>
    </main>

    <!-- ═══ 重命名弹窗 ═══ -->
    <el-dialog v-model="renameVisible" title="重命名会话" width="400px">
      <el-input v-model="renameTitle" placeholder="输入新的会话名称" @keyup.enter="confirmRename" />
      <template #footer>
        <el-button @click="renameVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmRename">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Nunito:wght@400;500;600;700;800&display=swap');

/* ═══ 布局 ═══ */
.chat-page {
  display: flex;
  height: 100vh;
  background: #F5F1EC;
}

/* ═══ 侧边栏 — 深色，与亮色聊天区形成对比 ═══ */
.sidebar {
  width: 270px;
  background: #2C2420;
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
}

.sidebar-brand {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 18px 18px 16px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.brand-icon {
  font-size: 22px;
}

.brand-text {
  flex: 1;
  font-size: 17px;
  font-weight: 800;
  color: #F5F1EC;
  letter-spacing: 0.5px;
}

/* 新建对话按钮 */
.new-chat-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 14px 14px 12px;
  padding: 11px 18px;
  background: #C25D3F;
  color: #fff;
  border: none;
  border-radius: 12px;
  font-size: 14px;
  font-weight: 700;
  font-family: inherit;
  cursor: pointer;
  transition: all 0.2s ease;
  box-shadow: 0 2px 10px rgba(194, 93, 63, 0.35);
}

.new-chat-btn:hover {
  background: #A84E34;
  transform: translateY(-1px);
  box-shadow: 0 4px 16px rgba(194, 93, 63, 0.45);
}

.btn-icon {
  font-size: 18px;
  font-weight: 400;
  line-height: 1;
}

/* ═══ 会话列表 — 等宽等高卡片，纵向排列 ═══ */
.session-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px 12px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.session-item {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  min-height: 42px;
  padding: 10px 14px;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.18s ease;
  background: rgba(255, 255, 255, 0.07);
  border: 1px solid rgba(255, 255, 255, 0.05);
  color: #D4CBC2;
  box-sizing: border-box;
}

.session-item:hover {
  background: rgba(255, 255, 255, 0.12);
  border-color: rgba(255, 255, 255, 0.12);
  color: #F0EBE5;
}

.session-item.active {
  background: rgba(194, 93, 63, 0.22);
  border-color: rgba(194, 93, 63, 0.4);
  color: #F5F1EC;
  font-weight: 600;
  box-shadow: 0 2px 10px rgba(194, 93, 63, 0.18);
}

.pin-icon {
  font-size: 11px;
  flex-shrink: 0;
}

.session-title {
  flex: 1;
  font-size: 13px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  min-width: 0;
}

.session-count {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.3);
  background: rgba(255, 255, 255, 0.08);
  padding: 2px 8px;
  border-radius: 8px;
  flex-shrink: 0;
  font-weight: 500;
}

.session-item.active .session-count {
  color: rgba(255, 255, 255, 0.55);
  background: rgba(255, 255, 255, 0.12);
}

/* 管理后台链接 */
.admin-link {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 8px 14px 14px;
  padding: 10px 14px;
  background: transparent;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 10px;
  font-size: 13px;
  font-weight: 600;
  font-family: inherit;
  color: #A89E94;
  cursor: pointer;
  transition: all 0.15s ease;
}

.admin-link:hover {
  background: rgba(255, 255, 255, 0.08);
  color: #D4CBC2;
}

/* ═══ 聊天区 — 亮色背景，深色文字 ═══ */
.chat-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  background: linear-gradient(175deg, #FDF9F5 0%, #F5F0EB 50%, #F0EBE5 100%);
}

.msg-list {
  flex: 1;
  overflow-y: auto;
  padding: 24px 32px;
}

/* ═══ 空状态 ═══ */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  padding-bottom: 40px;
  animation: fadeInUp 0.5s ease;
}

.empty-mascot {
  font-size: 56px;
  margin-bottom: 12px;
  animation: gentleBounce 2.5s ease-in-out infinite;
}

.empty-title {
  font-size: 22px;
  font-weight: 800;
  color: #3D322A;
  margin-bottom: 6px;
}

.empty-sub {
  font-size: 14px;
  color: #8A7E74;
  margin-bottom: 28px;
}

.suggestion-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: center;
  max-width: 520px;
}

.chip {
  padding: 8px 18px;
  background: #FFFCF8;
  border: 1.5px solid #E8DDD0;
  border-radius: 20px;
  font-size: 13px;
  font-weight: 600;
  font-family: inherit;
  color: #3D322A;
  cursor: pointer;
  transition: all 0.2s ease;
}

.chip:hover {
  border-color: #C25D3F;
  color: #C25D3F;
  background: #FFF5F0;
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(194, 93, 63, 0.12);
}

/* ═══ 思考指示器 ═══ */
.thinking {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 8px;
  margin-bottom: 16px;
  animation: fadeIn 0.3s ease;
}

.thinking-avatar {
  width: 36px;
  height: 36px;
  border-radius: 12px;
  background: linear-gradient(135deg, #81B29A, #6A9B82);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  color: #fff;
  box-shadow: 0 2px 8px rgba(129, 178, 154, 0.3);
}

.thinking-dots {
  display: flex;
  gap: 4px;
  padding: 12px 16px;
  background: #FFFCF8;
  border-radius: 16px;
  border-top-left-radius: 4px;
  box-shadow: 0 1px 4px rgba(61, 50, 42, 0.06);
}

.thinking-dots span {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #D4917A;
  animation: dotBounce 1.4s ease-in-out infinite;
}

.thinking-dots span:nth-child(2) { animation-delay: 0.16s; }
.thinking-dots span:nth-child(3) { animation-delay: 0.32s; }

/* ═══ 输入区 ═══ */
.input-bar {
  padding: 14px 32px 18px;
  background: rgba(255, 252, 248, 0.85);
  backdrop-filter: blur(12px);
  border-top: 1px solid #E8DDD0;
}

.input-wrapper {
  display: flex;
  align-items: center;
  gap: 10px;
  max-width: 820px;
  margin: 0 auto;
}

.input-wrapper :deep(.el-input) {
  flex: 1;
}

.send-btn {
  width: 40px;
  height: 40px;
  border-radius: 12px;
  background: #C25D3F;
  color: #fff;
  border: none;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s ease;
  flex-shrink: 0;
  box-shadow: 0 2px 8px rgba(194, 93, 63, 0.3);
}

.send-btn:hover:not(:disabled) {
  background: #A84E34;
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(194, 93, 63, 0.4);
}

.send-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
  transform: none;
}

.send-btn.loading svg {
  animation: spin 1s linear infinite;
}

/* ═══ 动画 ═══ */
@keyframes fadeInUp {
  from { opacity: 0; transform: translateY(16px); }
  to { opacity: 1; transform: translateY(0); }
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

@keyframes gentleBounce {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-6px); }
}

@keyframes dotBounce {
  0%, 80%, 100% { transform: scale(0.6); opacity: 0.4; }
  40% { transform: scale(1); opacity: 1; }
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>
