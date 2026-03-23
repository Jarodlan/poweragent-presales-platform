<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { ArrowLeft, Download, Refresh, Right } from '@element-plus/icons-vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

import EmptyState from '@/components/common/EmptyState.vue'
import { DEFAULT_PARAMS, SCENARIO_PRESET_MAP, type ComposerParams } from '@/config/solutionComposer'
import { useCustomerDemandStore } from '@/stores/customerDemand'
import { useMetaStore } from '@/stores/meta'
import type { OptionItem } from '@/types/meta'
import type {
  CustomerDemandKnowledgeSource,
  CustomerDemandReportItem,
  CustomerDemandSessionItem,
} from '@/types/customerDemand'
import { saveSolutionHandoffDraft } from '@/utils/solutionHandoff'
import { renderMarkdown } from '@/utils/markdown'
import { formatDateTime } from '@/utils/time'

const route = useRoute()
const router = useRouter()
const demandStore = useCustomerDemandStore()
const metaStore = useMetaStore()

const sessionId = computed(() => String(route.params.sessionId || ''))
const report = computed(() => demandStore.currentReport)
const handoffDialogVisible = ref(false)
const handoffQuery = ref('')
const handoffParams = ref<ComposerParams>({ ...DEFAULT_PARAMS })

const scenarioFlags = computed(() => {
  const value = handoffParams.value.scenario
  return {
    isOther: value === 'other_solution',
    isFaultDiagnosis: value === 'fault_diagnosis_solution',
    isStorageAggregation: value === 'storage_aggregation_solution',
    isDistributionPlanning: value === 'distribution_planning_solution',
    isPowerForecast: value === 'power_forecast_solution',
    isVppCoordination: value === 'vpp_coordination_solution',
  }
})

const handoffSummary = computed(() => {
  const options = metaStore.options
  if (!options) return []
  const resolveLabel = (items: OptionItem[], value: string) => items.find((item) => item.value === value)?.label || value
  const resolveMany = (items: OptionItem[], values: string[]) => values.map((value) => resolveLabel(items, value)).join(' / ')
  return [
    {
      label: '方案场景',
      value: resolveLabel(options.scenario_options, handoffParams.value.scenario),
    },
    handoffParams.value.grid_environment !== 'not_involved'
      ? {
          label: '电网环境',
          value: resolveLabel(options.grid_environment_options, handoffParams.value.grid_environment),
        }
      : null,
    handoffParams.value.resource_type !== 'not_involved'
      ? {
          label: '资源类型',
          value: resolveLabel(options.resource_type_options, handoffParams.value.resource_type),
        }
      : null,
    handoffParams.value.data_basis.length
      ? {
          label: '数据基础',
          value: resolveMany(options.data_basis_options, handoffParams.value.data_basis),
        }
      : null,
    handoffParams.value.target_capability.length
      ? {
          label: '目标能力',
          value: resolveMany(options.target_capability_options, handoffParams.value.target_capability),
        }
      : null,
  ].filter(Boolean) as Array<{ label: string; value: string }>
})

const knowledgeSources = computed<CustomerDemandKnowledgeSource[]>(() => {
  const raw = report.value?.used_knowledge_sources || []
  if (!Array.isArray(raw)) return []
  return raw
    .map((item) => {
      if (!item || typeof item !== 'object') return null
      const source = item as Record<string, unknown>
      return {
        source_type: String(source.source_type || ''),
        source_label: String(source.source_label || '知识来源'),
        title: String(source.title || '未命名资料'),
        snippet: String(source.snippet || ''),
        score: Number(source.score || 0),
        metadata: (source.metadata as Record<string, unknown>) || {},
      }
    })
    .filter(Boolean) as CustomerDemandKnowledgeSource[]
})

function knowledgeScoreLabel(value: number) {
  if (!Number.isFinite(value) || value <= 0) return ''
  return value >= 1 ? value.toFixed(2) : value.toFixed(3)
}

function knowledgeMetaSummary(item: CustomerDemandKnowledgeSource) {
  const metadata = item.metadata || {}
  const positions = metadata.positions
  if (Array.isArray(positions) && positions.length) {
    const first = positions[0]
    if (Array.isArray(first) && typeof first[0] === 'number') {
      return `命中页码：第 ${first[0]} 页`
    }
  }
  const datasetId = metadata.dataset_id
  if (datasetId) {
    return `数据集：${String(datasetId).slice(0, 8)}...`
  }
  return ''
}

async function loadReportContext() {
  if (!sessionId.value) return
  await metaStore.loadOptions()
  await demandStore.selectSession(sessionId.value)
}

function compactLine(text: string, limit = 28) {
  const normalized = text.replace(/\s+/g, ' ').trim()
  if (normalized.length <= limit) return normalized
  return `${normalized.slice(0, limit).trim()}...`
}

function extractStringArray(source: Record<string, unknown> | null | undefined, key: string) {
  const value = source?.[key]
  if (!Array.isArray(value)) return []
  return value.map((item) => String(item || '').trim()).filter(Boolean)
}

function detectScenario(text: string) {
  const normalized = text.toLowerCase()
  const scenarios = [
    { id: 'power_forecast_solution', keywords: ['功率预测', '出力预测', '偏差考核', '日前预测', '日内预测', '风电', '光伏预测'] },
    { id: 'distribution_planning_solution', keywords: ['配网规划', '网架', '台区', '重过载', 'n-1', '投资优化'] },
    { id: 'fault_diagnosis_solution', keywords: ['故障诊断', '故障定位', '接地', '自愈', '停电', '保护动作'] },
    { id: 'vpp_coordination_solution', keywords: ['虚拟电厂', '源网荷储', '需求响应', '聚合调度', '可调负荷'] },
    { id: 'storage_aggregation_solution', keywords: ['储能', '弃电', '消纳', '充放电', '峰谷', '套利', 'bms', 'pcs'] },
  ]
  let best = { id: 'other_solution', score: 0 }
  for (const scenario of scenarios) {
    const score = scenario.keywords.reduce((sum, keyword) => sum + (normalized.includes(keyword) ? 1 : 0), 0)
    if (score > best.score) {
      best = { id: scenario.id, score }
    }
  }
  return best.score > 0 ? best.id : 'other_solution'
}

function pushUnique(target: string[], value: string) {
  if (value && !target.includes(value)) {
    target.push(value)
  }
}

function inferParamsFromReport(currentReport: CustomerDemandReportItem | null, currentSession: CustomerDemandSessionItem | null): ComposerParams {
  const payload = (currentReport?.report_payload || {}) as Record<string, unknown>
  const sourceText = [
    currentReport?.report_title,
    currentSession?.session_title,
    currentSession?.topic,
    currentSession?.industry,
    currentSession?.region,
    currentReport?.report_markdown,
    ...extractStringArray(payload, 'current_problem'),
    ...extractStringArray(payload, 'explicit_requirements'),
    ...extractStringArray(payload, 'implicit_requirements'),
    ...extractStringArray(payload, 'constraints_and_risks'),
  ]
    .filter(Boolean)
    .join(' ')

  const scenario = detectScenario(sourceText)
  const preset = SCENARIO_PRESET_MAP[scenario] ?? {}
  const next: ComposerParams = {
    ...DEFAULT_PARAMS,
    ...(preset as Partial<ComposerParams>),
    scenario,
    data_basis: [...((preset.data_basis as string[] | undefined) ?? DEFAULT_PARAMS.data_basis)],
    target_capability: [...((preset.target_capability as string[] | undefined) ?? DEFAULT_PARAMS.target_capability)],
    market_policy_focus: [...((preset.market_policy_focus as string[] | undefined) ?? DEFAULT_PARAMS.market_policy_focus)],
    planning_objective: [...((preset.planning_objective as string[] | undefined) ?? DEFAULT_PARAMS.planning_objective)],
    forecast_target: [...((preset.forecast_target as string[] | undefined) ?? DEFAULT_PARAMS.forecast_target)],
  }

  if (/(园区|工业园|厂区|办公园区|综合能源站|微网)/.test(sourceText)) {
    next.grid_environment = 'microgrid'
  } else if (/(综合能源)/.test(sourceText)) {
    next.grid_environment = 'integrated_energy'
  } else if (/(配电|配网|台区)/.test(sourceText)) {
    next.grid_environment = 'distribution_network'
  } else if (/(输电|变电主网)/.test(sourceText)) {
    next.grid_environment = 'transmission_network'
  }

  if (/(风电.*光伏.*储能|光伏.*风电.*储能)/.test(sourceText)) {
    next.resource_type = 'wind_pv_storage'
  } else if (/(光伏.*储能|储能.*光伏)/.test(sourceText)) {
    next.resource_type = 'pv_storage'
  } else if (/(储能)/.test(sourceText)) {
    next.resource_type = 'distributed_storage'
  }

  if (/(气象|天气|风速|辐照)/.test(sourceText)) {
    pushUnique(next.data_basis, 'weather_data')
  }
  if (/(负荷|用电量|尖峰负荷)/.test(sourceText)) {
    pushUnique(next.data_basis, 'load_curve')
  }
  if (/(光伏|风电|新能源出力|消纳)/.test(sourceText)) {
    pushUnique(next.data_basis, 'renewable_curve')
  }
  if (/(电价|现货|峰谷|套利)/.test(sourceText)) {
    pushUnique(next.data_basis, 'market_price_data')
    pushUnique(next.market_policy_focus, 'spot_market')
  }
  if (/(储能|pcs|bms|充放电)/.test(sourceText)) {
    pushUnique(next.data_basis, 'bms_pcs_data')
  }
  if (/(需求响应)/.test(sourceText)) {
    pushUnique(next.market_policy_focus, 'demand_response')
  }

  return next
}

function buildHandoffQuery(currentReport: CustomerDemandReportItem | null, currentSession: CustomerDemandSessionItem | null) {
  const payload = (currentReport?.report_payload || {}) as Record<string, unknown>
  const currentProblems = extractStringArray(payload, 'current_problem')
  const explicitRequirements = extractStringArray(payload, 'explicit_requirements')
  const implicitRequirements = extractStringArray(payload, 'implicit_requirements')
  const constraintsAndRisks = extractStringArray(payload, 'constraints_and_risks')
  const pendingQuestions = extractStringArray(payload, 'pending_questions')

  return [
    '请基于以下客户需求分析结果，生成一份结构完整、偏实施型的电力行业解决方案。',
    '',
    `客户名称：${currentSession?.customer_name || '未填写'}`,
    `沟通主题：${currentSession?.topic || currentSession?.session_title || '未填写'}`,
    currentSession?.industry ? `行业：${currentSession.industry}` : '',
    currentSession?.region ? `区域：${currentSession.region}` : '',
    '',
    '当前问题：',
    ...(currentProblems.length ? currentProblems : ['暂无明确问题，请结合下方需求自行归纳。']).map((item) => `- ${compactLine(item, 120)}`),
    '',
    '已明确需求：',
    ...(explicitRequirements.length ? explicitRequirements : ['暂无，请从客户诉求中提炼。']).map((item) => `- ${compactLine(item, 120)}`),
    '',
    '隐性需求与潜在诉求：',
    ...(implicitRequirements.length ? implicitRequirements : ['暂无，请结合沟通背景适度推断。']).map((item) => `- ${compactLine(item, 120)}`),
    '',
    '约束条件与风险点：',
    ...(constraintsAndRisks.length ? constraintsAndRisks : ['暂无，请结合实施场景补充。']).map((item) => `- ${compactLine(item, 120)}`),
    '',
    '待确认问题：',
    ...(pendingQuestions.length ? pendingQuestions : ['暂无，请给出合理的待确认项。']).map((item) => `- ${compactLine(item, 120)}`),
    '',
    '要求：',
    '- 输出正式解决方案标题。',
    '- 结合上述需求自动匹配最合适的电力业务场景。',
    '- 重点体现实施路径、系统架构、能力模块、关键指标和落地建议。',
  ]
    .filter(Boolean)
    .join('\n')
}

function openHandoffDialog() {
  handoffParams.value = inferParamsFromReport(report.value, demandStore.currentSession)
  handoffQuery.value = buildHandoffQuery(report.value, demandStore.currentSession)
  handoffDialogVisible.value = true
}

function handleScenarioChange(value: string) {
  handoffParams.value = {
    ...handoffParams.value,
    scenario: value,
    ...(SCENARIO_PRESET_MAP[value] ?? {}),
  }
}

function updateArrayField(key: keyof ComposerParams, values: string[]) {
  handoffParams.value = {
    ...handoffParams.value,
    [key]: values,
  }
}

async function confirmHandoff() {
  if (!report.value || !sessionId.value || !handoffQuery.value.trim()) {
    ElMessage.warning('请先确认要导入的方案草稿内容。')
    return
  }
  saveSolutionHandoffDraft({
    source: 'customer-demand',
    sourceSessionId: sessionId.value,
    sourceReportId: report.value.id,
    query: handoffQuery.value.trim(),
    params: handoffParams.value,
    createdAt: new Date().toISOString(),
  })
  handoffDialogVisible.value = false
  ElMessage.success('已带入方案工作台，请继续确认并发送。')
  await router.push('/')
}

onMounted(loadReportContext)
watch(sessionId, async () => {
  await loadReportContext()
})
</script>

<template>
  <div class="customer-demand-report-shell">
    <header class="customer-demand-report-header panel-card">
      <div class="customer-demand-report-header__left">
        <el-button plain @click="router.push('/customer-demand')">
          <el-icon><ArrowLeft /></el-icon>
          返回会中工作台
        </el-button>
        <div>
          <p class="section-title">Demand Report</p>
          <h1>{{ report?.report_title || demandStore.currentSession?.session_title || '客户需求分析报告' }}</h1>
          <p>
            {{ demandStore.currentSession?.customer_name || '未选中客户' }}
            <span v-if="demandStore.currentSession?.region"> · {{ demandStore.currentSession?.region }}</span>
            <span v-if="report?.updated_at"> · 更新于 {{ formatDateTime(report.updated_at) }}</span>
          </p>
        </div>
      </div>
      <div class="customer-demand-report-header__actions">
        <el-button type="success" :disabled="!report" @click="openHandoffDialog">
          <el-icon><Right /></el-icon>
          转入方案生成
        </el-button>
        <el-button plain @click="loadReportContext">
          <el-icon><Refresh /></el-icon>
          刷新
        </el-button>
        <el-button type="primary" :loading="demandStore.exporting" @click="demandStore.exportCurrentReport()">
          <el-icon><Download /></el-icon>
          导出 Markdown
        </el-button>
      </div>
    </header>

    <div v-if="demandStore.loadingDetail" class="customer-demand-report-loading panel-card">
      正在加载报告内容...
    </div>

    <template v-else-if="report">
      <section class="customer-demand-report-grid">
        <article class="panel-card report-main">
          <div class="report-main__head">
            <h2>正式需求分析报告</h2>
            <p>适合会后阅读、导出和流转，不再挤在会中辅助工作台的小卡片里。</p>
          </div>
          <div class="markdown-view" v-html="renderMarkdown(report.report_markdown || '')"></div>
        </article>

        <aside class="report-side">
          <section class="panel-card report-side__card">
            <h3>需求挖掘方向建议</h3>
            <div class="markdown-view" v-html="renderMarkdown(report.digging_suggestions_markdown || '暂无建议')"></div>
          </section>

          <section class="panel-card report-side__card">
            <h3>推荐追问问题</h3>
            <div class="markdown-view" v-html="renderMarkdown(report.recommended_questions_markdown || '暂无推荐问题')"></div>
          </section>

          <section class="panel-card report-side__card">
            <h3>报告元信息</h3>
            <ul class="report-meta-list">
              <li>
                <strong>模型</strong>
                <span>{{ report.llm_model || '未记录' }}</span>
              </li>
              <li>
                <strong>版本</strong>
                <span>V{{ report.report_version }}</span>
              </li>
              <li>
                <strong>知识库开关</strong>
                <span>{{ report.knowledge_enabled ? '已开启' : '未开启' }}</span>
              </li>
              <li>
                <strong>创建时间</strong>
                <span>{{ formatDateTime(report.created_at) }}</span>
              </li>
            </ul>
          </section>

          <section class="panel-card report-side__card">
            <div class="report-side__head">
              <div>
                <h3>知识来源</h3>
                <p>这里展示本次需求分析实际参考到的知识资料，方便快速确认知识库是否真正生效。</p>
              </div>
              <el-tag effect="plain" type="info">{{ knowledgeSources.length }} 条</el-tag>
            </div>
            <div v-if="!report.knowledge_enabled" class="report-source-empty">
              当前报告生成时未开启知识库辅助。
            </div>
            <div v-else-if="!knowledgeSources.length" class="report-source-empty">
              本次未命中合适的知识资料，因此报告仅基于沟通内容分析。
            </div>
            <div v-else class="report-source-list">
              <article v-for="(item, index) in knowledgeSources" :key="`${item.source_type}-${item.title}-${index}`" class="report-source-item">
                <div class="report-source-item__head">
                  <el-tag size="small" effect="light" type="success">{{ item.source_label || '知识来源' }}</el-tag>
                  <span v-if="knowledgeScoreLabel(item.score)" class="report-source-item__score">相关度 {{ knowledgeScoreLabel(item.score) }}</span>
                </div>
                <strong class="report-source-item__title">{{ item.title }}</strong>
                <p class="report-source-item__snippet">{{ item.snippet || '暂无摘要' }}</p>
                <p v-if="knowledgeMetaSummary(item)" class="report-source-item__meta">{{ knowledgeMetaSummary(item) }}</p>
              </article>
            </div>
          </section>
        </aside>
      </section>
    </template>

    <div v-else class="customer-demand-report-empty">
      <EmptyState
        title="还没有正式需求分析报告"
        description="你可以先回到会中工作台，点击“会后生成正式报告”，生成完成后再回来查看。"
      />
    </div>

    <el-dialog
      v-model="handoffDialogVisible"
      title="转入解决方案生成"
      width="900px"
      destroy-on-close
    >
      <div class="handoff-dialog">
        <section class="panel-card handoff-dialog__section">
          <div class="handoff-dialog__head">
            <div>
              <h3>生成请求草稿</h3>
              <p>这里会自动带入需求分析结果，你可以先人工确认和修改，再带到方案工作台。</p>
            </div>
            <div class="handoff-summary">
              <span v-for="item in handoffSummary" :key="item.label">{{ item.label }}：{{ item.value }}</span>
            </div>
          </div>

          <el-input
            v-model="handoffQuery"
            type="textarea"
            :rows="14"
            resize="vertical"
            placeholder="请确认导入到方案生成工作台的内容"
          />
        </section>

        <section class="panel-card handoff-dialog__section">
          <div class="handoff-dialog__head">
            <div>
              <h3>方案参数配置</h3>
              <p>系统已根据需求分析结果自动加载较匹配的参数，你仍然可以继续调整。</p>
            </div>
          </div>

          <div class="handoff-dialog__grid">
            <el-form-item label="方案场景">
              <el-select :model-value="handoffParams.scenario" @update:model-value="handleScenarioChange">
                <el-option
                  v-for="item in metaStore.options?.scenario_options || []"
                  :key="item.value"
                  :label="item.label"
                  :value="item.value"
                />
              </el-select>
            </el-form-item>

            <el-form-item label="电网环境">
              <el-select v-model="handoffParams.grid_environment">
                <el-option
                  v-for="item in metaStore.options?.grid_environment_options || []"
                  :key="item.value"
                  :label="item.label"
                  :value="item.value"
                />
              </el-select>
            </el-form-item>

            <el-form-item label="对象/设备">
              <el-select v-model="handoffParams.equipment_type">
                <el-option
                  v-for="item in metaStore.options?.equipment_type_options || []"
                  :key="item.value"
                  :label="item.label"
                  :value="item.value"
                />
              </el-select>
            </el-form-item>

            <el-form-item label="资源类型">
              <el-select v-model="handoffParams.resource_type">
                <el-option
                  v-for="item in metaStore.options?.resource_type_options || []"
                  :key="item.value"
                  :label="item.label"
                  :value="item.value"
                />
              </el-select>
            </el-form-item>

            <el-form-item label="协同范围">
              <el-select v-model="handoffParams.coordination_scope">
                <el-option
                  v-for="item in metaStore.options?.coordination_scope_options || []"
                  :key="item.value"
                  :label="item.label"
                  :value="item.value"
                />
              </el-select>
            </el-form-item>

            <el-form-item label="生命周期目标">
              <el-select v-model="handoffParams.lifecycle_goal">
                <el-option
                  v-for="item in metaStore.options?.lifecycle_goal_options || []"
                  :key="item.value"
                  :label="item.label"
                  :value="item.value"
                />
              </el-select>
            </el-form-item>
          </div>

          <div class="handoff-dialog__grid handoff-dialog__grid--wide">
            <el-form-item label="数据基础">
              <el-select
                :model-value="handoffParams.data_basis"
                multiple
                collapse-tags
                collapse-tags-tooltip
                @update:model-value="updateArrayField('data_basis', $event)"
              >
                <el-option
                  v-for="item in metaStore.options?.data_basis_options || []"
                  :key="item.value"
                  :label="item.label"
                  :value="item.value"
                />
              </el-select>
            </el-form-item>

            <el-form-item label="目标能力">
              <el-select
                :model-value="handoffParams.target_capability"
                multiple
                collapse-tags
                collapse-tags-tooltip
                @update:model-value="updateArrayField('target_capability', $event)"
              >
                <el-option
                  v-for="item in metaStore.options?.target_capability_options || []"
                  :key="item.value"
                  :label="item.label"
                  :value="item.value"
                />
              </el-select>
            </el-form-item>

            <el-form-item v-if="!scenarioFlags.isOther" label="市场/政策关注">
              <el-select
                :model-value="handoffParams.market_policy_focus"
                multiple
                collapse-tags
                collapse-tags-tooltip
                @update:model-value="updateArrayField('market_policy_focus', $event)"
              >
                <el-option
                  v-for="item in metaStore.options?.market_policy_focus_options || []"
                  :key="item.value"
                  :label="item.label"
                  :value="item.value"
                />
              </el-select>
            </el-form-item>

            <el-form-item v-if="scenarioFlags.isDistributionPlanning" label="规划目标">
              <el-select
                :model-value="handoffParams.planning_objective"
                multiple
                collapse-tags
                collapse-tags-tooltip
                @update:model-value="updateArrayField('planning_objective', $event)"
              >
                <el-option
                  v-for="item in metaStore.options?.planning_objective_options || []"
                  :key="item.value"
                  :label="item.label"
                  :value="item.value"
                />
              </el-select>
            </el-form-item>

            <el-form-item v-if="scenarioFlags.isPowerForecast" label="预测目标">
              <el-select
                :model-value="handoffParams.forecast_target"
                multiple
                collapse-tags
                collapse-tags-tooltip
                @update:model-value="updateArrayField('forecast_target', $event)"
              >
                <el-option
                  v-for="item in metaStore.options?.forecast_target_options || []"
                  :key="item.value"
                  :label="item.label"
                  :value="item.value"
                />
              </el-select>
            </el-form-item>
          </div>
        </section>
      </div>

      <template #footer>
        <div class="handoff-dialog__footer">
          <el-button @click="handoffDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="confirmHandoff">带入方案工作台</el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.customer-demand-report-shell {
  display: flex;
  flex-direction: column;
  gap: 18px;
  min-height: 100vh;
  padding: 22px;
}

.customer-demand-report-header,
.report-main,
.report-side__card,
.customer-demand-report-loading {
  padding: 20px 22px;
}

.customer-demand-report-header {
  display: flex;
  justify-content: space-between;
  gap: 18px;
}

.customer-demand-report-header__left {
  display: flex;
  gap: 16px;
  align-items: flex-start;
}

.customer-demand-report-header__left h1 {
  margin: 8px 0 0;
  line-height: 1.2;
}

.customer-demand-report-header__left p {
  margin: 6px 0 0;
  color: var(--muted);
  line-height: 1.6;
}

.customer-demand-report-header__actions {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}

.customer-demand-report-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.3fr) minmax(320px, 0.7fr);
  gap: 18px;
}

.report-main__head h2,
.report-side__card h3 {
  margin: 0;
}

.report-main__head p {
  margin: 8px 0 16px;
  color: var(--muted);
  line-height: 1.6;
}

.report-side__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
}

.report-side__head p {
  margin: 6px 0 0;
  color: var(--muted);
  line-height: 1.6;
}

.report-side {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.handoff-dialog {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.handoff-dialog__section {
  padding: 18px 20px;
}

.handoff-dialog__head {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 14px;
}

.handoff-dialog__head h3 {
  margin: 0 0 6px;
}

.handoff-dialog__head p {
  margin: 0;
  color: var(--muted);
  line-height: 1.6;
}

.handoff-summary {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 8px;
}

.handoff-summary span {
  padding: 6px 10px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.88);
  border: 1px solid rgba(15, 93, 140, 0.14);
  color: var(--muted);
  font-size: 12px;
}

.handoff-dialog__grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0 16px;
}

.handoff-dialog__grid--wide {
  margin-top: 8px;
}

.handoff-dialog__grid :deep(.el-form-item) {
  margin-bottom: 16px;
}

.handoff-dialog__grid :deep(.el-select) {
  width: 100%;
}

.handoff-dialog__footer {
  display: flex;
  justify-content: flex-end;
}

.report-meta-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  list-style: none;
  padding: 0;
  margin: 0;
}

.report-meta-list li {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  color: var(--muted);
}

.report-meta-list strong {
  color: var(--text);
}

.report-source-empty {
  color: var(--muted);
  line-height: 1.7;
}

.report-source-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.report-source-item {
  padding: 14px 14px 12px;
  border-radius: 16px;
  border: 1px solid rgba(15, 93, 140, 0.12);
  background: rgba(248, 252, 255, 0.9);
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.report-source-item__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.report-source-item__score {
  color: var(--muted);
  font-size: 12px;
}

.report-source-item__title {
  color: var(--text);
  line-height: 1.5;
}

.report-source-item__snippet,
.report-source-item__meta {
  margin: 0;
  color: var(--muted);
  line-height: 1.7;
  font-size: 13px;
}

.markdown-view {
  line-height: 1.85;
  color: var(--text);
}

.markdown-view :deep(h1),
.markdown-view :deep(h2),
.markdown-view :deep(h3),
.markdown-view :deep(h4) {
  margin-top: 0.9em;
  margin-bottom: 0.35em;
}

.markdown-view :deep(p) {
  margin: 0.55em 0;
}

.markdown-view :deep(ul),
.markdown-view :deep(ol) {
  padding-left: 22px;
}

@media (max-width: 1080px) {
  .customer-demand-report-grid {
    grid-template-columns: minmax(0, 1fr);
  }
}

@media (max-width: 768px) {
  .customer-demand-report-shell {
    padding: 16px;
  }

  .customer-demand-report-header {
    flex-direction: column;
  }

  .customer-demand-report-header__left {
    flex-direction: column;
  }

  .customer-demand-report-header__actions {
    flex-wrap: wrap;
  }

  .handoff-dialog__head {
    flex-direction: column;
  }

  .handoff-summary {
    justify-content: flex-start;
  }

  .handoff-dialog__grid {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
