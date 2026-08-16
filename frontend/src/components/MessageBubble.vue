<script setup lang="ts">
// 消息气泡：用户右、AI 左；AI 消息渲染 Markdown + 来源卡片 + 点赞/点踩
import { computed } from 'vue'
import MarkdownIt from 'markdown-it'
import DOMPurify from 'dompurify'
import SourceCard from './SourceCard.vue'
import type { ChatMessage } from '@/api/chat'
import { submitFeedback } from '@/api/chat'

const props = defineProps<{ message: ChatMessage }>()

// Markdown 渲染器（关闭原生 html，防止注入）
const md = new MarkdownIt({ html: false, breaks: true })

// 渲染 Markdown 后用 DOMPurify 消毒（防 XSS：AI 输出可能包含 <script>）
const html = computed(() => DOMPurify.sanitize(md.render(props.message.content)))

// 点赞/点踩（需要消息 id；历史消息有 id，反馈按钮才显示）
async function feedback(rating: 1 | -1) {
  if (!props.message.id) return
  await submitFeedback(props.message.id, rating)
}
</script>

<template>
  <div class="bubble-row" :class="message.role">
    <!-- 头像 -->
    <div class="avatar" :class="message.role">
      {{ message.role === 'user' ? '🧑' : '🐾' }}
    </div>

    <!-- 气泡 -->
    <div class="bubble" :class="message.role">
      <!-- AI 消息渲染 Markdown，用户消息纯文本 -->
      <div v-if="message.role === 'assistant'" class="md-body" v-html="html" />
      <div v-else class="plain">{{ message.content }}</div>

      <!-- 来源卡片（仅 AI 消息） -->
      <SourceCard v-if="message.role === 'assistant'" :sources="message.sources ?? []" />

      <!-- 反馈按钮（仅 AI 消息且有 id） -->
      <div v-if="message.role === 'assistant' && message.id" class="feedback">
        <button class="fb-btn" title="有用" @click="feedback(1)">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 9V5a3 3 0 0 0-3-3l-4 9v11h11.28a2 2 0 0 0 2-1.7l1.38-9a2 2 0 0 0-2-2.3zM7 22H4a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2h3"/></svg>
        </button>
        <button class="fb-btn" title="没用" @click="feedback(-1)">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10 15v4a3 3 0 0 0 3 3l4-9V2H5.72a2 2 0 0 0-2 1.7l-1.38 9a2 2 0 0 0 2 2.3zm7-13h2.67A2.31 2.31 0 0 1 22 4v7a2.31 2.31 0 0 1-2.33 2H17"/></svg>
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Nunito:wght@400;500;600;700&display=swap');

:root {
  --coral: #C25D3F;
  --coral-hover: #A84E34;
  --sage: #81B29A;
  --brown: #3D322A;
  --brown-light: #8A7E74;
  --cream: #FFFCF8;
  --warm-border: #E8DDD0;
}

/* ── 行布局 ── */
.bubble-row {
  display: flex;
  gap: 10px;
  margin-bottom: 18px;
  align-items: flex-start;
  animation: msgIn 0.35s ease both;
}

.bubble-row.user {
  flex-direction: row-reverse;
}

@keyframes msgIn {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}

/* ── 头像 ── */
.avatar {
  width: 36px;
  height: 36px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 17px;
  flex-shrink: 0;
}

.avatar.assistant {
  background: linear-gradient(135deg, #81B29A, #6A9B82);
  box-shadow: 0 2px 8px rgba(129, 178, 154, 0.3);
}

.avatar.user {
  background: linear-gradient(135deg, #E07A5F, #D06A50);
  box-shadow: 0 2px 8px rgba(224, 122, 95, 0.3);
}

/* ── 气泡 ── */
.bubble {
  max-width: 70%;
  padding: 12px 16px;
  border-radius: 16px;
  font-size: 14px;
  line-height: 1.65;
}

.bubble.assistant {
  background: var(--cream);
  color: var(--brown);
  border-top-left-radius: 4px;
  box-shadow: 0 1px 4px rgba(61, 50, 42, 0.06);
}

.bubble.user {
  background: #F5E6E0;
  color: #3D322A;
  border-top-right-radius: 4px;
  box-shadow: 0 1px 4px rgba(61, 50, 42, 0.06);
}

/* ── Markdown 排版 ── */
.md-body :deep(p) {
  margin: 4px 0;
}

.md-body :deep(p:first-child) {
  margin-top: 0;
}

.md-body :deep(p:last-child) {
  margin-bottom: 0;
}

.md-body :deep(ul),
.md-body :deep(ol) {
  padding-left: 20px;
  margin: 6px 0;
}

.md-body :deep(li) {
  margin: 2px 0;
}

.md-body :deep(code) {
  background: rgba(0, 0, 0, 0.05);
  padding: 1px 5px;
  border-radius: 4px;
  font-size: 13px;
}

.md-body :deep(pre) {
  background: #2D2A24;
  color: #E8DDD0;
  padding: 12px 14px;
  border-radius: 10px;
  overflow-x: auto;
  margin: 8px 0;
}

.md-body :deep(pre code) {
  background: none;
  padding: 0;
  color: inherit;
  font-size: 13px;
}

.md-body :deep(strong) {
  font-weight: 700;
}

.md-body :deep(h1),
.md-body :deep(h2),
.md-body :deep(h3) {
  margin: 10px 0 4px;
  font-weight: 700;
}

.md-body :deep(h1) { font-size: 18px; }
.md-body :deep(h2) { font-size: 16px; }
.md-body :deep(h3) { font-size: 15px; }

.md-body :deep(blockquote) {
  border-left: 3px solid var(--coral-light);
  padding-left: 12px;
  margin: 8px 0;
  color: var(--brown-light);
}

.md-body :deep(a) {
  color: var(--coral);
  text-decoration: underline;
}

.md-body :deep(hr) {
  border: none;
  border-top: 1px solid var(--warm-border);
  margin: 12px 0;
}

/* ── 纯文本 ── */
.plain {
  white-space: pre-wrap;
  word-break: break-word;
}

/* ── 反馈按钮 ── */
.feedback {
  margin-top: 8px;
  display: flex;
  gap: 4px;
}

.fb-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border: none;
  background: none;
  border-radius: 8px;
  cursor: pointer;
  color: var(--brown-light);
  transition: all 0.15s ease;
  opacity: 0.5;
}

.fb-btn:hover {
  opacity: 1;
  background: rgba(0, 0, 0, 0.04);
  color: var(--coral);
}
</style>
