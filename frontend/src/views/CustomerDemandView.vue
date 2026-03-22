<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import {
  ArrowLeft,
  ChatDotRound,
  CircleCheck,
  Connection,
  Document,
  Expand,
  Fold,
  Microphone,
  Opportunity,
  QuestionFilled,
  Refresh,
  Right,
  Search,
  UploadFilled,
  VideoPause,
  VideoPlay,
  Warning,
} from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useRouter } from 'vue-router'

import EmptyState from '@/components/common/EmptyState.vue'
import { useAuthStore } from '@/stores/auth'
import { useCustomerDemandStore } from '@/stores/customerDemand'
import { renderMarkdown } from '@/utils/markdown'
import { formatDateTime, formatRelativeTime } from '@/utils/time'

type ReviewDecision = 'accept' | 'discard'

const router = useRouter()
const authStore = useAuthStore()
const demandStore = useCustomerDemandStore()
const keyword = ref('')
const sidebarCollapsed = ref(false)
const createDialogVisible = ref(false)
const uploadInputRef = ref<HTMLInputElement | null>(null)
const reviewDialogVisible = ref(false)
const reviewForm = reactive({
  segmentId: '',
  decision: 'accept' as ReviewDecision,
  editedText: '',
  note: '',
})
const createForm = reactive({
  customer_name: '',
  session_title: '',
  industry: '',
  region: '',
  topic: '',
  customer_type: '',
  knowledge_enabled: false,
  remarks: '',
})

const filteredSessions = computed(() => {
  const normalized = keyword.value.trim().toLowerCase()
  if (!normalized) return demandStore.sessions
  return demandStore.sessions.filter((item) =>
    [item.customer_name, item.session_title, item.topic, item.industry, item.region]
      .join(' ')
      .toLowerCase()
      .includes(normalized),
  )
})

const currentStatusLabel = computed(() => {
  const statusMap: Record<string, string> = {
    draft: '草稿',
    recording: '记录中',
    paused: '已暂停',
    closed: '已结束',
    analyzing: '分析中',
    completed: '已完成',
    failed: '失败',
    archived: '已归档',
  }
  return statusMap[demandStore.currentSession?.status || 'draft'] || demandStore.currentSession?.status || '草稿'
})

const activityLabel = computed(() => {
  if (demandStore.uploadingAudio) return '正在调用 Qwen ASR 识别音频分片'
  if (demandStore.actionLoading) return '正在执行当前分析动作'
  if (demandStore.currentTask?.current_step_label) return demandStore.currentTask.current_step_label
  return '准备开始记录客户沟通内容'
})

const createDisabled = computed(() => !createForm.customer_name.trim() || !createForm.session_title.trim())

const latestSummaryPayload = computed<Record<string, unknown>>(
  () => demandStore.latestStageSummary?.summary_payload || {},
)

function payloadList(key: string) {
  const value = latestSummaryPayload.value[key]
  return Array.isArray(value) ? value.map((item) => String(item).trim()).filter(Boolean) : []
}

function compactPromptText(text: string, limit = 48) {
  const normalized = String(text || '')
    .replace(/\s+/g, ' ')
    .replace(/[；;。！？!?]/g, '，')
    .trim()
  const firstClause = normalized.split('，').map((item) => item.trim()).filter(Boolean)[0] || normalized
  if (firstClause.length <= limit) return firstClause
  return `${firstClause.slice(0, limit).trim()}...`
}

function compactList(items: string[], limit = 3, textLimit = 48) {
  return items.slice(0, limit).map((item) => compactPromptText(item, textLimit))
}

const currentTopics = computed(() => payloadList('current_topics'))
const confirmedRequirements = computed(() => payloadList('confirmed_requirements'))
const pendingQuestions = computed(() => payloadList('pending_questions'))
const potentialDirections = computed(() => payloadList('potential_directions'))
const riskPoints = computed(() => payloadList('risk_points'))
const semanticWarnings = computed(() => payloadList('semantic_warnings'))

const currentTopicsCompact = computed(() => compactList(currentTopics.value, 3, 42))
const confirmedRequirementsCompact = computed(() => compactList(confirmedRequirements.value, 3, 44))
const pendingQuestionsCompact = computed(() => compactList(pendingQuestions.value, 3, 44))
const potentialDirectionsCompact = computed(() => compactList(potentialDirections.value, 3, 42))
const riskPointsCompact = computed(() => compactList(riskPoints.value, 3, 42))
const semanticWarningsCompact = computed(() => compactList(semanticWarnings.value, 3, 42))

const quickInsightCards = computed(() => [
  {
    title: '已明确需求',
    description: '客户已经明确表达的重点。',
    items: confirmedRequirementsCompact.value,
    tone: 'success',
    icon: CircleCheck,
    actionLabel: '可以继续压实量化指标',
  },
  {
    title: '待确认问题',
    description: '现场建议继续追问的点。',
    items: pendingQuestionsCompact.value,
    tone: 'warning',
    icon: QuestionFilled,
    actionLabel: '优先补问缺失信息',
  },
  {
    title: '下一步可深挖',
    description: '顺着客户表达继续展开。',
    items: potentialDirectionsCompact.value,
    tone: 'primary',
    icon: Opportunity,
    actionLabel: '适合继续向价值点追问',
  },
  {
    title: '风险与约束',
    description: '当前需要提醒的限制条件。',
    items: riskPointsCompact.value,
    tone: 'danger',
    icon: Warning,
    actionLabel: '避免后续方案边界反复',
  },
])

function sessionAvatarLabel(title: string) {
  const cleaned = (title || '会').trim()
  return cleaned.slice(0, 2)
}

async function handleCreateSession() {
  if (createDisabled.value) {
    ElMessage.warning('请先填写客户名称和会话标题')
    return
  }
  await demandStore.createSession({
    customer_name: createForm.customer_name.trim(),
    session_title: createForm.session_title.trim(),
    industry: createForm.industry.trim(),
    region: createForm.region.trim(),
    topic: createForm.topic.trim(),
    customer_type: createForm.customer_type.trim(),
    knowledge_enabled: createForm.knowledge_enabled,
    remarks: createForm.remarks.trim(),
    knowledge_scope: {},
  })
  createDialogVisible.value = false
  Object.assign(createForm, {
    customer_name: '',
    session_title: '',
    industry: '',
    region: '',
    topic: '',
    customer_type: '',
    knowledge_enabled: false,
    remarks: '',
  })
}

async function handleSelectSession(sessionId: string) {
  await demandStore.selectSession(sessionId)
}

function triggerAudioUpload() {
  uploadInputRef.value?.click()
}

async function handleAudioPicked(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  await demandStore.uploadAudio(file)
  input.value = ''
}

async function handleExportReport() {
  await demandStore.exportCurrentReport()
}

function semanticScoreDisplay(value: string | number | null | undefined) {
  if (value === null || value === undefined || value === '') return '--'
  const parsed = Number(value)
  return Number.isNaN(parsed) ? String(value) : parsed.toFixed(2)
}

function segmentStatusType(status: string) {
  if (status === 'normalized') return 'success'
  if (status === 'review_required') return 'warning'
  if (status === 'discarded') return 'danger'
  return 'info'
}

function segmentStatusLabel(status: string) {
  const map: Record<string, string> = {
    draft: '草稿',
    asr_ready: '已识别',
    normalized: '已通过',
    review_required: '待复核',
    discarded: '已丢弃',
  }
  return map[status] || status
}

function openReviewDialog(segment: any, decision: ReviewDecision) {
  reviewForm.segmentId = segment.id
  reviewForm.decision = decision
  reviewForm.editedText = segment.final_text || segment.normalized_text || segment.raw_text || ''
  reviewForm.note = ''
  reviewDialogVisible.value = true
}

async function submitReview() {
  if (!reviewForm.segmentId) return
  await demandStore.reviewSegment(reviewForm.segmentId, {
    decision: reviewForm.decision,
    edited_text: reviewForm.decision === 'accept' ? reviewForm.editedText.trim() : undefined,
    note: reviewForm.note.trim() || undefined,
  })
  reviewDialogVisible.value = false
}

function openReportPage() {
  if (!demandStore.currentSessionId) return
  router.push(`/customer-demand/${demandStore.currentSessionId}/report`)
}

onMounted(async () => {
  await demandStore.loadSessions()
  if (demandStore.currentSessionId) {
    await demandStore.selectSession(demandStore.currentSessionId)
  }
})
</script>

<template>
  <div class="customer-demand-shell" :class="{ 'is-sidebar-collapsed': sidebarCollapsed }">
    <aside class="customer-demand-sidebar">
      <div class="customer-demand-sidebar__top">
        <div class="customer-demand-sidebar__toolbar">
          <el-tooltip :content="sidebarCollapsed ? '展开会话栏' : '收起会话栏'" placement="right">
            <el-button circle @click="sidebarCollapsed = !sidebarCollapsed">
              <el-icon><component :is="sidebarCollapsed ? Expand : Fold" /></el-icon>
            </el-button>
          </el-tooltip>
          <el-tooltip content="返回方案工作台" placement="right">
            <el-button circle plain @click="router.push('/')">
              <el-icon><ArrowLeft /></el-icon>
            </el-button>
          </el-tooltip>
          <el-tooltip content="新建沟通会话" placement="right">
            <el-button circle type="primary" @click="createDialogVisible = true">
              <el-icon><ChatDotRound /></el-icon>
            </el-button>
          </el-tooltip>
        </div>

        <template v-if="!sidebarCollapsed">
          <div class="customer-demand-sidebar__account panel-card">
            <div>
              <strong>{{ authStore.displayName || '未登录用户' }}</strong>
              <p>{{ authStore.user?.department?.name || '未设置部门' }}</p>
            </div>
            <el-button text @click="router.push('/')">返回方案工作台</el-button>
          </div>

          <div class="customer-demand-sidebar__hero">
            <p class="section-title">Demand Agent</p>
            <h1>客户需求分析工作台</h1>
            <p>会中优先帮助你明确需求、挖掘问题、识别风险，会后再单独查看完整分析报告。</p>
          </div>

          <el-input v-model="keyword" placeholder="搜索客户、主题或区域" clearable>
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>
        </template>
      </div>

      <div v-if="!sidebarCollapsed" class="customer-demand-sidebar__list panel-card">
        <div class="customer-demand-sidebar__list-head">
          <strong>沟通会话</strong>
          <span>{{ filteredSessions.length }}</span>
        </div>
        <div v-if="demandStore.loadingSessions" class="customer-demand-sidebar__empty">正在加载会话...</div>
        <div v-else-if="!filteredSessions.length" class="customer-demand-sidebar__empty">
          还没有客户需求会话，先创建一条开始试跑吧。
        </div>
        <button
          v-for="item in filteredSessions"
          :key="item.id"
          class="customer-demand-sidebar__item"
          :class="{ 'is-active': item.id === demandStore.currentSessionId }"
          @click="handleSelectSession(item.id)"
        >
          <div class="customer-demand-sidebar__item-top">
            <strong>{{ item.session_title }}</strong>
            <span>{{ formatRelativeTime(item.updated_at) }}</span>
          </div>
          <p>{{ item.customer_name }} · {{ item.region || '未标注区域' }}</p>
          <small>{{ item.topic || '未补充会话主题' }}</small>
        </button>
      </div>

      <div v-else class="customer-demand-sidebar__mini-list panel-card">
        <div v-if="demandStore.loadingSessions" class="customer-demand-sidebar__mini-empty">加载中</div>
        <div v-else-if="!filteredSessions.length" class="customer-demand-sidebar__mini-empty">空</div>
        <el-tooltip
          v-for="item in filteredSessions"
          :key="item.id"
          :content="`${item.session_title} · ${item.customer_name}`"
          placement="right"
        >
          <button
            class="customer-demand-sidebar__mini-item"
            :class="{ 'is-active': item.id === demandStore.currentSessionId }"
            @click="handleSelectSession(item.id)"
          >
            {{ sessionAvatarLabel(item.session_title) }}
          </button>
        </el-tooltip>
      </div>
    </aside>

    <main class="customer-demand-main">
      <header class="customer-demand-header panel-card">
        <div>
          <p class="section-title">In-Meeting Copilot</p>
          <h2>{{ demandStore.currentSession?.session_title || '请选择或创建一个沟通会话' }}</h2>
          <p>
            {{ demandStore.currentSession?.customer_name || '尚未选中客户' }}
            <span v-if="demandStore.currentSession?.region"> · {{ demandStore.currentSession?.region }}</span>
            <span v-if="demandStore.currentSession?.industry"> · {{ demandStore.currentSession?.industry }}</span>
          </p>
        </div>
        <div class="customer-demand-header__meta">
          <el-tag effect="plain">{{ currentStatusLabel }}</el-tag>
          <el-tag effect="plain" type="info">{{ demandStore.segments.length }} 条分段</el-tag>
          <el-tag effect="plain" type="success">{{ demandStore.stageSummaries.length }} 版阶段整理</el-tag>
        </div>
      </header>

      <div v-if="!demandStore.currentSession" class="customer-demand-empty">
        <EmptyState
          title="客户需求分析智能体已就绪"
          description="先创建一条客户沟通会话，然后就可以开始记录现场交流、上传语音分片、生成阶段整理，并在会后单独查看正式需求分析报告。"
        />
      </div>

      <template v-else>
        <section class="customer-demand-grid">
          <div class="customer-demand-column customer-demand-column--workspace">
            <section class="customer-card panel-card">
              <div class="customer-card__head">
                <div>
                  <h3>会话信息</h3>
                  <p>补齐客户、主题和知识库开关，后续会中提示与会后报告都会沿用这里的信息。</p>
                </div>
                <el-button :loading="demandStore.savingProfile" type="primary" plain @click="demandStore.saveCurrentSessionProfile()">
                  保存信息
                </el-button>
              </div>

              <div class="customer-card__form">
                <el-input v-model="demandStore.draftForm.customer_name" placeholder="客户名称" />
                <el-input v-model="demandStore.draftForm.session_title" placeholder="会话标题" />
                <el-input v-model="demandStore.draftForm.industry" placeholder="行业" />
                <el-input v-model="demandStore.draftForm.region" placeholder="区域" />
                <el-input v-model="demandStore.draftForm.topic" placeholder="主题，例如：智慧园区能源管理" />
                <el-input v-model="demandStore.draftForm.customer_type" placeholder="客户类型，例如：供电公司 / 园区业主" />
                <el-switch
                  v-model="demandStore.draftForm.knowledge_enabled"
                  active-text="允许分析时参考知识库"
                  inactive-text="仅根据当前沟通内容分析"
                />
                <el-input
                  v-model="demandStore.draftForm.remarks"
                  type="textarea"
                  :rows="3"
                  placeholder="可选：补充现场背景、已知约束或内部备注"
                />
              </div>
            </section>

            <section class="customer-card panel-card">
              <div class="customer-card__head">
                <div>
                  <h3>记录控制</h3>
                  <p>当前活动：{{ activityLabel }}</p>
                </div>
                <div class="customer-card__actions">
                  <el-button :loading="demandStore.actionLoading" type="primary" @click="demandStore.startRecording()">
                    <el-icon><VideoPlay /></el-icon>
                    开始记录
                  </el-button>
                  <el-button :loading="demandStore.actionLoading" @click="demandStore.pauseRecording()">
                    <el-icon><VideoPause /></el-icon>
                    暂停
                  </el-button>
                  <el-button :loading="demandStore.actionLoading" type="danger" plain @click="demandStore.stopRecording()">
                    <el-icon><Microphone /></el-icon>
                    结束记录
                  </el-button>
                </div>
              </div>

              <div class="customer-card__manual">
                <el-input
                  v-model="demandStore.manualInput"
                  type="textarea"
                  :rows="4"
                  placeholder="MVP 阶段支持手动补录：把现场沟通中的一句或一段内容贴进来，直接形成一条结构化分段。"
                />
                <div class="customer-card__manual-bar">
                  <el-select v-model="demandStore.speakerLabel" style="width: 140px">
                    <el-option label="客户" value="客户" />
                    <el-option label="销售" value="销售" />
                    <el-option label="技术支持" value="技术支持" />
                    <el-option label="项目经理" value="项目经理" />
                  </el-select>
                  <div class="customer-card__manual-actions">
                    <input
                      ref="uploadInputRef"
                      type="file"
                      accept="audio/*"
                      class="customer-card__file-input"
                      @change="handleAudioPicked"
                    />
                    <el-button :loading="demandStore.uploadingAudio" plain @click="triggerAudioUpload">
                      <el-icon><UploadFilled /></el-icon>
                      上传音频分片
                    </el-button>
                    <el-button :loading="demandStore.actionLoading" type="primary" @click="demandStore.appendManualSegment()">
                      补录文本分段
                    </el-button>
                  </div>
                </div>
              </div>
            </section>

            <section class="customer-card panel-card customer-card--segments">
              <div class="customer-card__head">
                <div>
                  <h3>沟通分段</h3>
                  <p>这里会累积现场转写、人工补录和语义校验后的最终文本。</p>
                </div>
                <el-button plain @click="demandStore.selectSession(demandStore.currentSession.id)">
                  <el-icon><Refresh /></el-icon>
                  刷新
                </el-button>
              </div>

              <div v-if="!demandStore.sortedSegments.length" class="customer-card__empty">
                还没有分段内容。你可以先手动补录一段文本，或者上传一段音频做 ASR 识别。
              </div>
              <div v-else class="segment-list">
                <article v-for="segment in demandStore.sortedSegments" :key="segment.id" class="segment-item">
                  <div class="segment-item__head">
                    <div class="segment-item__head-main">
                      <strong>#{{ segment.sequence_no }} {{ segment.speaker_label || '未标注说话人' }}</strong>
                      <div class="segment-item__badges">
                        <el-tag size="small" :type="segmentStatusType(segment.segment_status)" effect="light">
                          {{ segmentStatusLabel(segment.segment_status) }}
                        </el-tag>
                        <el-tag size="small" effect="plain" type="info">{{ segment.asr_provider || 'manual' }}</el-tag>
                        <el-tag size="small" effect="plain">语义分：{{ semanticScoreDisplay(segment.semantic_score) }}</el-tag>
                      </div>
                    </div>
                    <span>{{ formatDateTime(segment.created_at) }}</span>
                  </div>
                  <p>{{ segment.final_text || segment.normalized_text || segment.raw_text || '当前分段暂无文本' }}</p>
                  <div class="segment-item__meta">
                    <div class="segment-item__meta-text">
                      <span v-if="segment.semantic_payload?.reasoning" class="segment-item__reasoning">
                        {{ String(segment.semantic_payload.reasoning) }}
                      </span>
                      <span v-if="segment.issues_json?.length" class="segment-item__issues">
                        {{ segment.issues_json.join('；') }}
                      </span>
                    </div>
                    <div v-if="segment.review_flag" class="segment-item__review-actions">
                      <el-button size="small" type="success" plain @click="openReviewDialog(segment, 'accept')">人工保留</el-button>
                      <el-button size="small" type="danger" plain @click="openReviewDialog(segment, 'discard')">确认丢弃</el-button>
                    </div>
                  </div>
                </article>
              </div>
            </section>
          </div>

          <div class="customer-demand-column customer-demand-column--copilot">
            <section class="customer-card panel-card">
              <div class="customer-card__head">
                <div>
                  <h3>会中辅助动作</h3>
                  <p>会中先看提示卡，会后再看完整报告。</p>
                </div>
              </div>
              <div class="insight-actions">
                <el-button :loading="demandStore.actionLoading" type="primary" @click="demandStore.triggerStageSummaryNow()">
                  <el-icon><Connection /></el-icon>
                  生成阶段整理
                </el-button>
                <el-button :loading="demandStore.actionLoading" type="success" @click="demandStore.triggerFinalAnalysisNow()">
                  <el-icon><Document /></el-icon>
                  会后生成正式报告
                </el-button>
              </div>
              <div v-if="demandStore.operationState.visible" class="operation-status-card" :class="`is-${demandStore.operationState.status}`">
                <div class="operation-status-card__head">
                  <div>
                    <strong>{{ demandStore.operationState.title }}</strong>
                    <p>{{ demandStore.operationState.message }}</p>
                  </div>
                  <el-tag
                    :type="
                      demandStore.operationState.status === 'success'
                        ? 'success'
                        : demandStore.operationState.status === 'error'
                          ? 'danger'
                          : 'primary'
                    "
                    effect="light"
                  >
                    {{
                      demandStore.operationState.status === 'success'
                        ? '已完成'
                        : demandStore.operationState.status === 'error'
                          ? '失败'
                          : '进行中'
                    }}
                  </el-tag>
                </div>
                <el-progress
                  :percentage="demandStore.operationState.progress"
                  :status="
                    demandStore.operationState.status === 'success'
                      ? 'success'
                      : demandStore.operationState.status === 'error'
                        ? 'exception'
                        : undefined
                  "
                  :stroke-width="10"
                  striped
                  striped-flow
                />
                <small>
                  {{
                    demandStore.operationState.status === 'running'
                      ? '系统正在基于有效分段整理当前需求脉络，请稍候。'
                      : demandStore.operationState.status === 'error'
                        ? '本次生成未成功完成，你可以稍后重试。'
                        : '本次结果已经准备好了，可以继续查看会中提示，或进入完整报告页。'
                  }}
                </small>
              </div>
              <div v-if="demandStore.currentTask" class="task-card">
                <strong>{{ demandStore.currentTask.current_step_label || demandStore.currentTask.task_type }}</strong>
                <p>状态：{{ demandStore.currentTask.status }} · 进度：{{ demandStore.currentTask.progress }}%</p>
                <el-button text @click="demandStore.refreshCurrentTask()">刷新任务状态</el-button>
              </div>
            </section>

            <section class="customer-card panel-card">
              <div class="customer-card__head">
                <div>
                  <h3>当前主题</h3>
                  <p>先看这次沟通现在聊到哪。</p>
                </div>
              </div>
              <div v-if="!currentTopics.length" class="customer-card__empty">
                还没有主题整理结果。可以先点击“生成阶段整理”。
              </div>
              <ul v-else class="insight-list">
                <li v-for="item in currentTopicsCompact" :key="item">{{ item }}</li>
              </ul>
            </section>

            <section class="customer-card panel-card customer-card--cards">
              <article
                v-for="card in quickInsightCards"
                :key="card.title"
                class="insight-card"
                :class="`is-${card.tone}`"
              >
                <div class="insight-card__head">
                  <div class="insight-card__title">
                    <span class="insight-card__icon">
                      <el-icon><component :is="card.icon" /></el-icon>
                    </span>
                    <div>
                      <strong>{{ card.title }}</strong>
                      <p>{{ card.description }}</p>
                    </div>
                  </div>
                  <el-tag size="small" effect="light" :type="card.tone === 'danger' ? 'danger' : card.tone === 'warning' ? 'warning' : card.tone === 'success' ? 'success' : 'primary'">
                    {{ card.items.length }} 条
                  </el-tag>
                </div>
                <ul v-if="card.items.length" class="insight-list">
                  <li v-for="item in card.items" :key="item">{{ item }}</li>
                </ul>
                <div v-else class="customer-card__empty">当前还没有相关提示。</div>
                <div class="insight-card__action">
                  <el-icon><Right /></el-icon>
                  <span>{{ card.actionLabel }}</span>
                </div>
              </article>
            </section>

            <section class="customer-card panel-card">
              <div class="customer-card__head">
                <div>
                  <h3>语义复核提醒</h3>
                  <p>这些内容可能跑题，现场需要判断。</p>
                </div>
              </div>
              <div v-if="!semanticWarningsCompact.length" class="customer-card__empty">
                当前没有需要特别提醒的语义复核项。
              </div>
              <ul v-else class="insight-list insight-list--warning">
                <li v-for="item in semanticWarningsCompact" :key="item">
                  <el-icon><Warning /></el-icon>
                  <span>{{ item }}</span>
                </li>
              </ul>
            </section>

            <section class="customer-card panel-card">
              <div class="customer-card__head">
                <div>
                  <h3>会后报告</h3>
                  <p>完整报告单独查看，不占会中空间。</p>
                </div>
              </div>
              <div v-if="!demandStore.currentReport" class="customer-card__empty">
                还没有正式需求分析报告。你可以在会后点击“会后生成正式报告”。
              </div>
              <div v-else class="report-preview-card">
                <div class="report-preview-card__head">
                  <div>
                    <strong>{{ demandStore.currentReport.report_title }}</strong>
                    <p>{{ formatDateTime(demandStore.currentReport.updated_at) }}</p>
                  </div>
                  <el-tag type="success" effect="light">已生成</el-tag>
                </div>
                <div class="report-preview-card__actions">
                  <el-button type="primary" @click="openReportPage">打开完整报告页</el-button>
                  <el-button plain :loading="demandStore.exporting" @click="handleExportReport">导出 Markdown</el-button>
                </div>
              </div>
            </section>

            <section v-if="demandStore.latestStageSummary" class="customer-card panel-card">
              <div class="customer-card__head">
                <div>
                  <h3>阶段整理原文</h3>
                  <p>需要完整核对时，可以展开查看当前阶段整理的全文。</p>
                </div>
              </div>
              <div class="summary-version">最新版本：V{{ demandStore.latestStageSummary.summary_version || 0 }}</div>
              <div class="markdown-view" v-html="renderMarkdown(demandStore.latestStageSummary.summary_markdown || '')"></div>
            </section>
          </div>
        </section>
      </template>
    </main>

    <el-dialog v-model="createDialogVisible" title="新建客户沟通会话" width="560px">
      <div class="create-form">
        <el-input v-model="createForm.customer_name" placeholder="客户名称" />
        <el-input v-model="createForm.session_title" placeholder="会话标题" />
        <el-input v-model="createForm.industry" placeholder="行业" />
        <el-input v-model="createForm.region" placeholder="区域" />
        <el-input v-model="createForm.topic" placeholder="主题" />
        <el-input v-model="createForm.customer_type" placeholder="客户类型" />
        <el-switch
          v-model="createForm.knowledge_enabled"
          active-text="允许分析时参考知识库"
          inactive-text="仅根据当前沟通内容分析"
        />
        <el-input v-model="createForm.remarks" type="textarea" :rows="3" placeholder="备注（可选）" />
      </div>
      <template #footer>
        <el-button @click="createDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="demandStore.actionLoading" :disabled="createDisabled" @click="handleCreateSession">
          创建会话
        </el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="reviewDialogVisible" title="人工复核分段" width="640px">
      <div class="review-form">
        <el-alert
          :title="reviewForm.decision === 'accept' ? '确认将这条分段保留并纳入后续整理与分析。' : '确认将这条分段丢弃，不纳入后续整理与分析。'"
          :type="reviewForm.decision === 'accept' ? 'success' : 'warning'"
          :closable="false"
          show-icon
        />
        <el-input
          v-if="reviewForm.decision === 'accept'"
          v-model="reviewForm.editedText"
          type="textarea"
          :rows="8"
          placeholder="如有需要，可手动修正最终保留文本。"
        />
        <el-input
          v-model="reviewForm.note"
          type="textarea"
          :rows="3"
          placeholder="可选：填写人工复核备注。"
        />
      </div>
      <template #footer>
        <el-button @click="reviewDialogVisible = false">取消</el-button>
        <el-button :loading="demandStore.reviewingSegment" :type="reviewForm.decision === 'accept' ? 'success' : 'danger'" @click="submitReview">
          确认
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.customer-demand-shell {
  display: grid;
  grid-template-columns: 320px minmax(0, 1fr);
  min-height: 100vh;
  transition: grid-template-columns 0.22s ease;
}

.customer-demand-shell.is-sidebar-collapsed {
  grid-template-columns: 88px minmax(0, 1fr);
}

.customer-demand-sidebar {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 20px 16px;
  background: rgba(255, 255, 255, 0.62);
  backdrop-filter: blur(20px);
  border-right: 1px solid rgba(24, 50, 71, 0.08);
  min-width: 0;
}

.customer-demand-sidebar__top {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.customer-demand-sidebar__toolbar {
  display: flex;
  align-items: center;
  gap: 10px;
}

.customer-demand-sidebar__account,
.customer-demand-sidebar__list,
.customer-demand-sidebar__mini-list,
.customer-demand-header,
.customer-card {
  padding: 18px 20px;
}

.customer-demand-sidebar__account {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.customer-demand-sidebar__account strong {
  display: block;
  font-size: 14px;
}

.customer-demand-sidebar__account p,
.customer-demand-sidebar__hero p,
.customer-card__head p,
.customer-demand-header p,
.report-preview-card__head p,
.insight-card__head p {
  margin: 6px 0 0;
  color: var(--muted);
  line-height: 1.6;
}

.customer-demand-sidebar__hero h1,
.customer-demand-header h2 {
  margin: 8px 0 0;
  line-height: 1.2;
}

.customer-demand-sidebar__list,
.customer-demand-sidebar__mini-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  overflow: auto;
}

.customer-demand-sidebar__mini-list {
  align-items: center;
  padding: 14px 10px;
}

.customer-demand-sidebar__mini-empty,
.customer-demand-sidebar__empty,
.customer-card__empty {
  color: var(--muted);
  line-height: 1.7;
}

.customer-demand-sidebar__mini-item {
  width: 44px;
  height: 44px;
  border: 1px solid transparent;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.8);
  color: var(--text);
  font-weight: 700;
  cursor: pointer;
  transition: 0.18s ease;
}

.customer-demand-sidebar__mini-item:hover,
.customer-demand-sidebar__mini-item.is-active {
  border-color: rgba(15, 93, 140, 0.18);
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(237, 247, 255, 0.96));
  box-shadow: 0 12px 22px rgba(15, 38, 56, 0.08);
}

.customer-demand-sidebar__list-head,
.customer-demand-sidebar__item-top,
.customer-demand-header,
.customer-card__head,
.segment-item__head,
.task-card,
.report-preview-card__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.customer-demand-sidebar__item {
  width: 100%;
  border: 1px solid transparent;
  border-radius: 18px;
  padding: 14px;
  text-align: left;
  background: transparent;
  cursor: pointer;
  transition: 0.18s ease;
}

.customer-demand-sidebar__item:hover,
.customer-demand-sidebar__item.is-active {
  background: rgba(255, 255, 255, 0.9);
  border-color: rgba(15, 93, 140, 0.16);
  box-shadow: 0 12px 22px rgba(15, 38, 56, 0.08);
}

.customer-demand-sidebar__item strong,
.customer-demand-header h2 {
  font-size: 20px;
}

.customer-demand-sidebar__item p,
.customer-demand-sidebar__item small {
  display: block;
  margin: 8px 0 0;
  color: var(--muted);
  line-height: 1.55;
}

.customer-demand-main {
  display: flex;
  flex-direction: column;
  gap: 18px;
  padding: 22px;
  min-width: 0;
}

.customer-demand-header {
  align-items: center;
}

.customer-demand-header__meta {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.customer-demand-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.25fr) minmax(360px, 0.9fr);
  gap: 18px;
}

.customer-demand-column {
  display: flex;
  flex-direction: column;
  gap: 18px;
  min-width: 0;
}

.customer-card__head h3 {
  margin: 0;
}

.customer-card__form {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  margin-top: 16px;
}

.customer-card__form :deep(.el-textarea),
.customer-card__form :deep(.el-switch) {
  grid-column: 1 / -1;
}

.customer-card__actions,
.customer-card__manual-bar,
.customer-card__manual-actions,
.insight-actions,
.report-preview-card__actions {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.customer-card__manual {
  display: flex;
  flex-direction: column;
  gap: 14px;
  margin-top: 18px;
}

.customer-card__file-input {
  display: none;
}

.customer-card--segments {
  min-height: 420px;
}

.segment-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-top: 16px;
  max-height: 760px;
  overflow: auto;
}

.segment-item {
  border-radius: 18px;
  border: 1px solid rgba(24, 50, 71, 0.08);
  background: rgba(255, 255, 255, 0.72);
  padding: 14px 16px;
}

.segment-item p {
  margin: 10px 0;
  line-height: 1.75;
  white-space: pre-wrap;
}

.segment-item__meta {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  align-items: flex-start;
  justify-content: space-between;
}

.segment-item__head-main,
.segment-item__meta-text {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-width: 0;
}

.segment-item__badges,
.segment-item__review-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.segment-item__reasoning {
  color: #305f86;
  font-size: 13px;
}

.segment-item__issues {
  color: var(--warning);
  font-size: 12px;
  line-height: 1.7;
}

.task-card {
  margin-top: 16px;
  padding: 14px 16px;
  border-radius: 16px;
  background: rgba(15, 93, 140, 0.06);
}

.task-card p {
  margin: 6px 0 0;
  color: var(--muted);
}

.operation-status-card {
  margin-top: 14px;
  padding: 16px 18px;
  border-radius: 18px;
  border: 1px solid rgba(15, 93, 140, 0.12);
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.96), rgba(243, 250, 255, 0.94));
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.operation-status-card.is-success {
  border-color: rgba(54, 179, 126, 0.18);
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.96), rgba(242, 255, 248, 0.94));
}

.operation-status-card.is-error {
  border-color: rgba(207, 88, 76, 0.18);
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.96), rgba(255, 245, 244, 0.94));
}

.operation-status-card__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.operation-status-card__head p,
.operation-status-card small {
  margin: 6px 0 0;
  color: var(--muted);
  line-height: 1.6;
}

.insight-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin: 0;
  padding-left: 18px;
  line-height: 1.7;
}

.insight-list--warning {
  padding-left: 0;
  list-style: none;
}

.insight-list--warning li {
  display: flex;
  align-items: flex-start;
  gap: 8px;
}

.customer-card--cards {
  gap: 14px;
}

.insight-card {
  border-radius: 18px;
  padding: 16px;
  border: 1px solid rgba(24, 50, 71, 0.08);
  background: rgba(255, 255, 255, 0.75);
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.insight-card.is-success {
  border-color: rgba(54, 179, 126, 0.16);
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.96), rgba(243, 255, 248, 0.92));
}

.insight-card.is-warning {
  border-color: rgba(240, 173, 78, 0.18);
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.96), rgba(255, 250, 240, 0.94));
}

.insight-card.is-primary {
  border-color: rgba(15, 93, 140, 0.14);
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.96), rgba(242, 249, 255, 0.94));
}

.insight-card.is-danger {
  border-color: rgba(207, 88, 76, 0.16);
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.96), rgba(255, 245, 244, 0.94));
}

.insight-card__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.insight-card__title {
  display: flex;
  gap: 12px;
  align-items: flex-start;
}

.insight-card__title strong {
  display: block;
  font-size: 15px;
}

.insight-card__icon {
  width: 34px;
  height: 34px;
  border-radius: 12px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: rgba(15, 93, 140, 0.1);
  color: var(--accent);
  flex: 0 0 auto;
}

.insight-card.is-success .insight-card__icon {
  background: rgba(54, 179, 126, 0.12);
  color: #2b9b67;
}

.insight-card.is-warning .insight-card__icon {
  background: rgba(240, 173, 78, 0.14);
  color: #d08a16;
}

.insight-card.is-danger .insight-card__icon {
  background: rgba(207, 88, 76, 0.12);
  color: #c54b3f;
}

.insight-card__action {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  align-self: flex-start;
  padding: 8px 12px;
  border-radius: 999px;
  background: rgba(15, 93, 140, 0.08);
  color: var(--accent);
  font-size: 12px;
  font-weight: 600;
}

.insight-card.is-success .insight-card__action {
  background: rgba(54, 179, 126, 0.12);
  color: #2b9b67;
}

.insight-card.is-warning .insight-card__action {
  background: rgba(240, 173, 78, 0.14);
  color: #d08a16;
}

.insight-card.is-danger .insight-card__action {
  background: rgba(207, 88, 76, 0.12);
  color: #c54b3f;
}

.insight-list li {
  position: relative;
  padding-left: 2px;
}

.report-preview-card {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.report-preview-card__head strong {
  display: block;
  font-size: 16px;
}

.summary-version {
  margin-bottom: 10px;
  color: var(--accent);
  font-weight: 700;
}

.markdown-view {
  line-height: 1.8;
  color: var(--text);
}

.markdown-view :deep(h1),
.markdown-view :deep(h2),
.markdown-view :deep(h3),
.markdown-view :deep(h4) {
  margin-top: 0.8em;
  margin-bottom: 0.35em;
}

.markdown-view :deep(p) {
  margin: 0.55em 0;
}

.markdown-view :deep(ul),
.markdown-view :deep(ol) {
  padding-left: 22px;
}

.create-form {
  display: grid;
  gap: 12px;
}

.review-form {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

@media (max-width: 1320px) {
  .customer-demand-grid {
    grid-template-columns: minmax(0, 1fr);
  }
}

@media (max-width: 960px) {
  .customer-demand-shell,
  .customer-demand-shell.is-sidebar-collapsed {
    grid-template-columns: minmax(0, 1fr);
  }

  .customer-demand-sidebar {
    border-right: none;
    border-bottom: 1px solid rgba(24, 50, 71, 0.08);
  }

  .customer-demand-main {
    padding: 16px;
  }

  .customer-demand-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .customer-card__form {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
