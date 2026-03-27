<script setup lang="ts">
import { computed, ref } from 'vue'

import CrmBindingCard from '@/components/crm/CrmBindingCard.vue'
import type { CrmBoundState } from '@/types/crm'
import feishuLogo from '../../../../assets/icon/feishu.svg'

const props = defineProps<{
  state: CrmBoundState | null | undefined
  canBind?: boolean
  canWriteback?: boolean
  title?: string
  description?: string
  writebackLabel?: string
  dialogTitle?: string
}>()

const emit = defineEmits<{
  bind: []
  writeback: []
  history: []
}>()

const dialogVisible = ref(false)

const bindingStatus = computed(() => {
  if (props.state?.crm_customer_record_id || props.state?.crm_opportunity_record_id) {
    return '已关联'
  }
  return '未关联'
})

const bindingTagType = computed(() => {
  return bindingStatus.value === '已关联' ? 'success' : 'info'
})

function openDialog() {
  dialogVisible.value = true
}

function handleBind() {
  dialogVisible.value = false
  emit('bind')
}

function handleWriteback() {
  dialogVisible.value = false
  emit('writeback')
}

function handleHistory() {
  dialogVisible.value = false
  emit('history')
}
</script>

<template>
  <div class="crm-action-button">
    <el-button class="crm-action-button__trigger" type="primary" @click="openDialog">
      <span class="crm-action-button__logo" aria-hidden="true">
        <img :src="feishuLogo" alt="" />
      </span>
      <span class="crm-action-button__label">飞书 CRM 关联</span>
      <el-tag size="small" effect="dark" :type="bindingTagType">{{ bindingStatus }}</el-tag>
    </el-button>

    <el-dialog
      v-model="dialogVisible"
      :title="dialogTitle || '飞书 CRM 关联'"
      width="720px"
      destroy-on-close
      class="crm-action-button__dialog"
    >
      <CrmBindingCard
        :title="title"
        :description="description"
        :state="state"
        :can-bind="canBind"
        :can-writeback="canWriteback"
        :writeback-label="writebackLabel"
        @bind="handleBind"
        @writeback="handleWriteback"
        @history="handleHistory"
      />
    </el-dialog>
  </div>
</template>

<style scoped>
.crm-action-button__trigger {
  height: 44px;
  padding: 0 16px 0 12px;
  border: none;
  border-radius: 16px;
  background: linear-gradient(135deg, #00b7ff 0%, #0068ff 100%);
  box-shadow: 0 12px 24px rgba(0, 104, 255, 0.22);
  display: inline-flex;
  align-items: center;
  gap: 10px;
}

.crm-action-button__trigger :deep(.el-tag) {
  margin-left: 4px;
  border: none;
}

.crm-action-button__logo {
  width: 22px;
  height: 22px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.14);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  backdrop-filter: blur(8px);
  overflow: hidden;
}

.crm-action-button__logo img {
  width: 18px;
  height: 18px;
  display: block;
}

.crm-action-button__label {
  font-weight: 600;
}

.crm-action-button__dialog :deep(.el-dialog__body) {
  padding-top: 10px;
}
</style>
