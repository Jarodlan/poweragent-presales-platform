<script setup lang="ts">
import { DocumentCopy, Search, Tickets } from '@element-plus/icons-vue'
import { computed, ref, watch } from 'vue'

import { copyText } from '@/utils/clipboard'
import type { EvidenceCard } from '@/types/conversation'

const props = defineProps<{
  modelValue: boolean
  items: EvidenceCard[]
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
}>()

const keyword = ref('')
const activeSource = ref<'all' | string>('all')
const activeKey = ref('')

const sourceOptions = computed(() => {
  const counts = new Map<string, number>()
  for (const item of props.items) {
    counts.set(item.source_type, (counts.get(item.source_type) || 0) + 1)
  }
  return [
    { value: 'all', label: '全部', count: props.items.length },
    ...Array.from(counts.entries()).map(([value, count]) => ({
      value,
      label: sourceLabel(value),
      count,
    })),
  ]
})

const filteredItems = computed(() => {
  const normalized = keyword.value.trim().toLowerCase()
  return props.items.filter((item) => {
    const matchSource = activeSource.value === 'all' || item.source_type === activeSource.value
    if (!matchSource) return false
    if (!normalized) return true
    return [item.title, item.summary, item.source_type, JSON.stringify(item.metadata || {})]
      .join(' ')
      .toLowerCase()
      .includes(normalized)
  })
})

const activeItem = computed(() => {
  return filteredItems.value.find((item) => cardKey(item) === activeKey.value) || filteredItems.value[0] || null
})

const activeMetadata = computed(() => formatMetadata(activeItem.value?.metadata))
const activeSummary = computed(() => prettifyText(activeItem.value?.summary || '暂无摘要'))
const primaryFacts = computed(() => summarizePrimaryFacts(activeItem.value))
const technicalMetadata = computed(() => activeMetadata.value.filter((item) => !item.primary))

watch(
  filteredItems,
  (items) => {
    if (!items.length) {
      activeKey.value = ''
      return
    }
    if (!items.some((item) => cardKey(item) === activeKey.value)) {
      activeKey.value = cardKey(items[0])
    }
  },
  { immediate: true },
)

watch(
  () => props.modelValue,
  (visible) => {
    if (!visible) {
      keyword.value = ''
      activeSource.value = 'all'
    }
  },
)

function cardKey(item: EvidenceCard) {
  return [
    item.source_type,
    item.title || '',
    item.summary || '',
    item.metadata?.document_id || '',
    item.metadata?.dataset_id || '',
    JSON.stringify(item.metadata?.positions || ''),
  ].join('::')
}

function sourceLabel(value: string) {
  const map: Record<string, string> = {
    solution: '解决方案',
    case: '案例',
    paper: '文献',
    standard: '标准',
  }
  return map[value] || value
}

function formatMetadata(metadata?: Record<string, unknown>) {
  if (!metadata) return []

  const preferredKeys = ['positions', 'dataset_id', 'document_id', 'score']
  const ordered = Object.entries(metadata).sort(([a], [b]) => {
    const aIndex = preferredKeys.indexOf(a)
    const bIndex = preferredKeys.indexOf(b)
    if (aIndex === -1 && bIndex === -1) return a.localeCompare(b)
    if (aIndex === -1) return 1
    if (bIndex === -1) return -1
    return aIndex - bIndex
  })

  return ordered.map(([key, value]) => ({
    key,
    label: metadataLabel(key),
    primary: ['positions', 'dataset_id', 'document_id'].includes(key),
    value: formatMetadataValue(key, value),
  }))
}

function itemIntro(item: EvidenceCard) {
  return prettifyText(item.summary || '暂无摘要')
}

async function copyEvidence(item: EvidenceCard) {
  await copyText([item.title, item.summary, JSON.stringify(item.metadata || {}, null, 2)].filter(Boolean).join('\n\n'))
}

async function copyCitation(item: EvidenceCard) {
  const segments = [
    `来源类型：${sourceLabel(item.source_type)}`,
    item.title ? `标题：${item.title}` : '',
    item.summary ? `摘要：${item.summary}` : '',
    item.metadata?.document_id ? `文档ID：${item.metadata.document_id}` : '',
    item.metadata?.dataset_id ? `数据集ID：${item.metadata.dataset_id}` : '',
  ].filter(Boolean)
  await copyText(segments.join('\n'))
}

function selectItem(item: EvidenceCard) {
  activeKey.value = cardKey(item)
}

function metadataLabel(key: string) {
  const map: Record<string, string> = {
    dataset_id: '数据集',
    document_id: '文档ID',
    positions: '命中位置',
    score: '相关度',
  }
  return map[key] || key
}

function formatMetadataValue(key: string, value: unknown) {
  if (key === 'positions') {
    return extractPositionLabel(value)
  }
  if (Array.isArray(value) || typeof value === 'object') {
    return JSON.stringify(value, null, 2)
  }
  return String(value)
}

function extractPositionLabel(value: unknown) {
  if (!Array.isArray(value) || !value.length) return '未提供'
  const first = value[0]
  if (Array.isArray(first) && typeof first[0] === 'number') {
    return `第 ${first[0]} 页`
  }
  return JSON.stringify(value)
}

function prettifyText(value: string) {
  return value.replace(/\s+/g, ' ').replace(/\s([,.，。；：])/g, '$1').trim()
}

function summarizePrimaryFacts(item: EvidenceCard | null) {
  if (!item) return []
  const metadata = formatMetadata(item.metadata)
  return metadata.filter((entry) => entry.primary)
}
</script>

<template>
  <el-drawer
    :model-value="props.modelValue"
    size="760px"
    title="证据来源详情"
    @update:model-value="emit('update:modelValue', $event)"
  >
    <div class="evidence-drawer">
      <div class="evidence-drawer__toolbar">
        <div class="evidence-drawer__count">
          <strong>{{ props.items.length }}</strong>
          <span>条证据</span>
        </div>
        <el-input v-model="keyword" clearable placeholder="搜索标题、摘要或元数据">
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
      </div>

      <div class="evidence-drawer__filters">
        <button
          v-for="item in sourceOptions"
          :key="item.value"
          :class="['evidence-drawer__filter', { 'is-active': activeSource === item.value }]"
          @click="activeSource = item.value"
        >
          <span>{{ item.label }}</span>
          <strong>{{ item.count }}</strong>
        </button>
      </div>

      <div v-if="!filteredItems.length" class="evidence-drawer__empty">
        <strong>没有匹配到证据</strong>
        <p>可以尝试搜索文档标题、摘要关键词或切换证据类型。</p>
      </div>

      <div v-else class="evidence-drawer__layout">
        <aside class="evidence-drawer__list">
          <button
            v-for="item in filteredItems"
            :key="cardKey(item)"
            :class="['evidence-drawer__list-item', { 'is-active': activeItem && cardKey(item) === cardKey(activeItem) }]"
            @click="selectItem(item)"
          >
            <div class="evidence-drawer__list-meta">
              <span>{{ sourceLabel(item.source_type) }}</span>
              <small v-if="item.metadata?.dataset_id">知识库</small>
            </div>
            <strong>{{ item.title || '未命名证据' }}</strong>
            <p>{{ itemIntro(item) }}</p>
          </button>
        </aside>

        <section v-if="activeItem" class="evidence-drawer__detail panel-card">
          <div class="evidence-drawer__detail-head">
            <div>
              <div class="evidence-drawer__detail-labels">
                <span>{{ sourceLabel(activeItem.source_type) }}</span>
                <small v-if="activeItem.metadata?.dataset_id">知识库来源</small>
              </div>
              <h3>{{ activeItem.title || '未命名证据' }}</h3>
            </div>
            <div class="evidence-drawer__detail-actions">
              <el-button text @click="copyCitation(activeItem)">
                <el-icon><Tickets /></el-icon>
                复制引用
              </el-button>
              <el-button text @click="copyEvidence(activeItem)">
                <el-icon><DocumentCopy /></el-icon>
                复制全文
              </el-button>
            </div>
          </div>

          <div v-if="primaryFacts.length" class="evidence-drawer__fact-row">
            <div
              v-for="fact in primaryFacts"
              :key="`${activeItem.title}-${fact.key}`"
              class="evidence-drawer__fact-chip"
            >
              <strong>{{ fact.label }}</strong>
              <span>{{ fact.value }}</span>
            </div>
          </div>

          <div class="evidence-drawer__summary-block">
            <strong>摘要</strong>
            <p>{{ activeSummary }}</p>
          </div>

          <details v-if="technicalMetadata.length" class="evidence-drawer__technical">
            <summary>查看技术字段</summary>
            <div class="evidence-drawer__meta-grid">
              <div
                v-for="meta in technicalMetadata"
                :key="`${activeItem.title}-${meta.key}`"
                class="evidence-drawer__meta-item"
              >
                <strong>{{ meta.label }}</strong>
                <code>{{ meta.value }}</code>
              </div>
            </div>
          </details>
        </section>
      </div>
    </div>
  </el-drawer>
</template>

<style scoped>
.evidence-drawer {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.evidence-drawer__toolbar {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: 14px;
  align-items: center;
}

.evidence-drawer__count {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 84px;
}

.evidence-drawer__count strong {
  font-size: 24px;
  line-height: 1;
  color: var(--accent);
}

.evidence-drawer__count span {
  color: var(--muted);
  font-size: 12px;
}

.evidence-drawer__filters {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.evidence-drawer__filter {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border-radius: 999px;
  border: 1px solid rgba(15, 93, 140, 0.1);
  background: white;
  cursor: pointer;
  transition: 0.18s ease;
}

.evidence-drawer__filter span {
  color: var(--muted);
  font-size: 12px;
}

.evidence-drawer__filter strong {
  color: var(--accent);
  font-size: 12px;
}

.evidence-drawer__filter.is-active {
  background: rgba(15, 93, 140, 0.08);
  border-color: rgba(15, 93, 140, 0.18);
}

.evidence-drawer__empty {
  padding: 18px;
  border-radius: 18px;
  background: var(--panel-soft);
  border: 1px solid rgba(15, 93, 140, 0.08);
}

.evidence-drawer__empty strong {
  display: block;
  margin-bottom: 8px;
}

.evidence-drawer__empty p {
  margin: 0;
  color: var(--muted);
  line-height: 1.6;
}

.evidence-drawer__layout {
  display: grid;
  grid-template-columns: minmax(240px, 280px) minmax(0, 1fr);
  gap: 14px;
  min-height: 420px;
}

.evidence-drawer__list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  max-height: 72vh;
  overflow: auto;
  padding-right: 4px;
}

.evidence-drawer__list-item {
  text-align: left;
  padding: 14px;
  border-radius: 18px;
  background: var(--panel-soft);
  border: 1px solid rgba(15, 93, 140, 0.08);
  cursor: pointer;
  transition: border-color 0.18s ease, transform 0.18s ease, box-shadow 0.18s ease;
}

.evidence-drawer__list-item:hover,
.evidence-drawer__list-item.is-active {
  border-color: rgba(15, 93, 140, 0.22);
  box-shadow: 0 10px 20px rgba(15, 38, 56, 0.06);
}

.evidence-drawer__list-item.is-active {
  transform: translateY(-1px);
  background: linear-gradient(180deg, rgba(245, 250, 253, 0.96) 0%, rgba(239, 247, 251, 0.96) 100%);
}

.evidence-drawer__list-meta,
.evidence-drawer__detail-labels {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 8px;
}

.evidence-drawer__list-meta span,
.evidence-drawer__detail-labels span {
  font-size: 11px;
  text-transform: uppercase;
  color: var(--accent);
}

.evidence-drawer__list-meta small,
.evidence-drawer__detail-labels small {
  padding: 3px 6px;
  border-radius: 999px;
  background: rgba(15, 93, 140, 0.08);
  color: #6f8797;
  font-size: 11px;
}

.evidence-drawer__list-item strong {
  display: block;
  line-height: 1.5;
  margin-bottom: 8px;
}

.evidence-drawer__list-item p {
  margin: 0;
  color: var(--muted);
  line-height: 1.65;
  display: -webkit-box;
  -webkit-line-clamp: 4;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.evidence-drawer__detail {
  padding: 18px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.evidence-drawer__detail-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
}

.evidence-drawer__detail-head h3 {
  margin: 0;
  font-size: 18px;
  line-height: 1.45;
}

.evidence-drawer__detail-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.evidence-drawer__fact-row {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.evidence-drawer__fact-chip {
  display: inline-flex;
  flex-direction: column;
  gap: 4px;
  padding: 10px 12px;
  border-radius: 14px;
  background: rgba(15, 93, 140, 0.06);
  border: 1px solid rgba(15, 93, 140, 0.08);
}

.evidence-drawer__fact-chip strong {
  font-size: 11px;
  color: var(--accent);
}

.evidence-drawer__fact-chip span {
  font-size: 13px;
  color: var(--text);
}

.evidence-drawer__summary-block {
  padding: 16px 18px;
  border-radius: 18px;
  background: var(--panel-soft);
  border: 1px solid rgba(15, 93, 140, 0.08);
}

.evidence-drawer__summary-block strong {
  display: block;
  margin-bottom: 8px;
}

.evidence-drawer__summary-block p {
  margin: 0;
  line-height: 1.75;
  color: var(--muted);
  white-space: pre-wrap;
}

.evidence-drawer__technical {
  border-top: 1px dashed rgba(15, 93, 140, 0.12);
  padding-top: 14px;
}

.evidence-drawer__technical summary {
  cursor: pointer;
  color: var(--muted);
  font-size: 13px;
  margin-bottom: 12px;
}

.evidence-drawer__meta-grid {
  display: grid;
  gap: 10px;
}

.evidence-drawer__meta-item {
  padding: 12px 14px;
  border-radius: 14px;
  background: white;
  border: 1px solid rgba(15, 93, 140, 0.08);
}

.evidence-drawer__meta-item strong {
  display: block;
  margin-bottom: 6px;
  color: #456;
  font-size: 12px;
}

.evidence-drawer__meta-item code {
  display: block;
  white-space: pre-wrap;
  word-break: break-word;
  color: var(--text);
  font-size: 12px;
  line-height: 1.6;
}

@media (max-width: 960px) {
  .evidence-drawer__toolbar,
  .evidence-drawer__layout,
  .evidence-drawer__detail-head {
    grid-template-columns: 1fr;
    flex-direction: column;
  }

  .evidence-drawer__list {
    max-height: 32vh;
  }

  .evidence-drawer__detail-actions {
    width: 100%;
    justify-content: flex-start;
  }
}
</style>
