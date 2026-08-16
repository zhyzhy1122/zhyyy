<script setup lang="ts">
// 来源卡片：展示 AI 回答参考了哪些文档（doc_id / title / snippet）
import type { SourceItem } from '@/api/chat'

defineProps<{ sources: SourceItem[] }>()
</script>

<template>
  <div v-if="sources.length" class="source-card">
    <div class="source-header">
      <span class="source-icon">📎</span>
      <span class="source-label">参考来源</span>
    </div>
    <div v-for="(s, i) in sources" :key="i" class="source-item">
      <span class="source-index">{{ i + 1 }}</span>
      <div class="source-body">
        <div class="source-name">{{ s.title }}</div>
        <div class="source-snippet">{{ s.snippet }}</div>
      </div>
    </div>
  </div>
</template>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Nunito:wght@400;500;600;700&display=swap');

:root {
  --coral: #E07A5F;
  --brown: #3D322A;
  --brown-light: #8A7E74;
}

.source-card {
  margin-top: 10px;
  padding: 10px 14px;
  background: #F8F4EE;
  border-radius: 10px;
  border: 1px solid #EDE6DC;
}

.source-header {
  display: flex;
  align-items: center;
  gap: 5px;
  margin-bottom: 8px;
}

.source-icon {
  font-size: 13px;
}

.source-label {
  font-size: 12px;
  font-weight: 700;
  color: var(--brown-light);
  letter-spacing: 0.3px;
}

.source-item {
  display: flex;
  gap: 8px;
  padding: 5px 0;
  align-items: flex-start;
}

.source-item + .source-item {
  border-top: 1px solid rgba(0, 0, 0, 0.04);
}

.source-index {
  width: 20px;
  height: 20px;
  line-height: 20px;
  text-align: center;
  background: var(--coral);
  color: #fff;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 700;
  flex-shrink: 0;
  margin-top: 1px;
}

.source-body {
  min-width: 0;
  flex: 1;
}

.source-name {
  font-size: 13px;
  font-weight: 700;
  color: var(--brown);
  line-height: 1.3;
}

.source-snippet {
  font-size: 12px;
  color: var(--brown-light);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  margin-top: 1px;
  line-height: 1.4;
}
</style>
