<script setup lang="ts">
import { reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'

import { fetchCrmCustomers, fetchCrmOpportunities } from '@/api/crm'
import type { CrmRecordItem } from '@/types/crm'

const props = defineProps<{
  modelValue: boolean
}>()

const emit = defineEmits<{
  'update:modelValue': [boolean]
  confirm: [{ crm_customer_record_id: string; crm_opportunity_record_id: string }]
}>()

const keyword = ref('')
const loading = ref(false)
const customers = ref<CrmRecordItem[]>([])
const opportunities = ref<CrmRecordItem[]>([])
const selectedCustomerId = ref('')
const selectedOpportunityId = ref('')

const searchForm = reactive({
  owner_name: '',
})

async function searchCustomers() {
  loading.value = true
  try {
    const data = await fetchCrmCustomers({
      keyword: keyword.value.trim() || undefined,
      owner_name: searchForm.owner_name.trim() || undefined,
    })
    customers.value = data.items
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '查询 CRM 客户失败')
  } finally {
    loading.value = false
  }
}

async function searchOpportunities(customerRecordId = selectedCustomerId.value) {
  if (!customerRecordId) {
    opportunities.value = []
    selectedOpportunityId.value = ''
    return
  }
  loading.value = true
  try {
    const data = await fetchCrmOpportunities({
      keyword: keyword.value.trim() || undefined,
      owner_name: searchForm.owner_name.trim() || undefined,
      customer_record_id: customerRecordId,
    })
    opportunities.value = data.items
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '查询 CRM 商机失败')
  } finally {
    loading.value = false
  }
}

watch(
  () => props.modelValue,
  async (visible) => {
    if (!visible) return
    keyword.value = ''
    searchForm.owner_name = ''
    customers.value = []
    opportunities.value = []
    selectedCustomerId.value = ''
    selectedOpportunityId.value = ''
    await searchCustomers()
  },
)

watch(selectedCustomerId, async (value) => {
  selectedOpportunityId.value = ''
  await searchOpportunities(value)
})

function close() {
  emit('update:modelValue', false)
}

function confirmSelection() {
  if (!selectedCustomerId.value) {
    ElMessage.warning('请先选择一个 CRM 客户')
    return
  }
  emit('confirm', {
    crm_customer_record_id: selectedCustomerId.value,
    crm_opportunity_record_id: selectedOpportunityId.value,
  })
  close()
}
</script>

<template>
  <el-dialog :model-value="modelValue" title="绑定飞书 CRM" width="880px" destroy-on-close @close="close">
    <div class="crm-search-dialog">
      <div class="crm-search-dialog__filters">
        <el-input v-model="keyword" placeholder="搜索客户或商机关键词" clearable @keyup.enter="searchCustomers" />
        <el-input v-model="searchForm.owner_name" placeholder="负责人姓名（可选）" clearable @keyup.enter="searchCustomers" />
        <el-button type="primary" :loading="loading" @click="searchCustomers">查询 CRM</el-button>
      </div>

      <div class="crm-search-dialog__grid">
        <section class="panel-card crm-search-dialog__panel">
          <div class="crm-search-dialog__panel-head">
            <h3>客户</h3>
            <span>{{ customers.length }} 条</span>
          </div>
          <el-radio-group v-model="selectedCustomerId" class="crm-search-dialog__list">
            <label
              v-for="item in customers"
              :key="item.record_id"
              class="crm-search-dialog__item"
              :class="{ 'is-selected': selectedCustomerId === item.record_id }"
            >
              <el-radio :value="item.record_id">
                <span>{{ item.name || '未命名客户' }}</span>
              </el-radio>
              <small>{{ [item.industry, item.region, item.owner_name].filter(Boolean).join(' · ') || '暂无补充信息' }}</small>
            </label>
          </el-radio-group>
        </section>

        <section class="panel-card crm-search-dialog__panel">
          <div class="crm-search-dialog__panel-head">
            <h3>商机</h3>
            <span>{{ opportunities.length }} 条</span>
          </div>
          <el-radio-group v-model="selectedOpportunityId" class="crm-search-dialog__list">
            <label
              v-for="item in opportunities"
              :key="item.record_id"
              class="crm-search-dialog__item"
              :class="{ 'is-selected': selectedOpportunityId === item.record_id }"
            >
              <el-radio :value="item.record_id">
                <span>{{ item.name || '未命名商机' }}</span>
              </el-radio>
              <small>{{ [item.stage, item.amount, item.owner_name].filter(Boolean).join(' · ') || '暂无补充信息' }}</small>
            </label>
          </el-radio-group>
          <div v-if="selectedCustomerId && !opportunities.length" class="crm-search-dialog__empty">
            当前客户下暂无可选商机，可只绑定客户。
          </div>
        </section>
      </div>
    </div>

    <template #footer>
      <el-button @click="close">取消</el-button>
      <el-button type="primary" @click="confirmSelection">确认绑定</el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.crm-search-dialog {
  display: grid;
  gap: 18px;
}

.crm-search-dialog__filters {
  display: grid;
  grid-template-columns: 1.4fr 1fr auto;
  gap: 12px;
  padding: 14px;
  border-radius: 18px;
  background: linear-gradient(135deg, rgba(248, 252, 255, 0.96), rgba(238, 247, 255, 0.9));
  border: 1px solid rgba(15, 93, 140, 0.08);
}

.crm-search-dialog__grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.crm-search-dialog__panel {
  min-height: 400px;
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  gap: 12px;
  padding: 16px;
}

.crm-search-dialog__panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.crm-search-dialog__list {
  display: grid;
  gap: 10px;
  align-content: start;
  max-height: 360px;
  overflow-y: auto;
  padding-right: 4px;
}

.crm-search-dialog__item {
  display: grid;
  gap: 6px;
  padding: 12px 14px;
  border-radius: 16px;
  background: rgba(255,255,255,0.82);
  border: 1px solid rgba(15,93,140,0.1);
  transition: border-color 0.18s ease, box-shadow 0.18s ease, transform 0.18s ease;
  min-width: 0;
}

.crm-search-dialog__item.is-selected {
  border-color: rgba(0, 104, 255, 0.4);
  box-shadow: 0 10px 22px rgba(0, 104, 255, 0.12);
  transform: translateY(-1px);
}

.crm-search-dialog__item :deep(.el-radio) {
  align-items: flex-start;
  min-width: 0;
}

.crm-search-dialog__item :deep(.el-radio__label) {
  white-space: normal;
  overflow-wrap: anywhere;
}

.crm-search-dialog__item small,
.crm-search-dialog__empty {
  color: var(--muted);
  line-height: 1.6;
  overflow-wrap: anywhere;
}

.crm-search-dialog__empty {
  padding: 10px 4px 0;
}

@media (max-width: 900px) {
  .crm-search-dialog__filters,
  .crm-search-dialog__grid {
    grid-template-columns: 1fr;
  }
}
</style>
