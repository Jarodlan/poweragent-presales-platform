<script setup lang="ts">
import { DocumentCopy, Reading, RefreshRight, WarningFilled } from '@element-plus/icons-vue'
import { computed } from 'vue'

import { copyText } from '@/utils/clipboard'
import { renderMarkdown } from '@/utils/markdown'
import { formatDateTime } from '@/utils/time'
import type { EvidenceCard } from '@/types/conversation'

const props = defineProps<{
  messageId?: string
  summary?: string
  content?: string
  assumptions?: string[]
  evidenceCards?: EvidenceCard[]
  status?: string
  createdAt?: string
}>()

const emit = defineEmits<{
  (e: 'open-evidence', cards: EvidenceCard[]): void
  (e: 'retry', messageId: string): void
}>()

const html = computed(() => renderMarkdown(props.content || ''))
const timeLabel = computed(() => formatDateTime(props.createdAt))
const evidenceCount = computed(() => props.evidenceCards?.length || 0)
const isRunning = computed(() => props.status === 'running')
const isFailed = computed(() => props.status === 'failed')
const isStopped = computed(() => props.status === 'stopped')
const statusText = computed(() => {
  if (isRunning.value) return '进行中'
  if (isFailed.value) return '失败'
  if (isStopped.value) return '已停止'
  return '已完成'
})
const titleText = computed(() => {
  if (isRunning.value) return '方案生成中'
  if (isFailed.value) return '生成失败'
  if (isStopped.value) return '生成已停止'
  return '解决方案输出'
})
const noticeText = computed(() => {
  if (isFailed.value) return '本次生成没有完整完成，你可以直接重新生成，系统会沿用上一条用户需求继续处理。'
  if (isStopped.value) return '你刚刚手动停止了本次任务，当前保留的内容不会丢失，也可以再次发起生成。'
  return ''
})

async function handleCopy(content: string) {
  if (!content) return
  await copyText(content)
}

function handleRetry() {
  if (!props.messageId) return
  emit('retry', props.messageId)
}
</script>

<template>
  <article class="assistant-card panel-card">
    <div class="assistant-card__toolbar">
      <div>
        <p class="section-title">Assistant</p>
        <strong>{{ titleText }}</strong>
        <div class="assistant-card__meta">
          <span :class="['assistant-card__status', `is-${status || 'completed'}`]">
            {{ statusText }}
          </span>
          <time>{{ timeLabel }}</time>
          <span v-if="evidenceCount">{{ evidenceCount }} 条证据</span>
        </div>
      </div>
      <div class="assistant-card__actions">
        <el-button v-if="isFailed || isStopped" text type="primary" @click="handleRetry">
          <el-icon><RefreshRight /></el-icon>
          重新生成
        </el-button>
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

    <section v-if="isFailed || isStopped" class="assistant-card__notice">
      <div class="assistant-card__notice-icon">
        <el-icon><WarningFilled /></el-icon>
      </div>
      <div>
        <strong>{{ isFailed ? '本次生成未完整完成' : '本次生成已被停止' }}</strong>
        <p>{{ noticeText }}</p>
      </div>
    </section>

    <section v-if="isRunning && !content" class="assistant-card__placeholder">
      <div class="assistant-card__placeholder-bar is-wide" />
      <div class="assistant-card__placeholder-bar" />
      <div class="assistant-card__placeholder-bar" />
      <p>系统正在组织长文内容，阶段进度会持续显示在上方状态条。</p>
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

.assistant-card__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 10px;
  color: #8aa0b0;
  font-size: 12px;
}

.assistant-card__status {
  padding: 3px 8px;
  border-radius: 999px;
  font-weight: 700;
}

.assistant-card__status.is-running {
  background: #eef8ee;
  color: var(--success);
}

.assistant-card__status.is-failed {
  background: #fdeeee;
  color: var(--danger);
}

.assistant-card__status.is-stopped {
  background: #fff4de;
  color: #c7820d;
}

.assistant-card__status.is-completed {
  background: #edf3f8;
  color: var(--accent);
}

.assistant-card__actions {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.assistant-card__notice {
  margin-top: 18px;
  padding: 16px 18px;
  border-radius: 18px;
  border: 1px solid rgba(235, 164, 37, 0.18);
  background: linear-gradient(180deg, rgba(255, 250, 239, 0.95) 0%, rgba(255, 246, 225, 0.95) 100%);
  display: flex;
  gap: 14px;
}

.assistant-card__notice-icon {
  flex-shrink: 0;
  color: #c98a10;
  font-size: 20px;
  padding-top: 2px;
}

.assistant-card__notice strong {
  display: block;
  margin-bottom: 6px;
}

.assistant-card__notice p {
  margin: 0;
  color: var(--muted);
  line-height: 1.7;
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

.assistant-card__placeholder {
  margin-top: 18px;
  padding: 18px;
  border-radius: 18px;
  background: linear-gradient(180deg, rgba(250, 252, 254, 0.9) 0%, rgba(241, 247, 251, 0.9) 100%);
  border: 1px solid rgba(15, 93, 140, 0.08);
}

.assistant-card__placeholder p {
  margin: 14px 0 0;
  color: var(--muted);
  line-height: 1.7;
}

.assistant-card__placeholder-bar {
  height: 12px;
  border-radius: 999px;
  background: linear-gradient(90deg, rgba(15, 93, 140, 0.08) 0%, rgba(15, 93, 140, 0.18) 50%, rgba(15, 93, 140, 0.08) 100%);
  margin-bottom: 12px;
  animation: pulseBar 1.6s ease-in-out infinite;
}

.assistant-card__placeholder-bar.is-wide {
  width: 78%;
}

.assistant-card__placeholder-bar:not(.is-wide) {
  width: 100%;
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

:deep(.markdown-body blockquote) {
  margin: 16px 0;
  padding: 12px 16px;
  border-left: 4px solid rgba(15, 93, 140, 0.18);
  background: rgba(15, 93, 140, 0.04);
  color: var(--muted);
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

@keyframes pulseBar {
  0% {
    opacity: 0.65;
  }
  50% {
    opacity: 1;
  }
  100% {
    opacity: 0.65;
  }
}
</style>
