<script setup lang="ts">
import type { EvidenceCard } from '@/types/conversation'

const props = defineProps<{
  modelValue: boolean
  items: EvidenceCard[]
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
}>()
</script>

<template>
  <el-drawer
    :model-value="props.modelValue"
    size="420px"
    title="证据来源详情"
    @update:model-value="emit('update:modelValue', $event)"
  >
    <div class="evidence-drawer">
      <article v-for="item in props.items" :key="`${item.source_type}-${item.title}`" class="evidence-drawer__item">
        <span>{{ item.source_type }}</span>
        <h3>{{ item.title || '未命名证据' }}</h3>
        <p>{{ item.summary || '暂无摘要' }}</p>
        <pre>{{ JSON.stringify(item.metadata || {}, null, 2) }}</pre>
      </article>
    </div>
  </el-drawer>
</template>

<style scoped>
.evidence-drawer {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.evidence-drawer__item {
  padding: 14px;
  border-radius: 18px;
  background: var(--panel-soft);
  border: 1px solid rgba(15, 93, 140, 0.08);
}

.evidence-drawer__item span {
  font-size: 11px;
  text-transform: uppercase;
  color: var(--accent);
}

.evidence-drawer__item h3 {
  margin: 8px 0;
  font-size: 16px;
}

.evidence-drawer__item p {
  margin: 0 0 10px;
  line-height: 1.65;
  color: var(--muted);
}

.evidence-drawer__item pre {
  white-space: pre-wrap;
  margin: 0;
  padding: 10px;
  border-radius: 12px;
  background: white;
  color: #456;
  font-size: 12px;
}
</style>
