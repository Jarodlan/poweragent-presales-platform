<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'

import { fetchCrmWritebackRecords } from '@/api/crm'
import type { CrmWritebackRecordItem } from '@/types/crm'
import { formatDateTime } from '@/utils/time'

const props = defineProps<{
  modelValue: boolean
  objectType: string
  objectId: string
}>()

const emit = defineEmits<{
  'update:modelValue': [boolean]
}>()

const loading = ref(false)
const records = ref<CrmWritebackRecordItem[]>([])

const title = computed(() => 'CRM 写回历史')

watch(
  () => props.modelValue,
  async (visible) => {
    if (!visible || !props.objectType || !props.objectId) return
    loading.value = true
    try {
      const data = await fetchCrmWritebackRecords({
        object_type: props.objectType,
        object_id: props.objectId,
      })
      records.value = data.items
    } catch (error) {
      ElMessage.error(error instanceof Error ? error.message : '加载 CRM 写回历史失败')
    } finally {
      loading.value = false
    }
  },
)

function close() {
  emit('update:modelValue', false)
}

function statusLabel(value: string) {
  const map: Record<string, string> = {
    pending: '处理中',
    success: '成功',
    failed: '失败',
  }
  return map[value] || value
}

function targetTableLabel(value: string) {
  const map: Record<string, string> = {
    followup: '跟进记录',
    attachment: '资料归档',
  }
  return map[value] || value
}
</script>

<template>
  <el-drawer :model-value="modelValue" size="640px" :with-header="false" @close="close">
    <div class="drawer-shell">
      <header class="drawer-header">
        <div>
          <p class="section-title">CRM History</p>
          <h2>{{ title }}</h2>
          <p>这里保留当前对象每次写回飞书 CRM 的请求和结果留痕。</p>
        </div>
        <el-button circle plain @click="close">×</el-button>
      </header>

      <div v-if="loading" class="empty-inline">正在加载写回记录...</div>
      <div v-else-if="!records.length" class="empty-inline">当前还没有 CRM 写回历史。</div>
      <section v-else class="history-list">
        <article v-for="item in records" :key="item.id" class="history-item">
          <div class="history-item__head">
            <strong>{{ targetTableLabel(item.target_table) }}</strong>
            <el-tag :type="item.status === 'success' ? 'success' : item.status === 'failed' ? 'danger' : 'info'" effect="plain">
              {{ statusLabel(item.status) }}
            </el-tag>
          </div>
          <div class="history-item__meta">
            <span>{{ formatDateTime(item.created_at) }}</span>
            <span v-if="item.target_record_id">目标记录：{{ item.target_record_id }}</span>
            <span v-else>目标记录：待返回</span>
          </div>
          <details class="history-item__details">
            <summary>查看请求与返回详情</summary>
            <pre class="json-card">{{ JSON.stringify(item.response_payload || item.request_payload || {}, null, 2) }}</pre>
          </details>
          <p v-if="item.error_message" class="history-item__error">{{ item.error_message }}</p>
        </article>
      </section>
    </div>
  </el-drawer>
</template>

<style scoped>
.history-list {
  display: grid;
  gap: 14px;
}

.history-item {
  display: grid;
  gap: 10px;
  padding: 16px;
  border-radius: 18px;
  background: rgba(255,255,255,0.78);
  border: 1px solid rgba(15,93,140,0.1);
}

.history-item__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.history-item__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 14px;
  color: var(--muted);
  font-size: 13px;
}

.history-item__details {
  border-top: 1px dashed rgba(15, 93, 140, 0.14);
  padding-top: 10px;
}

.history-item__details summary {
  cursor: pointer;
  color: var(--muted);
  user-select: none;
}

.history-item__details summary:hover {
  color: var(--brand);
}

.history-item__error {
  color: #c0392b;
  margin: 0;
}

.json-card {
  margin: 10px 0 0;
  max-height: 240px;
  overflow: auto;
  padding: 12px;
  border-radius: 14px;
  background: #0d1b2a;
  color: #dbeafe;
  font-size: 12px;
  line-height: 1.55;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}
</style>
