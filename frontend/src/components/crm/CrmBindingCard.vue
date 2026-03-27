<script setup lang="ts">
import { computed } from 'vue'
import { Connection, DocumentChecked, Link, Notebook, Opportunity } from '@element-plus/icons-vue'

import type { CrmBoundState } from '@/types/crm'
import { formatDateTime } from '@/utils/time'

const props = defineProps<{
  title?: string
  description?: string
  state: CrmBoundState | null | undefined
  canBind?: boolean
  canWriteback?: boolean
  writebackLabel?: string
}>()

const emit = defineEmits<{
  bind: []
  writeback: []
  history: []
}>()

const customerName = computed(() => String(props.state?.crm_customer_snapshot?.name || '未绑定客户'))
const opportunityName = computed(() => String(props.state?.crm_opportunity_snapshot?.name || '未绑定商机'))
const providerLabel = computed(() => (props.state?.crm_provider ? '飞书 CRM' : '未绑定'))
const bindingStatusLabel = computed(() => {
  if (props.state?.crm_customer_record_id || props.state?.crm_opportunity_record_id) return '已关联 CRM'
  return '待关联'
})
const bindingTagType = computed(() => {
  return bindingStatusLabel.value === '已关联 CRM' ? 'success' : 'info'
})
const writebackStatusLabel = computed(() => {
  const map: Record<string, string> = {
    success: '最近写回成功',
    failed: '最近写回失败',
  }
  return map[String(props.state?.crm_last_writeback_status || '')] || '尚未写回'
})
const writebackTagType = computed(() => {
  const status = String(props.state?.crm_last_writeback_status || '')
  if (status === 'success') return 'success'
  if (status === 'failed') return 'danger'
  return 'info'
})
const compactCustomerId = computed(() => {
  const value = String(props.state?.crm_customer_record_id || '')
  return value ? `${value.slice(0, 6)}...${value.slice(-4)}` : '未绑定记录'
})
const compactOpportunityId = computed(() => {
  const value = String(props.state?.crm_opportunity_record_id || '')
  return value ? `${value.slice(0, 6)}...${value.slice(-4)}` : '未绑定记录'
})
const compactBaseId = computed(() => {
  const value = String(props.state?.crm_base_id || '')
  return value ? `${value.slice(0, 8)}...${value.slice(-6)}` : '未绑定 Base'
})
</script>

<template>
  <section class="crm-binding-card panel-card">
    <div class="crm-binding-card__summary">
      <div class="crm-binding-card__summary-main">
        <p class="section-title">Feishu CRM</p>
        <div class="crm-binding-card__summary-title">
          <h3>{{ title || '飞书 CRM 绑定' }}</h3>
          <el-tag size="small" effect="dark" :type="bindingTagType">{{ bindingStatusLabel }}</el-tag>
        </div>
        <p class="crm-binding-card__summary-text">
          {{ description || '先关联客户与商机，再决定是否把需求分析、方案结果或售前任务写回飞书 CRM。' }}
        </p>
      </div>
      <div class="crm-binding-card__summary-meta">
        <div class="crm-binding-card__meta-pill">
          <span>来源</span>
          <strong>{{ providerLabel }}</strong>
        </div>
        <div class="crm-binding-card__meta-pill">
          <span>最近写回</span>
          <el-tag size="small" :type="writebackTagType" effect="plain">{{ writebackStatusLabel }}</el-tag>
        </div>
      </div>
    </div>

    <div class="crm-binding-card__grid">
      <article class="crm-binding-card__item">
        <div class="crm-binding-card__item-head">
          <span>客户</span>
          <el-icon><Connection /></el-icon>
        </div>
        <strong class="crm-binding-card__value" :title="customerName">{{ customerName }}</strong>
        <small :title="state?.crm_customer_record_id || ''">{{ compactCustomerId }}</small>
      </article>
      <article class="crm-binding-card__item">
        <div class="crm-binding-card__item-head">
          <span>商机</span>
          <el-icon><Opportunity /></el-icon>
        </div>
        <strong class="crm-binding-card__value" :title="opportunityName">{{ opportunityName }}</strong>
        <small :title="state?.crm_opportunity_record_id || ''">{{ compactOpportunityId }}</small>
      </article>
      <article class="crm-binding-card__item">
        <div class="crm-binding-card__item-head">
          <span>数据源</span>
          <el-icon><Link /></el-icon>
        </div>
        <strong class="crm-binding-card__value">{{ providerLabel }}</strong>
        <small :title="state?.crm_base_id || ''">{{ compactBaseId }}</small>
      </article>
      <article class="crm-binding-card__item">
        <div class="crm-binding-card__item-head">
          <span>最近写回</span>
          <el-icon><DocumentChecked /></el-icon>
        </div>
        <strong class="crm-binding-card__value">
          <el-tag size="small" :type="writebackTagType" effect="plain">{{ writebackStatusLabel }}</el-tag>
        </strong>
        <small>{{ state?.crm_last_writeback_at ? formatDateTime(state.crm_last_writeback_at) : '暂无记录' }}</small>
      </article>
    </div>

    <div class="crm-binding-card__toolbar">
      <div class="crm-binding-card__footer">
        <el-icon><Connection /></el-icon>
        <span>绑定时间：{{ state?.crm_bound_at ? formatDateTime(state.crm_bound_at) : '未绑定' }}</span>
      </div>
      <div class="crm-binding-card__actions">
        <el-button v-if="canBind" plain @click="emit('bind')">
          <el-icon><Link /></el-icon>
          绑定 CRM
        </el-button>
        <el-button v-if="canWriteback" type="primary" @click="emit('writeback')">
          <el-icon><DocumentChecked /></el-icon>
          {{ writebackLabel || '写回 CRM' }}
        </el-button>
        <el-button plain @click="emit('history')">
          <el-icon><Notebook /></el-icon>
          写回历史
        </el-button>
      </div>
    </div>
  </section>
</template>

<style scoped>
.crm-binding-card {
  display: grid;
  gap: 18px;
}

.crm-binding-card__summary {
  display: flex;
  justify-content: space-between;
  gap: 18px;
  padding: 18px 20px;
  border-radius: 22px;
  background:
    radial-gradient(circle at top left, rgba(0, 183, 255, 0.18), transparent 40%),
    linear-gradient(135deg, rgba(255, 255, 255, 0.94), rgba(244, 250, 255, 0.88));
  border: 1px solid rgba(15, 93, 140, 0.12);
}

.crm-binding-card__summary-main {
  min-width: 0;
  display: grid;
  gap: 8px;
}

.crm-binding-card__summary-title {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.crm-binding-card__summary-title h3 {
  margin: 0;
}

.crm-binding-card__summary-text {
  margin: 0;
  color: var(--muted);
  line-height: 1.7;
}

.crm-binding-card__summary-meta {
  display: grid;
  gap: 10px;
  align-content: start;
  min-width: 180px;
}

.crm-binding-card__meta-pill {
  padding: 12px 14px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.84);
  border: 1px solid rgba(15, 93, 140, 0.1);
  display: grid;
  gap: 6px;
}

.crm-binding-card__meta-pill span {
  color: var(--muted);
  font-size: 12px;
}

.crm-binding-card__item-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
  color: var(--muted);
}

.crm-binding-card__grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.crm-binding-card__item {
  padding: 16px;
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.78);
  border: 1px solid rgba(15, 93, 140, 0.1);
  display: grid;
  gap: 8px;
  min-width: 0;
}

.crm-binding-card__item span,
.crm-binding-card__item small {
  color: var(--muted);
}

.crm-binding-card__value {
  min-width: 0;
  font-size: 16px;
  line-height: 1.45;
  overflow-wrap: anywhere;
}

.crm-binding-card__item small {
  overflow-wrap: anywhere;
  line-height: 1.5;
}

.crm-binding-card__toolbar {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: center;
  flex-wrap: wrap;
}

.crm-binding-card__footer {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: var(--muted);
  font-size: 13px;
}

.crm-binding-card__actions {
  display: flex;
  gap: 10px;
  align-items: center;
  flex-wrap: wrap;
}

@media (max-width: 820px) {
  .crm-binding-card__summary,
  .crm-binding-card__toolbar {
    flex-direction: column;
    align-items: stretch;
  }

  .crm-binding-card__grid {
    grid-template-columns: 1fr;
  }

  .crm-binding-card__summary-meta {
    min-width: 0;
  }
}
</style>
