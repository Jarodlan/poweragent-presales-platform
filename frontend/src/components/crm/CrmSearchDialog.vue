<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'

import { fetchCrmCustomers, fetchCrmOpportunities } from '@/api/crm'
import type { CrmRecordItem } from '@/types/crm'

const props = defineProps<{
  modelValue: boolean
}>()

const emit = defineEmits<{
  'update:modelValue': [boolean]
  confirm: [{
    crm_customer_record_id: string
    crm_opportunity_record_id: string
    customer?: CrmRecordItem | null
    opportunity?: CrmRecordItem | null
  }]
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

const selectedCustomer = computed(() =>
  customers.value.find((item) => item.record_id === selectedCustomerId.value) || null,
)

const selectedOpportunity = computed(() =>
  opportunities.value.find((item) => item.record_id === selectedOpportunityId.value) || null,
)

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
  if (opportunities.value.length === 1) {
    selectedOpportunityId.value = opportunities.value[0].record_id
  }
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
    customer: selectedCustomer.value,
    opportunity: selectedOpportunity.value,
  })
  close()
}
</script>

<template>
  <el-dialog :model-value="modelValue" title="绑定飞书 CRM" width="960px" destroy-on-close @close="close">
    <div class="crm-search-dialog">
      <div class="crm-search-dialog__filters">
        <el-input v-model="keyword" placeholder="搜索客户或商机关键词" clearable @keyup.enter="searchCustomers" />
        <el-input v-model="searchForm.owner_name" placeholder="负责人姓名（可选）" clearable @keyup.enter="searchCustomers" />
        <el-button type="primary" :loading="loading" @click="searchCustomers">查询 CRM</el-button>
      </div>

      <div class="crm-search-dialog__steps">
        <article class="crm-search-dialog__step-card">
          <span class="crm-search-dialog__step-index">1</span>
          <div>
            <strong>先绑定客户</strong>
            <p>先把当前对象挂到正确的飞书 CRM 客户上，这样后续的商机关联、跟进写回和售前闭环才会稳定。</p>
          </div>
        </article>
        <article class="crm-search-dialog__step-card crm-search-dialog__step-card--secondary">
          <span class="crm-search-dialog__step-index">2</span>
          <div>
            <strong>再绑定该客户对应商机</strong>
            <p>客户选定后，右侧会自动加载该客户下的商机。商机可选填，但推荐在项目推进后尽快补齐。</p>
          </div>
        </article>
      </div>

      <div class="crm-search-dialog__grid">
        <section class="panel-card crm-search-dialog__panel">
          <div class="crm-search-dialog__panel-head">
            <h3>客户（第一步）</h3>
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
            <h3>商机（第二步，可选）</h3>
            <span>{{ opportunities.length }} 条</span>
          </div>

          <div v-if="selectedCustomer" class="crm-search-dialog__selected-summary">
            <span class="crm-search-dialog__selected-label">当前客户</span>
            <strong>{{ selectedCustomer.name || '未命名客户' }}</strong>
            <small>
              {{ [selectedCustomer.industry, selectedCustomer.region, selectedCustomer.owner_name].filter(Boolean).join(' · ') || '暂无补充信息' }}
            </small>
          </div>
          <div v-else class="crm-search-dialog__empty crm-search-dialog__empty--guide">
            请先在左侧选择一个 CRM 客户，再从这里绑定该客户对应的商机。
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
            当前客户下暂无可选商机，可先只绑定客户。
          </div>

          <div v-if="selectedOpportunity" class="crm-search-dialog__selected-opportunity">
            <span class="crm-search-dialog__selected-label">已选商机</span>
            <strong>{{ selectedOpportunity.name || '未命名商机' }}</strong>
            <small>
              {{ [selectedOpportunity.stage, selectedOpportunity.amount, selectedOpportunity.owner_name].filter(Boolean).join(' · ') || '暂无补充信息' }}
            </small>
          </div>
        </section>
      </div>
    </div>

    <template #footer>
      <el-button @click="close">取消</el-button>
      <el-button type="primary" @click="confirmSelection">
        {{ selectedOpportunityId ? '确认绑定客户和商机' : '确认绑定客户' }}
      </el-button>
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

.crm-search-dialog__steps {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.crm-search-dialog__step-card {
  display: flex;
  gap: 12px;
  padding: 14px 16px;
  border-radius: 18px;
  background: linear-gradient(135deg, rgba(235, 247, 255, 0.95), rgba(247, 252, 255, 0.92));
  border: 1px solid rgba(0, 126, 255, 0.16);
}

.crm-search-dialog__step-card--secondary {
  background: linear-gradient(135deg, rgba(249, 250, 255, 0.96), rgba(244, 247, 252, 0.94));
  border-color: rgba(15, 93, 140, 0.12);
}

.crm-search-dialog__step-card p {
  margin: 4px 0 0;
  color: var(--muted);
  line-height: 1.6;
}

.crm-search-dialog__step-index {
  width: 26px;
  height: 26px;
  border-radius: 999px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: #007eff;
  color: #fff;
  font-size: 13px;
  font-weight: 700;
  flex: none;
}

.crm-search-dialog__grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.crm-search-dialog__panel {
  min-height: 430px;
  display: grid;
  grid-template-rows: auto auto minmax(0, 1fr) auto;
  gap: 12px;
  padding: 16px;
}

.crm-search-dialog__panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.crm-search-dialog__selected-summary,
.crm-search-dialog__selected-opportunity {
  display: grid;
  gap: 4px;
  padding: 12px 14px;
  border-radius: 16px;
  background: rgba(246, 250, 255, 0.9);
  border: 1px solid rgba(15, 93, 140, 0.1);
}

.crm-search-dialog__selected-label {
  color: var(--muted);
  font-size: 12px;
}

.crm-search-dialog__list {
  display: grid;
  gap: 10px;
  align-content: start;
  max-height: 320px;
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
.crm-search-dialog__empty,
.crm-search-dialog__selected-summary small,
.crm-search-dialog__selected-opportunity small {
  color: var(--muted);
  line-height: 1.6;
  overflow-wrap: anywhere;
}

.crm-search-dialog__empty {
  padding: 10px 4px 0;
}

.crm-search-dialog__empty--guide {
  margin-bottom: auto;
}

@media (max-width: 900px) {
  .crm-search-dialog__filters,
  .crm-search-dialog__steps,
  .crm-search-dialog__grid {
    grid-template-columns: 1fr;
  }
}
</style>
