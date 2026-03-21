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
  '帮我形成一个新能源功率预测智能体方案，强调预测偏差考核与数据体系。',
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
      label: '电网场景',
      value: resolveLabel(options.grid_environment_options, workspace.composerParams.grid_environment),
    },
    {
      label: '诊断对象',
      value: resolveLabel(options.equipment_type_options, workspace.composerParams.equipment_type),
    },
    {
      label: '数据基础',
      value: resolveMany(options.data_basis_options, workspace.composerParams.data_basis),
    },
    {
      label: '目标能力',
      value: resolveMany(options.target_capability_options, workspace.composerParams.target_capability),
    },
  ]
})

function useSuggestion(text: string) {
  workspace.setComposerText(text)
  expandComposer()
}

function handleEnter(event: KeyboardEvent) {
  if (event.shiftKey) return
  event.preventDefault()
  if (canSubmit.value) {
    workspace.submitCurrentMessage()
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
  if (!hasMessages.value || workspace.composerText.trim() || workspace.sending) return
  collapseTimer = window.setTimeout(() => {
    collapseComposer()
  }, 180)
}

function toggleParams() {
  expanded.value = true
  showParams.value = !showParams.value
  if (showParams.value) {
    focusComposer()
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
            <span>这些设置仅影响本次提问，不会改动历史会话。</span>
          </div>
          <div class="composer__params-actions">
            <el-button text @click="resetParams">恢复默认参数</el-button>
            <el-button text @click="showParams = false">收起</el-button>
          </div>
        </div>

        <el-form label-position="top">
          <el-form-item label="电网场景">
            <el-select v-model="workspace.composerParams.grid_environment" placeholder="选择电网场景">
              <el-option
                v-for="item in metaStore.options.grid_environment_options"
                :key="item.value"
                :label="item.label"
                :value="item.value"
              />
            </el-select>
          </el-form-item>

          <el-form-item label="诊断对象">
            <el-select v-model="workspace.composerParams.equipment_type" placeholder="选择对象">
              <el-option
                v-for="item in metaStore.options.equipment_type_options"
                :key="item.value"
                :label="item.label"
                :value="item.value"
              />
            </el-select>
          </el-form-item>

          <el-form-item label="数据基础">
            <el-select v-model="workspace.composerParams.data_basis" multiple collapse-tags>
              <el-option
                v-for="item in metaStore.options.data_basis_options"
                :key="item.value"
                :label="item.label"
                :value="item.value"
              />
            </el-select>
          </el-form-item>

          <el-form-item label="目标能力">
            <el-select v-model="workspace.composerParams.target_capability" multiple collapse-tags>
              <el-option
                v-for="item in metaStore.options.target_capability_options"
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
          @keydown.ctrl.enter.prevent="workspace.submitCurrentMessage()"
          @keydown.meta.enter.prevent="workspace.submitCurrentMessage()"
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
            <el-button type="primary" round :disabled="!canSubmit" @click="workspace.submitCurrentMessage()">
              <el-icon><ArrowUp /></el-icon>
              发送
            </el-button>
          </div>
        </div>
      </template>
    </div>
  </div>
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
