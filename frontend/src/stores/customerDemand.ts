import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { ElMessage } from 'element-plus'

import {
  createCustomerDemandManualSegment,
  createCustomerDemandSession,
  exportCustomerDemandReport,
  fetchCustomerDemandReport,
  reviewCustomerDemandSegment,
  fetchCustomerDemandSegments,
  fetchCustomerDemandSessionDetail,
  fetchCustomerDemandSessions,
  fetchCustomerDemandStageSummaries,
  fetchCustomerDemandTask,
  pauseCustomerDemandSession,
  startCustomerDemandSession,
  stopCustomerDemandSession,
  triggerCustomerDemandAnalyze,
  triggerCustomerDemandStageSummary,
  updateCustomerDemandSession,
  uploadCustomerDemandAudioChunk,
} from '@/api/customerDemand'
import type {
  CustomerDemandCreateSessionPayload,
  CustomerDemandReportItem,
  CustomerDemandReviewSegmentPayload,
  CustomerDemandSegmentItem,
  CustomerDemandSessionItem,
  CustomerDemandStageSummaryItem,
  CustomerDemandTaskItem,
  CustomerDemandUpdateSessionPayload,
} from '@/types/customerDemand'

interface CustomerDemandOperationState {
  visible: boolean
  kind: 'stage_summary' | 'final_analysis' | ''
  title: string
  message: string
  progress: number
  status: 'running' | 'success' | 'error'
}

const DEFAULT_SESSION_FORM: CustomerDemandCreateSessionPayload = {
  customer_name: '',
  session_title: '',
  industry: '',
  region: '',
  topic: '',
  customer_type: '',
  knowledge_enabled: false,
  knowledge_scope: {},
  remarks: '',
}

export const useCustomerDemandStore = defineStore('customerDemand', () => {
  const sessions = ref<CustomerDemandSessionItem[]>([])
  const currentSessionId = ref('')
  const segments = ref<CustomerDemandSegmentItem[]>([])
  const stageSummaries = ref<CustomerDemandStageSummaryItem[]>([])
  const currentReport = ref<CustomerDemandReportItem | null>(null)
  const currentTask = ref<CustomerDemandTaskItem | null>(null)
  const loadingSessions = ref(false)
  const loadingDetail = ref(false)
  const savingProfile = ref(false)
  const actionLoading = ref(false)
  const uploadingAudio = ref(false)
  const exporting = ref(false)
  const reviewingSegment = ref(false)
  const manualInput = ref('')
  const speakerLabel = ref('客户')
  const draftForm = ref<CustomerDemandCreateSessionPayload>({ ...DEFAULT_SESSION_FORM })
  const operationState = ref<CustomerDemandOperationState>({
    visible: false,
    kind: '',
    title: '',
    message: '',
    progress: 0,
    status: 'running',
  })
  let operationTimer: number | null = null

  const currentSession = computed(() =>
    sessions.value.find((item) => item.id === currentSessionId.value) ?? null,
  )

  const sortedSegments = computed(() =>
    [...segments.value].sort((a, b) => {
      if (a.sequence_no !== b.sequence_no) return a.sequence_no - b.sequence_no
      return new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
    }),
  )

  const latestStageSummary = computed(() => stageSummaries.value[0] || null)

  function clearOperationTimer() {
    if (operationTimer !== null) {
      window.clearInterval(operationTimer)
      operationTimer = null
    }
  }

  function hideOperationLater(delay = 3000) {
    window.setTimeout(() => {
      operationState.value.visible = false
    }, delay)
  }

  function startOperation(
    kind: 'stage_summary' | 'final_analysis',
    config: {
      title: string
      initialMessage: string
    },
  ) {
    clearOperationTimer()
    operationState.value = {
      visible: true,
      kind,
      title: config.title,
      message: config.initialMessage || '正在处理中',
      progress: 5,
      status: 'running',
    }
  }

  function completeOperation(message: string) {
    clearOperationTimer()
    operationState.value = {
      ...operationState.value,
      visible: true,
      status: 'success',
      progress: 100,
      message,
    }
    hideOperationLater()
  }

  function failOperation(message: string) {
    clearOperationTimer()
    operationState.value = {
      ...operationState.value,
      visible: true,
      status: 'error',
      message,
    }
  }

  function syncOperationWithTask(task: CustomerDemandTaskItem) {
    const title = task.task_type === 'final_analysis' ? '需求分析报告生成中' : '阶段整理生成中'
    operationState.value = {
      visible: true,
      kind: task.task_type === 'final_analysis' ? 'final_analysis' : 'stage_summary',
      title,
      message: task.current_step_label || '系统正在处理中',
      progress: task.progress || 5,
      status: task.status === 'failed' ? 'error' : task.status === 'completed' ? 'success' : 'running',
    }
  }

  async function waitForTask(taskId: string, taskType: 'stage_summary' | 'final_analysis') {
    const maxRounds = 160
    for (let round = 0; round < maxRounds; round += 1) {
      const task = await fetchCustomerDemandTask(taskId)
      currentTask.value = task
      syncOperationWithTask(task)

      if (task.status === 'completed') {
        if (currentSession.value) {
          await loadSessionDetail(currentSession.value.id)
        }
        if (taskType === 'stage_summary') {
          completeOperation('阶段整理已生成，可以继续查看提炼结果。')
        } else {
          completeOperation('需求分析报告已生成，可以开始查看和导出。')
        }
        return task
      }

      if (task.status === 'failed' || task.status === 'cancelled') {
        const message = task.error_message || (taskType === 'stage_summary' ? '阶段整理生成失败，请稍后重试。' : '需求分析报告生成失败，请稍后重试。')
        failOperation(message)
        throw new Error(message)
      }

      await new Promise((resolve) => window.setTimeout(resolve, 1500))
    }

    failOperation(taskType === 'stage_summary' ? '阶段整理生成超时，请稍后重试。' : '需求分析报告生成超时，请稍后重试。')
    throw new Error('任务轮询超时')
  }

  function syncCurrentSession(updated: CustomerDemandSessionItem) {
    const index = sessions.value.findIndex((item) => item.id === updated.id)
    if (index >= 0) {
      sessions.value.splice(index, 1, updated)
    } else {
      sessions.value.unshift(updated)
    }
  }

  function applySessionToDraft(session: CustomerDemandSessionItem | null) {
    draftForm.value = session
      ? {
          customer_name: session.customer_name,
          session_title: session.session_title,
          industry: session.industry || '',
          region: session.region || '',
          topic: session.topic || '',
          customer_type: session.customer_type || '',
          knowledge_enabled: session.knowledge_enabled,
          knowledge_scope: session.knowledge_scope || {},
          remarks: session.remarks || '',
        }
      : { ...DEFAULT_SESSION_FORM }
  }

  async function loadSessions() {
    loadingSessions.value = true
    try {
      const data = await fetchCustomerDemandSessions()
      sessions.value = data.items
      if (!currentSessionId.value && data.items.length) {
        currentSessionId.value = data.items[0].id
      }
    } finally {
      loadingSessions.value = false
    }
  }

  async function loadSessionDetail(sessionId: string) {
    loadingDetail.value = true
    try {
      const [detail, segmentData, summaryData, reportData] = await Promise.all([
        fetchCustomerDemandSessionDetail(sessionId),
        fetchCustomerDemandSegments(sessionId),
        fetchCustomerDemandStageSummaries(sessionId),
        fetchCustomerDemandReport(sessionId),
      ])
      currentSessionId.value = sessionId
      syncCurrentSession(detail)
      applySessionToDraft(detail)
      segments.value = segmentData.items
      stageSummaries.value = summaryData.items
      currentReport.value = reportData
      currentTask.value = null
    } finally {
      loadingDetail.value = false
    }
  }

  async function selectSession(sessionId: string) {
    if (!sessionId) return
    await loadSessionDetail(sessionId)
  }

  async function createSession(payload: CustomerDemandCreateSessionPayload) {
    actionLoading.value = true
    try {
      const session = await createCustomerDemandSession(payload)
      sessions.value.unshift(session)
      await loadSessionDetail(session.id)
      ElMessage.success('客户沟通会话已创建')
    } finally {
      actionLoading.value = false
    }
  }

  async function saveCurrentSessionProfile() {
    if (!currentSession.value) return
    savingProfile.value = true
    try {
      const updated = await updateCustomerDemandSession(currentSession.value.id, draftForm.value as CustomerDemandUpdateSessionPayload)
      syncCurrentSession(updated)
      applySessionToDraft(updated)
      ElMessage.success('会话信息已保存')
    } finally {
      savingProfile.value = false
    }
  }

  async function startRecording() {
    if (!currentSession.value) return
    actionLoading.value = true
    try {
      await startCustomerDemandSession(currentSession.value.id)
      const detail = await fetchCustomerDemandSessionDetail(currentSession.value.id)
      syncCurrentSession(detail)
      applySessionToDraft(detail)
      ElMessage.success('已开始记录沟通内容')
    } finally {
      actionLoading.value = false
    }
  }

  async function pauseRecording() {
    if (!currentSession.value) return
    actionLoading.value = true
    try {
      await pauseCustomerDemandSession(currentSession.value.id)
      const detail = await fetchCustomerDemandSessionDetail(currentSession.value.id)
      syncCurrentSession(detail)
      applySessionToDraft(detail)
      ElMessage.success('已暂停记录')
    } finally {
      actionLoading.value = false
    }
  }

  async function stopRecording() {
    if (!currentSession.value) return
    actionLoading.value = true
    try {
      await stopCustomerDemandSession(currentSession.value.id)
      const detail = await fetchCustomerDemandSessionDetail(currentSession.value.id)
      syncCurrentSession(detail)
      applySessionToDraft(detail)
      ElMessage.success('已结束本轮沟通记录')
    } finally {
      actionLoading.value = false
    }
  }

  async function appendManualSegment() {
    if (!currentSession.value || !manualInput.value.trim()) return
    actionLoading.value = true
    try {
      await createCustomerDemandManualSegment(currentSession.value.id, {
        sequence_no: sortedSegments.value.length + 1,
        speaker_label: speakerLabel.value,
        raw_text: manualInput.value.trim(),
        normalized_text: manualInput.value.trim(),
        final_text: manualInput.value.trim(),
        asr_provider: 'manual',
        segment_status: 'normalized',
        review_flag: false,
        issues_json: [],
      })
      manualInput.value = ''
      await loadSessionDetail(currentSession.value.id)
      ElMessage.success('已补录一条沟通分段')
    } finally {
      actionLoading.value = false
    }
  }

  async function uploadAudio(file: File) {
    if (!currentSession.value) return
    uploadingAudio.value = true
    try {
      await uploadCustomerDemandAudioChunk(currentSession.value.id, {
        file,
        chunkIndex: sortedSegments.value.length + 1,
        provider: 'qwen',
        language: 'zh',
        audioFs: 16000,
      })
      await loadSessionDetail(currentSession.value.id)
      ElMessage.success('音频分片已上传并完成识别')
    } finally {
      uploadingAudio.value = false
    }
  }

  async function reviewSegment(segmentId: string, payload: CustomerDemandReviewSegmentPayload) {
    if (!currentSession.value) return
    reviewingSegment.value = true
    try {
      await reviewCustomerDemandSegment(currentSession.value.id, segmentId, payload)
      await loadSessionDetail(currentSession.value.id)
      ElMessage.success(payload.decision === 'accept' ? '分段已保留并通过复核' : '分段已标记为丢弃')
    } finally {
      reviewingSegment.value = false
    }
  }

  async function triggerStageSummaryNow() {
    if (!currentSession.value) return
    actionLoading.value = true
    startOperation('stage_summary', {
      title: '阶段整理生成中',
      initialMessage: '正在提交阶段整理任务',
    })
    try {
      const data = await triggerCustomerDemandStageSummary(currentSession.value.id, 'manual')
      currentTask.value = data.task
      syncOperationWithTask(data.task)
      await waitForTask(data.task.id, 'stage_summary')
      ElMessage.success('阶段整理已生成')
    } catch (error) {
      if (!(error instanceof Error)) {
        failOperation('阶段整理生成失败，请稍后重试。')
      }
      throw error
    } finally {
      actionLoading.value = false
    }
  }

  async function triggerFinalAnalysisNow() {
    if (!currentSession.value) return
    actionLoading.value = true
    startOperation('final_analysis', {
      title: '需求分析报告生成中',
      initialMessage: '正在提交需求分析任务',
    })
    try {
      const data = await triggerCustomerDemandAnalyze(currentSession.value.id, draftForm.value.knowledge_enabled ?? false)
      currentTask.value = data.task
      syncOperationWithTask(data.task)
      await waitForTask(data.task.id, 'final_analysis')
      ElMessage.success('需求分析报告已生成')
    } catch (error) {
      if (!(error instanceof Error)) {
        failOperation('需求分析报告生成失败，请稍后重试。')
      }
      throw error
    } finally {
      actionLoading.value = false
    }
  }

  async function refreshCurrentTask() {
    if (!currentTask.value) return
    currentTask.value = await fetchCustomerDemandTask(currentTask.value.id)
  }

  async function exportCurrentReport() {
    if (!currentSession.value) return
    exporting.value = true
    try {
      const data = await exportCustomerDemandReport(currentSession.value.id, 'markdown')
      await navigator.clipboard.writeText(data.content)
      ElMessage.success('报告 Markdown 已复制到剪贴板')
    } finally {
      exporting.value = false
    }
  }

  return {
    sessions,
    currentSessionId,
    currentSession,
    segments,
    sortedSegments,
    stageSummaries,
    latestStageSummary,
    currentReport,
    currentTask,
    operationState,
    loadingSessions,
    loadingDetail,
    savingProfile,
    actionLoading,
    uploadingAudio,
    reviewingSegment,
    exporting,
    manualInput,
    speakerLabel,
    draftForm,
    loadSessions,
    selectSession,
    createSession,
    saveCurrentSessionProfile,
    startRecording,
    pauseRecording,
    stopRecording,
    appendManualSegment,
    uploadAudio,
    reviewSegment,
    triggerStageSummaryNow,
    triggerFinalAnalysisNow,
    refreshCurrentTask,
    exportCurrentReport,
    applySessionToDraft,
  }
})
