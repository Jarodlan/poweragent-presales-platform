<script setup lang="ts">
import { DocumentCopy, Reading } from '@element-plus/icons-vue'
import { computed } from 'vue'

import { copyText } from '@/utils/clipboard'
import { renderMarkdown } from '@/utils/markdown'
import type { EvidenceCard } from '@/types/conversation'

const props = defineProps<{
  summary?: string
  content?: string
  assumptions?: string[]
  evidenceCards?: EvidenceCard[]
  status?: string
}>()

const emit = defineEmits<{
  (e: 'open-evidence', cards: EvidenceCard[]): void
}>()

const html = computed(() => renderMarkdown(props.content || ''))

async function handleCopy(content: string) {
  if (!content) return
  await copyText(content)
}
</script>

<template>
  <article class="assistant-card panel-card">
    <div class="assistant-card__toolbar">
      <div>
        <p class="section-title">Assistant</p>
        <strong>{{ status === 'running' ? '方案生成中' : '解决方案输出' }}</strong>
      </div>
      <div class="assistant-card__actions">
        <el-button text @click="handleCopy(summary || '')">
          <el-icon><Reading /></el-icon>
          复制摘要
        </el-button>
        <el-button text @click="handleCopy(content || '')">
          <el-icon><DocumentCopy /></el-icon>
          复制全文
        </el-button>
      </div>
    </div>

    <section v-if="summary" class="assistant-card__summary">
      <h3>方案摘要</h3>
      <p>{{ summary }}</p>
    </section>

    <section v-if="content" class="assistant-card__body markdown-body" v-html="html" />

    <section v-if="assumptions?.length" class="assistant-card__assumptions">
      <h3>默认假设</h3>
      <ul>
        <li v-for="item in assumptions" :key="item">{{ item }}</li>
      </ul>
    </section>

    <section v-if="evidenceCards?.length" class="assistant-card__evidence">
      <div class="assistant-card__evidence-head">
        <h3>证据卡</h3>
        <el-button text type="primary" @click="emit('open-evidence', evidenceCards)">查看详情</el-button>
      </div>
      <div class="assistant-card__evidence-grid">
        <button
          v-for="card in evidenceCards.slice(0, 3)"
          :key="`${card.source_type}-${card.title}`"
          class="assistant-card__evidence-item"
          @click="emit('open-evidence', evidenceCards)"
        >
          <span>{{ card.source_type }}</span>
          <strong>{{ card.title || '未命名证据' }}</strong>
          <p>{{ card.summary || '点击查看来源详情' }}</p>
        </button>
      </div>
    </section>
  </article>
</template>

<style scoped>
.assistant-card {
  padding: 22px;
}

.assistant-card__toolbar {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
  margin-bottom: 18px;
}

.assistant-card__toolbar strong {
  display: block;
  margin-top: 6px;
  font-size: 18px;
}

.assistant-card__actions {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.assistant-card__summary,
.assistant-card__assumptions,
.assistant-card__evidence {
  margin-top: 18px;
  padding: 16px 18px;
  border-radius: 18px;
  background: var(--panel-soft);
  border: 1px solid rgba(15, 93, 140, 0.08);
}

.assistant-card__summary h3,
.assistant-card__assumptions h3,
.assistant-card__evidence h3 {
  margin: 0 0 10px;
  font-size: 16px;
}

.assistant-card__summary p {
  margin: 0;
  color: var(--muted);
  line-height: 1.8;
  white-space: pre-wrap;
}

.assistant-card__body {
  padding-top: 6px;
}

.assistant-card__evidence-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.assistant-card__evidence-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 12px;
}

.assistant-card__evidence-item {
  text-align: left;
  border: 1px solid rgba(15, 93, 140, 0.14);
  border-radius: 16px;
  background: white;
  padding: 14px;
  cursor: pointer;
}

.assistant-card__evidence-item span {
  display: inline-block;
  font-size: 11px;
  color: var(--accent);
  text-transform: uppercase;
  margin-bottom: 8px;
}

.assistant-card__evidence-item strong {
  display: block;
  line-height: 1.45;
  margin-bottom: 8px;
}

.assistant-card__evidence-item p {
  margin: 0;
  color: var(--muted);
  line-height: 1.6;
}

:deep(.markdown-body h1),
:deep(.markdown-body h2),
:deep(.markdown-body h3) {
  color: #12354e;
}

:deep(.markdown-body p),
:deep(.markdown-body li) {
  line-height: 1.8;
}

:deep(.markdown-body table) {
  width: 100%;
  border-collapse: collapse;
  margin: 16px 0;
}

:deep(.markdown-body th),
:deep(.markdown-body td) {
  border: 1px solid var(--line);
  padding: 10px 12px;
  text-align: left;
}

@media (max-width: 760px) {
  .assistant-card__toolbar {
    flex-direction: column;
  }
}
</style>
