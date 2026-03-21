<script setup lang="ts">
import { ArrowUp, EditPen, Setting, VideoPause } from '@element-plus/icons-vue'
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'

import { useMetaStore } from '@/stores/meta'
import { useWorkspaceStore } from '@/stores/workspace'

const metaStore = useMetaStore()
const workspace = useWorkspaceStore()
const expanded = ref(false)
const showParams = ref(false)
const isFocused = ref(false)
const isHovering = ref(false)
const openSelectCount = ref(0)
const conflictDialogVisible = ref(false)
const detectedScenario = ref('')
const conflictMode = ref<'switch' | 'keep'>('switch')
const shellRef = ref<HTMLElement | null>(null)
const inputRef = ref<{ focus?: () => void } | null>(null)
let collapseTimer: number | null = null

const canSubmit = computed(() => workspace.composerText.trim().length > 0 && !workspace.sending)
const hasMessages = computed(() => workspace.currentMessages.length > 0)
const isCompact = computed(
  () =>
    hasMessages.value &&
    !expanded.value &&
    !showParams.value &&
    !isFocused.value &&
    !workspace.composerText.trim() &&
    !workspace.sending,
)
const promptSuggestions = [
  '给我生成一个面向无锡地区的智能配电网故障诊断解决方案。',
  '请输出一个分布式储能聚合运营智能体解决方案，重点强调收益与寿命优化。',
]

const paramSummary = computed(() => {
  const options = metaStore.options
  if (!options) return []

  const resolveLabel = (items: { label: string; value: string }[], value: string) =>
    items.find((item) => item.value === value)?.label || value

  const resolveMany = (items: { label: string; value: string }[], values: string[]) =>
    values.map((value) => resolveLabel(items, value)).join(' / ')

  return [
    {
      label: '方案场景',
      value: resolveLabel(options.scenario_options, workspace.composerParams.scenario),
    },
    workspace.composerParams.grid_environment !== 'not_involved'
      ? {
          label: '电网环境',
          value: resolveLabel(options.grid_environment_options, workspace.composerParams.grid_environment),
        }
      : null,
    workspace.composerParams.equipment_type !== 'not_involved'
      ? {
          label: '对象/设备',
          value: resolveLabel(options.equipment_type_options, workspace.composerParams.equipment_type),
        }
      : null,
    workspace.composerParams.resource_type !== 'not_involved'
      ? {
          label: '资源类型',
          value: resolveLabel(options.resource_type_options, workspace.composerParams.resource_type),
        }
      : null,
    workspace.composerParams.data_basis.length
      ? {
          label: '数据基础',
          value: resolveMany(options.data_basis_options, workspace.composerParams.data_basis),
        }
      : null,
    workspace.composerParams.target_capability.length
      ? {
          label: '目标能力',
          value: resolveMany(options.target_capability_options, workspace.composerParams.target_capability),
        }
      : null,
    workspace.composerParams.market_policy_focus.length
      ? {
          label: '市场关注',
          value: resolveMany(options.market_policy_focus_options, workspace.composerParams.market_policy_focus),
        }
      : null,
    workspace.composerParams.planning_objective.length
      ? {
          label: '规划目标',
          value: resolveMany(options.planning_objective_options, workspace.composerParams.planning_objective),
        }
      : null,
    workspace.composerParams.forecast_target.length
      ? {
          label: '预测目标',
          value: resolveMany(options.forecast_target_options, workspace.composerParams.forecast_target),
        }
      : null,
    workspace.composerParams.coordination_scope !== 'not_involved'
      ? {
          label: '协同范围',
          value: resolveLabel(options.coordination_scope_options, workspace.composerParams.coordination_scope),
        }
      : null,
    workspace.composerParams.lifecycle_goal !== 'not_involved'
      ? {
          label: '生命周期目标',
          value: resolveLabel(options.lifecycle_goal_options, workspace.composerParams.lifecycle_goal),
        }
      : null,
  ].filter(Boolean) as Array<{ label: string; value: string }>
})

const scenarioFlags = computed(() => {
  const value = workspace.composerParams.scenario
  return {
    isFaultDiagnosis: value === 'fault_diagnosis_solution',
    isStorageAggregation: value === 'storage_aggregation_solution',
    isDistributionPlanning: value === 'distribution_planning_solution',
    isPowerForecast: value === 'power_forecast_solution',
    isVppCoordination: value === 'vpp_coordination_solution',
  }
})

const scenarioHint = computed(() => {
  if (scenarioFlags.value.isFaultDiagnosis) {
    return '适合补充故障对象、数据基础与诊断能力，未涉及项可不填。'
  }
  if (scenarioFlags.value.isStorageAggregation) {
    return '建议补充资源类型、市场关注点和生命周期目标，未涉及项可不填。'
  }
  if (scenarioFlags.value.isDistributionPlanning) {
    return '建议补充规划对象、规划目标和数据基础，未涉及项可不填。'
  }
  if (scenarioFlags.value.isPowerForecast) {
    return '建议补充预测目标、数据基础和目标能力，未涉及项可不填。'
  }
  if (scenarioFlags.value.isVppCoordination) {
    return '建议补充资源类型、协同范围和市场关注点，未涉及项可不填。'
  }
  return '这些设置仅影响本次提问，不会改动历史会话。'
})

const scenarioLabelMap = computed(() => {
  const map = new Map<string, string>()
  for (const item of metaStore.options?.scenario_options ?? []) {
    map.set(item.value, item.label)
  }
  return map
})

const currentScenarioLabel = computed(
  () => scenarioLabelMap.value.get(workspace.composerParams.scenario) || workspace.composerParams.scenario,
)

const detectedScenarioLabel = computed(
  () => scenarioLabelMap.value.get(detectedScenario.value) || detectedScenario.value,
)

function updateSelectOverlay(visible: boolean) {
  if (visible) {
    openSelectCount.value += 1
    clearCollapseTimer()
    return
  }
  openSelectCount.value = Math.max(0, openSelectCount.value - 1)
}

function detectScenarioFromQuery(query: string) {
  const normalized = query.trim().toLowerCase()
  if (!normalized) return null

  const scenarios = [
    {
      id: 'fault_diagnosis_solution',
      keywords: ['故障诊断', '故障定位', '故障', '接地选线', '自愈', '停电'],
    },
    {
      id: 'storage_aggregation_solution',
      keywords: ['储能聚合', '储能运营', '储能', '峰谷套利', '电池寿命', 'pcs', 'bms'],
    },
    {
      id: 'distribution_planning_solution',
      keywords: ['配网规划', '网架优化', '重过载', '台区规划', 'n-1', '投资效益'],
    },
    {
      id: 'power_forecast_solution',
      keywords: ['功率预测', '出力预测', '偏差考核', '日前预测', '日内预测', '短时预测'],
    },
    {
      id: 'vpp_coordination_solution',
      keywords: ['虚拟电厂', '源网荷储', '协同调度', '需求响应', '聚合调度', '可调负荷'],
    },
  ]

  const scores = scenarios.map((scenario) => ({
    id: scenario.id,
    score: scenario.keywords.reduce((sum, keyword) => sum + (normalized.includes(keyword) ? 1 : 0), 0),
  }))

  scores.sort((a, b) => b.score - a.score)
  const top = scores[0]
  if (!top || top.score <= 0) return null

  const current = scores.find((item) => item.id === workspace.composerParams.scenario)
  if (top.id === workspace.composerParams.scenario) return null
  if (top.score >= 2 || (top.score >= 1 && (current?.score ?? 0) === 0)) {
    return top.id
  }
  return null
}

function useSuggestion(text: string) {
  workspace.setComposerText(text)
  expandComposer()
}

async function handleEnter(event: KeyboardEvent) {
  if (event.shiftKey) return
  event.preventDefault()
  if (canSubmit.value) {
    await attemptSubmit()
  }
}

function resetParams() {
  workspace.resetComposerParams(metaStore.options?.default_params)
}

async function focusComposer() {
  await nextTick()
  inputRef.value?.focus?.()
}

async function expandComposer(options?: { openParams?: boolean; focus?: boolean }) {
  expanded.value = true
  if (options?.openParams !== undefined) {
    showParams.value = options.openParams
  }
  if (options?.focus !== false) {
    await focusComposer()
  }
}

function collapseComposer() {
  if (workspace.composerText.trim() || workspace.sending) return
  expanded.value = false
  showParams.value = false
  isFocused.value = false
}

function clearCollapseTimer() {
  if (collapseTimer) {
    window.clearTimeout(collapseTimer)
    collapseTimer = null
  }
}

function scheduleCollapse() {
  clearCollapseTimer()
  if (!hasMessages.value || workspace.composerText.trim() || workspace.sending || showParams.value || openSelectCount.value > 0) return
  collapseTimer = window.setTimeout(() => {
    collapseComposer()
  }, 180)
}

function toggleParams() {
  expanded.value = true
  showParams.value = !showParams.value
  if (showParams.value) {
    focusComposer()
  } else if (!isFocused.value && !isHovering.value) {
    scheduleCollapse()
  }
}

function handleFocus() {
  clearCollapseTimer()
  isFocused.value = true
  expanded.value = true
}

function handleBlur() {
  window.setTimeout(() => {
    isFocused.value = false
    if (!isHovering.value) {
      scheduleCollapse()
    }
  }, 120)
}

function handleMouseEnter() {
  isHovering.value = true
  clearCollapseTimer()
}

function handleMouseLeave() {
  isHovering.value = false
  collapseFromOutside()
}

function collapseFromOutside() {
  if (showParams.value || openSelectCount.value > 0) return
  const activeElement = document.activeElement as HTMLElement | null
  if (
    !workspace.composerText.trim() &&
    !workspace.sending &&
    activeElement &&
    shellRef.value?.contains(activeElement)
  ) {
    activeElement.blur()
  }
  scheduleCollapse()
}

async function attemptSubmit() {
  if (!canSubmit.value) return
  const suggestedScenario = detectScenarioFromQuery(workspace.composerText)
  if (suggestedScenario) {
    detectedScenario.value = suggestedScenario
    conflictMode.value = 'switch'
    conflictDialogVisible.value = true
    return
  }
  await workspace.submitCurrentMessage()
}

async function confirmScenarioConflict() {
  if (conflictMode.value === 'switch' && detectedScenario.value) {
    workspace.applyScenarioPreset(detectedScenario.value)
  }
  conflictDialogVisible.value = false
  await workspace.submitCurrentMessage()
}

function cancelScenarioConflict() {
  conflictDialogVisible.value = false
}

function handlePointerDown(event: PointerEvent) {
  const target = event.target as Node | null
  if (!target || shellRef.value?.contains(target)) return
  isHovering.value = false
  collapseFromOutside()
}

function handleWheel(event: WheelEvent) {
  const target = event.target as Node | null
  if (!target || shellRef.value?.contains(target)) return
  isHovering.value = false
  collapseFromOutside()
}

watch(
  hasMessages,
  (value) => {
    if (!value) {
      expanded.value = true
    }
  },
  { immediate: true },
)

onMounted(() => {
  document.addEventListener('pointerdown', handlePointerDown, true)
  window.addEventListener('wheel', handleWheel, { passive: true })
})

onBeforeUnmount(() => {
  clearCollapseTimer()
  document.removeEventListener('pointerdown', handlePointerDown, true)
  window.removeEventListener('wheel', handleWheel)
})
</script>

<template>
  <div
    ref="shellRef"
    class="composer-shell"
    @mouseenter="handleMouseEnter"
    @mouseleave="handleMouseLeave"
  >
    <transition name="composer-fade">
      <div v-if="showParams && metaStore.options" class="composer__params-sheet panel-card">
        <div class="composer__params-header">
          <div>
            <strong>参数配置</strong>
            <span>{{ scenarioHint }}</span>
          </div>
          <div class="composer__params-actions">
            <el-button text @click="resetParams">恢复默认参数</el-button>
            <el-button text @click="showParams = false">收起</el-button>
          </div>
        </div>

        <el-form label-position="top">
          <el-form-item label="方案场景">
            <el-select
              v-model="workspace.composerParams.scenario"
              placeholder="选择本次方案所属场景"
              @visible-change="updateSelectOverlay"
            >
              <el-option
                v-for="item in metaStore.options.scenario_options"
                :key="item.value"
                :label="item.label"
                :value="item.value"
              />
            </el-select>
          </el-form-item>

          <el-form-item label="电网环境">
            <el-select
              v-model="workspace.composerParams.grid_environment"
              placeholder="选择电网场景"
              @visible-change="updateSelectOverlay"
            >
              <el-option
                v-for="item in metaStore.options.grid_environment_options"
                :key="item.value"
                :label="item.label"
                :value="item.value"
              />
            </el-select>
          </el-form-item>

          <el-form-item
            v-if="scenarioFlags.isFaultDiagnosis || scenarioFlags.isDistributionPlanning"
            :label="scenarioFlags.isFaultDiagnosis ? '诊断对象/设备' : '规划对象/设备'"
          >
            <el-select
              v-model="workspace.composerParams.equipment_type"
              placeholder="选择对象"
              @visible-change="updateSelectOverlay"
            >
              <el-option
                v-for="item in metaStore.options.equipment_type_options"
                :key="item.value"
                :label="item.label"
                :value="item.value"
              />
            </el-select>
          </el-form-item>

          <el-form-item
            v-if="scenarioFlags.isStorageAggregation || scenarioFlags.isVppCoordination"
            label="资源类型"
          >
            <el-select
              v-model="workspace.composerParams.resource_type"
              placeholder="选择聚合或协同资源"
              @visible-change="updateSelectOverlay"
            >
              <el-option
                v-for="item in metaStore.options.resource_type_options"
                :key="item.value"
                :label="item.label"
                :value="item.value"
              />
            </el-select>
          </el-form-item>

          <el-form-item label="数据基础">
            <el-select
              v-model="workspace.composerParams.data_basis"
              multiple
              collapse-tags
              collapse-tags-tooltip
              placeholder="可多选，不涉及可留空"
              @visible-change="updateSelectOverlay"
            >
              <el-option
                v-for="item in metaStore.options.data_basis_options"
                :key="item.value"
                :label="item.label"
                :value="item.value"
              />
            </el-select>
          </el-form-item>

          <el-form-item label="目标能力">
            <el-select
              v-model="workspace.composerParams.target_capability"
              multiple
              collapse-tags
              collapse-tags-tooltip
              placeholder="可多选，不涉及可留空"
              @visible-change="updateSelectOverlay"
            >
              <el-option
                v-for="item in metaStore.options.target_capability_options"
                :key="item.value"
                :label="item.label"
                :value="item.value"
              />
            </el-select>
          </el-form-item>

          <el-form-item
            v-if="scenarioFlags.isStorageAggregation || scenarioFlags.isVppCoordination"
            label="市场/政策关注点"
          >
            <el-select
              v-model="workspace.composerParams.market_policy_focus"
              multiple
              collapse-tags
              collapse-tags-tooltip
              placeholder="可多选，不涉及可留空"
              @visible-change="updateSelectOverlay"
            >
              <el-option
                v-for="item in metaStore.options.market_policy_focus_options"
                :key="item.value"
                :label="item.label"
                :value="item.value"
              />
            </el-select>
          </el-form-item>

          <el-form-item v-if="scenarioFlags.isDistributionPlanning" label="规划目标">
            <el-select
              v-model="workspace.composerParams.planning_objective"
              multiple
              collapse-tags
              collapse-tags-tooltip
              placeholder="可多选，不涉及可留空"
              @visible-change="updateSelectOverlay"
            >
              <el-option
                v-for="item in metaStore.options.planning_objective_options"
                :key="item.value"
                :label="item.label"
                :value="item.value"
              />
            </el-select>
          </el-form-item>

          <el-form-item v-if="scenarioFlags.isPowerForecast" label="预测目标">
            <el-select
              v-model="workspace.composerParams.forecast_target"
              multiple
              collapse-tags
              collapse-tags-tooltip
              placeholder="可多选，不涉及可留空"
              @visible-change="updateSelectOverlay"
            >
              <el-option
                v-for="item in metaStore.options.forecast_target_options"
                :key="item.value"
                :label="item.label"
                :value="item.value"
              />
            </el-select>
          </el-form-item>

          <el-form-item v-if="scenarioFlags.isVppCoordination" label="协同范围">
            <el-select
              v-model="workspace.composerParams.coordination_scope"
              placeholder="选择协同范围"
              @visible-change="updateSelectOverlay"
            >
              <el-option
                v-for="item in metaStore.options.coordination_scope_options"
                :key="item.value"
                :label="item.label"
                :value="item.value"
              />
            </el-select>
          </el-form-item>

          <el-form-item
            v-if="scenarioFlags.isStorageAggregation || scenarioFlags.isVppCoordination"
            label="生命周期/运营目标"
          >
            <el-select
              v-model="workspace.composerParams.lifecycle_goal"
              placeholder="选择目标，或保持不涉及"
              @visible-change="updateSelectOverlay"
            >
              <el-option
                v-for="item in metaStore.options.lifecycle_goal_options"
                :key="item.value"
                :label="item.label"
                :value="item.value"
              />
            </el-select>
          </el-form-item>
        </el-form>
      </div>
    </transition>

    <div :class="['composer panel-card', { 'composer--compact': isCompact }]">
      <template v-if="isCompact">
        <div class="composer__compact">
          <button class="composer__compact-trigger" @click="expandComposer()">
            <span class="composer__compact-label">继续追问或输入新的电力场景需求</span>
            <span class="composer__compact-placeholder">
              例如：为无锡某地区生成智能配电网故障诊断解决方案
            </span>
          </button>
          <div class="composer__compact-actions">
            <el-button text @click="toggleParams">
              <el-icon><Setting /></el-icon>
              参数
            </el-button>
            <el-button type="primary" round @click="expandComposer()">
              <el-icon><EditPen /></el-icon>
              展开编辑
            </el-button>
          </div>
        </div>
      </template>

      <template v-else>
        <div class="composer__header">
          <div class="composer__header-left">
            <el-button text @click="toggleParams">
              <el-icon><Setting /></el-icon>
              {{ showParams ? '收起参数' : '参数配置' }}
            </el-button>
            <span>当前参数仅对本次发送生效</span>
          </div>
          <div class="composer__header-actions">
            <el-button text @click="resetParams">恢复默认参数</el-button>
            <el-button v-if="hasMessages" text @click="collapseComposer">收起编辑区</el-button>
          </div>
        </div>

        <div class="composer__summary">
          <span v-for="item in paramSummary" :key="item.label" class="composer__summary-tag">
            <strong>{{ item.label }}</strong>
            <em>{{ item.value }}</em>
          </span>
        </div>

        <el-input
          ref="inputRef"
          v-model="workspace.composerText"
          type="textarea"
          :autosize="{ minRows: 2, maxRows: 8 }"
          resize="none"
          placeholder="输入你的电力业务场景需求，例如：请给我生成一个配电网故障诊断智能体解决方案。"
          @focus="handleFocus"
          @blur="handleBlur"
          @keydown.enter.exact="handleEnter"
          @keydown.ctrl.enter.prevent="attemptSubmit"
          @keydown.meta.enter.prevent="attemptSubmit"
        />

        <div class="composer__prompt-tools">
          <div class="composer__suggestions">
            <button
              v-for="item in promptSuggestions"
              :key="item"
              class="composer__suggestion"
              @click="useSuggestion(item)"
            >
              {{ item }}
            </button>
          </div>
          <span>{{ workspace.composerText.trim().length }} 字</span>
        </div>

        <div class="composer__actions">
          <span>Enter 发送，Shift + Enter 换行，Ctrl/Command + Enter 也可发送</span>
          <div class="composer__buttons">
            <el-button v-if="workspace.sending" type="danger" plain @click="workspace.stopCurrentTask()">
              <el-icon><VideoPause /></el-icon>
              停止
            </el-button>
            <el-button type="primary" round :disabled="!canSubmit" @click="attemptSubmit">
              <el-icon><ArrowUp /></el-icon>
              发送
            </el-button>
          </div>
        </div>
      </template>
    </div>
  </div>

  <el-dialog
    v-model="conflictDialogVisible"
    title="场景与输入内容可能不一致"
    width="560px"
    destroy-on-close
  >
    <div class="composer__conflict-body">
      <p>
        我们从你的输入里更像识别到了
        <strong>{{ detectedScenarioLabel }}</strong>
        ，但当前参数配置选择的是
        <strong>{{ currentScenarioLabel }}</strong>
        。
      </p>
      <p>为了避免按错模板和参数生成，我们先帮你确认一次。</p>

      <div class="composer__conflict-options">
        <button
          :class="['composer__conflict-option', { 'is-active': conflictMode === 'switch' }]"
          @click="conflictMode = 'switch'"
        >
          <strong>切换到识别场景</strong>
          <span>自动切换到 {{ detectedScenarioLabel }}，并套用更合适的参数建议。</span>
        </button>
        <button
          :class="['composer__conflict-option', { 'is-active': conflictMode === 'keep' }]"
          @click="conflictMode = 'keep'"
        >
          <strong>保持当前场景</strong>
          <span>继续使用 {{ currentScenarioLabel }} 及当前参数配置生成方案。</span>
        </button>
      </div>
    </div>

    <template #footer>
      <div class="composer__conflict-footer">
        <el-button @click="cancelScenarioConflict">返回继续编辑</el-button>
        <el-button type="primary" @click="confirmScenarioConflict">确认并继续</el-button>
      </div>
    </template>
  </el-dialog>
</template>

<style scoped>
.composer-shell {
  position: relative;
  background: transparent;
}

.composer {
  padding: 16px;
  transition: box-shadow 0.2s ease, transform 0.2s ease;
}

.composer--compact {
  padding: 10px 12px;
  border-radius: 22px;
  box-shadow: 0 8px 20px rgba(15, 38, 56, 0.06);
}

.composer__header,
.composer__actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.composer__header {
  margin-bottom: 12px;
}

.composer__header-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.composer__header-left {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.composer__header span,
.composer__actions span {
  font-size: 12px;
  color: var(--muted);
}

.composer__summary {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 14px;
}

.composer__summary-tag {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border-radius: 999px;
  background: rgba(15, 93, 140, 0.06);
  border: 1px solid rgba(15, 93, 140, 0.08);
  font-size: 12px;
}

.composer__summary-tag strong {
  color: var(--accent);
}

.composer__summary-tag em {
  color: var(--muted);
  font-style: normal;
}

.composer__params {
  margin-bottom: 14px;
  padding: 12px;
  border-radius: 18px;
  background: var(--panel-soft);
}

.composer__params-sheet {
  position: absolute;
  left: 0;
  right: 0;
  bottom: calc(100% + 12px);
  z-index: 20;
  padding: 16px;
  box-shadow: 0 18px 40px rgba(15, 38, 56, 0.16);
}

.composer__params-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  margin-bottom: 14px;
}

.composer__params-header strong {
  display: block;
  margin-bottom: 4px;
  color: var(--text);
}

.composer__params-header span {
  font-size: 12px;
  color: var(--muted);
}

.composer__params-actions {
  display: flex;
  gap: 8px;
}

.composer__prompt-tools {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-top: 14px;
  margin-bottom: 14px;
}

.composer__prompt-tools span {
  font-size: 12px;
  color: #8aa0b0;
  white-space: nowrap;
}

.composer__conflict-body {
  display: flex;
  flex-direction: column;
  gap: 12px;
  color: var(--text);
}

.composer__conflict-body p {
  margin: 0;
  line-height: 1.7;
  color: var(--muted);
}

.composer__conflict-body strong {
  color: var(--text);
}

.composer__conflict-options {
  display: grid;
  grid-template-columns: 1fr;
  gap: 12px;
  margin-top: 6px;
}

.composer__conflict-option {
  text-align: left;
  padding: 14px 16px;
  border-radius: 18px;
  border: 1px solid rgba(15, 93, 140, 0.12);
  background: #fff;
  cursor: pointer;
  transition: 0.18s ease;
}

.composer__conflict-option:hover {
  border-color: rgba(15, 93, 140, 0.24);
  transform: translateY(-1px);
}

.composer__conflict-option.is-active {
  border-color: rgba(15, 93, 140, 0.36);
  background: rgba(15, 93, 140, 0.05);
  box-shadow: inset 0 0 0 1px rgba(15, 93, 140, 0.1);
}

.composer__conflict-option strong,
.composer__conflict-option span {
  display: block;
}

.composer__conflict-option strong {
  margin-bottom: 6px;
  font-size: 14px;
  color: var(--text);
}

.composer__conflict-option span {
  font-size: 12px;
  line-height: 1.6;
  color: var(--muted);
}

.composer__conflict-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.composer__suggestions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.composer__suggestion {
  padding: 8px 12px;
  border-radius: 999px;
  border: 1px solid rgba(15, 93, 140, 0.12);
  background: white;
  color: var(--text);
  cursor: pointer;
  transition: 0.18s ease;
}

.composer__suggestion:hover {
  border-color: rgba(15, 93, 140, 0.28);
  color: var(--accent);
  transform: translateY(-1px);
}

.composer__buttons {
  display: flex;
  gap: 8px;
}

.composer__compact {
  display: flex;
  align-items: center;
  gap: 14px;
}

.composer__compact-trigger {
  flex: 1;
  min-width: 0;
  text-align: left;
  border: 0;
  background: transparent;
  padding: 2px 4px;
  cursor: text;
}

.composer__compact-label {
  display: block;
  font-size: 13px;
  font-weight: 600;
  color: var(--text);
  margin-bottom: 2px;
}

.composer__compact-placeholder {
  display: block;
  font-size: 12px;
  color: var(--muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.composer__compact-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.composer-fade-enter-active,
.composer-fade-leave-active {
  transition: opacity 0.16s ease, transform 0.16s ease;
}

.composer-fade-enter-from,
.composer-fade-leave-to {
  opacity: 0;
  transform: translateY(8px);
}

:deep(.el-form) {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

:deep(.el-form-item) {
  margin-bottom: 0;
}

@media (max-width: 760px) {
  :deep(.el-form) {
    grid-template-columns: 1fr;
  }

  .composer__compact,
  .composer__params-header,
  .composer__prompt-tools,
  .composer__actions,
  .composer__header {
    flex-direction: column;
    align-items: flex-start;
  }

  .composer__compact-actions,
  .composer__header-actions,
  .composer__params-actions {
    width: 100%;
    justify-content: flex-start;
    flex-wrap: wrap;
  }

  .composer__compact-placeholder {
    white-space: normal;
  }
}
</style>
