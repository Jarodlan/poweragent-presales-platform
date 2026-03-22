<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import {
  ArrowLeft,
  ChatDotRound,
  Connection,
  Document,
  FolderOpened,
  Microphone,
  Refresh,
  Search,
  UploadFilled,
  VideoPause,
  VideoPlay,
} from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useRouter } from 'vue-router'

import EmptyState from '@/components/common/EmptyState.vue'
import { useAuthStore } from '@/stores/auth'
import { useCustomerDemandStore } from '@/stores/customerDemand'
import { renderMarkdown } from '@/utils/markdown'
import { formatDateTime, formatRelativeTime } from '@/utils/time'

const router = useRouter()
const authStore = useAuthStore()
const demandStore = useCustomerDemandStore()
const keyword = ref('')
const createDialogVisible = ref(false)
const uploadInputRef = ref<HTMLInputElement | null>(null)
const reviewDialogVisible = ref(false)
const reviewForm = reactive({
  segmentId: '',
  decision: 'accept' as 'accept' | 'discard',
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
    [item.customer_name, item.session_title, item.topic, item.industry, item.region].join(' ').toLowerCase().includes(normalized),
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

function openReviewDialog(segment: any, decision: 'accept' | 'discard') {
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

onMounted(async () => {
  await demandStore.loadSessions()
  if (demandStore.currentSessionId) {
    await demandStore.selectSession(demandStore.currentSessionId)
  }
})
</script>

<template>
  <div class="customer-demand-shell">
    <aside class="customer-demand-sidebar">
      <div class="customer-demand-sidebar__top">
        <div class="customer-demand-sidebar__account panel-card">
          <div>
            <strong>{{ authStore.displayName || '未登录用户' }}</strong>
            <p>{{ authStore.user?.department?.name || '未设置部门' }}</p>
          </div>
          <el-button text @click="router.push('/')">
            <el-icon><ArrowLeft /></el-icon>
            返回方案工作台
          </el-button>
        </div>

        <div class="customer-demand-sidebar__hero">
          <p class="section-title">Demand Agent</p>
          <h1>客户需求分析工作台</h1>
          <p>把现场口语化、碎片化的客户沟通内容，整理成结构化需求理解和后续挖掘建议。</p>
        </div>

        <el-button type="primary" round @click="createDialogVisible = true">
          <el-icon><ChatDotRound /></el-icon>
          新建沟通会话
        </el-button>
      </div>

      <el-input v-model="keyword" placeholder="搜索客户、主题或区域" clearable>
        <template #prefix>
          <el-icon><Search /></el-icon>
        </template>
      </el-input>

      <div class="customer-demand-sidebar__list panel-card">
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
    </aside>

    <main class="customer-demand-main">
      <header class="customer-demand-header panel-card">
        <div>
          <p class="section-title">Customer Demand</p>
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
          <el-tag effect="plain" type="success">{{ demandStore.stageSummaries.length }} 版整理</el-tag>
        </div>
      </header>

      <div v-if="!demandStore.currentSession" class="customer-demand-empty">
        <EmptyState
          title="客户需求分析智能体已就绪"
          description="先创建一条客户沟通会话，然后就可以开始记录现场交流、上传语音分片、生成阶段整理和需求分析报告。"
        />
      </div>

      <template v-else>
        <section class="customer-demand-grid">
          <div class="customer-demand-column">
            <section class="customer-card panel-card">
              <div class="customer-card__head">
                <div>
                  <h3>会话信息</h3>
                  <p>先把客户、主题和知识库开关补齐，后续报告会直接沿用这里的信息。</p>
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

          <div class="customer-demand-column customer-demand-column--insights">
            <section class="customer-card panel-card">
              <div class="customer-card__head">
                <div>
                  <h3>分析动作</h3>
                  <p>阶段整理适合现场中途快速复盘；最终分析会形成正式需求报告和后续挖掘建议。</p>
                </div>
              </div>
              <div class="insight-actions">
                <el-button :loading="demandStore.actionLoading" type="primary" @click="demandStore.triggerStageSummaryNow()">
                  <el-icon><Connection /></el-icon>
                  生成阶段整理
                </el-button>
                <el-button :loading="demandStore.actionLoading" type="success" @click="demandStore.triggerFinalAnalysisNow()">
                  <el-icon><Document /></el-icon>
                  开始需求分析
                </el-button>
                <el-button :loading="demandStore.exporting" plain @click="handleExportReport">
                  <el-icon><FolderOpened /></el-icon>
                  导出报告 Markdown
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
                      ? '系统正在处理，请稍候。生成结构化阶段整理或正式需求分析报告通常会持续数秒到几十秒。'
                      : demandStore.operationState.status === 'error'
                        ? '本次生成未成功完成，你可以稍后重试。'
                        : '本次结果已经准备好了，现在可以继续阅读、复核或导出报告。'
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
                  <h3>阶段整理</h3>
                  <p>自动抽取本阶段已明确的需求点、约束和待确认问题。</p>
                </div>
              </div>
              <div v-if="!demandStore.stageSummaries.length" class="customer-card__empty">
                还没有阶段整理记录。
              </div>
              <div v-else class="markdown-view">
                <div class="summary-version">
                  最新版本：V{{ demandStore.latestStageSummary?.summary_version || 0 }}
                </div>
                <div v-html="renderMarkdown(demandStore.latestStageSummary?.summary_markdown || '')"></div>
              </div>
            </section>

            <section class="customer-card panel-card">
              <div class="customer-card__head">
                <div>
                  <h3>最终需求分析报告</h3>
                  <p>形成需求理解、方案方向和后续挖掘建议，方便内部复盘与再次沟通。</p>
                </div>
              </div>
              <div v-if="!demandStore.currentReport" class="customer-card__empty">
                还没有生成正式分析报告。
              </div>
              <div v-else class="report-stack">
                <div class="report-title-block">
                  <strong>{{ demandStore.currentReport.report_title }}</strong>
                  <small>{{ formatDateTime(demandStore.currentReport.updated_at) }}</small>
                </div>
                <div class="markdown-view" v-html="renderMarkdown(demandStore.currentReport.report_markdown || '')"></div>
                <div class="report-subsection">
                  <h4>需求挖掘方向建议</h4>
                  <div class="markdown-view" v-html="renderMarkdown(demandStore.currentReport.digging_suggestions_markdown || '暂无建议')"></div>
                </div>
                <div class="report-subsection">
                  <h4>推荐追问问题</h4>
                  <div class="markdown-view" v-html="renderMarkdown(demandStore.currentReport.recommended_questions_markdown || '暂无推荐问题')"></div>
                </div>
              </div>
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
}

.customer-demand-sidebar {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 22px 18px;
  background: rgba(255, 255, 255, 0.62);
  backdrop-filter: blur(20px);
  border-right: 1px solid rgba(24, 50, 71, 0.08);
}

.customer-demand-sidebar__top {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.customer-demand-sidebar__account,
.customer-demand-sidebar__list,
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
.customer-demand-header p {
  margin: 6px 0 0;
  color: var(--muted);
  line-height: 1.6;
}

.customer-demand-sidebar__hero h1,
.customer-demand-header h2 {
  margin: 8px 0 0;
  line-height: 1.2;
}

.customer-demand-sidebar__list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  overflow: auto;
}

.customer-demand-sidebar__list-head,
.customer-demand-sidebar__item-top,
.customer-demand-header,
.customer-card__head,
.segment-item__head,
.task-card {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.customer-demand-sidebar__empty,
.customer-card__empty {
  color: var(--muted);
  line-height: 1.7;
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
  grid-template-columns: minmax(0, 1.15fr) minmax(320px, 0.85fr);
  gap: 18px;
}

.customer-demand-column {
  display: flex;
  flex-direction: column;
  gap: 18px;
  min-width: 0;
}

.customer-card__head h3,
.report-subsection h4 {
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
.report-title-block {
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

.operation-status-card__head p {
  margin: 6px 0 0;
  color: var(--muted);
  line-height: 1.6;
}

.operation-status-card small {
  color: var(--muted);
  line-height: 1.6;
}

.task-card p {
  margin: 6px 0 0;
  color: var(--muted);
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

.summary-version {
  margin-bottom: 10px;
  color: var(--accent);
  font-weight: 700;
}

.report-stack {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.report-title-block {
  justify-content: space-between;
}

.report-title-block small {
  color: var(--muted);
}

.report-subsection {
  border-top: 1px solid rgba(24, 50, 71, 0.08);
  padding-top: 14px;
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

@media (max-width: 1200px) {
  .customer-demand-grid {
    grid-template-columns: minmax(0, 1fr);
  }
}

@media (max-width: 960px) {
  .customer-demand-shell {
    grid-template-columns: minmax(0, 1fr);
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
