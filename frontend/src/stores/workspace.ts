import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { ElMessage } from 'element-plus'

import {
  createConversation,
  deleteConversation as deleteConversationRequest,
  fetchConversationList,
  fetchConversationMessages,
  sendConversationMessage,
} from '@/api/conversation'
import { cancelTask } from '@/api/task'
import { DEFAULT_PARAMS, SCENARIO_PRESET_MAP, type ComposerParams } from '@/config/solutionComposer'
import { createTaskEventSource } from '@/utils/sse'
import { groupConversationLabel } from '@/utils/time'
import type { ConversationItem, EvidenceCard, MessageItem } from '@/types/conversation'
import type { ContentStreamData, EvidenceStreamData, SendMessageResult, StatusStreamData, StreamEnvelope } from '@/types/task'

interface WorkflowStageItem {
  key: string
  label: string
  status: 'completed' | 'current' | 'failed' | 'stopped'
}

export const useWorkspaceStore = defineStore('workspace', () => {
  const conversations = ref<ConversationItem[]>([])
  const messages = ref<Record<string, MessageItem[]>>({})
  const currentConversationId = ref<string>('')
  const loadingConversations = ref(false)
  const loadingMessages = ref(false)
  const sending = ref(false)
  const currentTaskId = ref<string>('')
  const currentAssistantMessageId = ref<string>('')
  const workflowAnchorMessageId = ref<string>('')
  const currentStepLabel = ref('')
  const currentProgress = ref(0)
  const workflowStages = ref<WorkflowStageItem[]>([])
  const showWorkflowRibbon = ref(false)
  const evidenceDrawerVisible = ref(false)
  const activeEvidenceCards = ref<EvidenceCard[]>([])
  const composerText = ref('')
  const composerParams = ref<ComposerParams>({ ...DEFAULT_PARAMS })
  const importedDraftNotice = ref('')
  let eventSource: EventSource | null = null
  let ribbonHideTimer: number | null = null

  const groupedConversations = computed(() => {
    const ordered = [...conversations.value].sort((a, b) => {
      const aTime = new Date(a.last_message_at || a.updated_at).getTime()
      const bTime = new Date(b.last_message_at || b.updated_at).getTime()
      return bTime - aTime
    })
    const groups = new Map<string, ConversationItem[]>()
    for (const item of ordered) {
      const label = groupConversationLabel(item.last_message_at || item.updated_at)
      const bucket = groups.get(label) ?? []
      bucket.push(item)
      groups.set(label, bucket)
    }
    return Array.from(groups.entries()).map(([label, items]) => ({ label, items }))
  })

  const currentConversation = computed(() =>
    conversations.value.find((item) => item.conversation_id === currentConversationId.value) ?? null,
  )

  const currentMessages = computed(() => messages.value[currentConversationId.value] ?? [])

  function resetComposer() {
    composerText.value = ''
  }

  function resetWorkflowStages() {
    workflowStages.value = []
  }

  function clearWorkflowRibbonHideTimer() {
    if (ribbonHideTimer) {
      window.clearTimeout(ribbonHideTimer)
      ribbonHideTimer = null
    }
  }

  function scheduleWorkflowRibbonHide() {
    clearWorkflowRibbonHideTimer()
    ribbonHideTimer = window.setTimeout(() => {
      showWorkflowRibbon.value = false
      workflowAnchorMessageId.value = ''
      currentStepLabel.value = ''
      currentProgress.value = 0
      resetWorkflowStages()
    }, 3000)
  }

  function setCurrentWorkflowStage(stepKey: string, label: string) {
    if (!label) return
    const stages = [...workflowStages.value]
    const existingIndex = stages.findIndex((item) => item.key === stepKey)

    if (existingIndex >= 0) {
      stages.forEach((item, index) => {
        if (index !== existingIndex && item.status === 'current') {
          item.status = 'completed'
        }
      })
      stages[existingIndex].status = 'current'
      workflowStages.value = stages
      return
    }

    stages.forEach((item) => {
      if (item.status === 'current') {
        item.status = 'completed'
      }
    })
    stages.push({
      key: stepKey,
      label,
      status: 'current',
    })
    workflowStages.value = stages
  }

  function markWorkflowTerminal(status: 'completed' | 'failed' | 'stopped') {
    const stages = [...workflowStages.value]
    const currentIndex = stages.findIndex((item) => item.status === 'current')
    if (currentIndex >= 0) {
      stages[currentIndex].status = status
    }
    workflowStages.value = stages
  }

  function setComposerText(text: string) {
    composerText.value = text
  }

  function applyDefaultParams(defaults?: Record<string, string | string[]>) {
    composerParams.value = {
      scenario: (defaults?.scenario as string) || DEFAULT_PARAMS.scenario,
      grid_environment: (defaults?.grid_environment as string) || DEFAULT_PARAMS.grid_environment,
      equipment_type: (defaults?.equipment_type as string) || DEFAULT_PARAMS.equipment_type,
      resource_type: (defaults?.resource_type as string) || DEFAULT_PARAMS.resource_type,
      data_basis: (defaults?.data_basis as string[]) || DEFAULT_PARAMS.data_basis,
      target_capability: (defaults?.target_capability as string[]) || DEFAULT_PARAMS.target_capability,
      market_policy_focus: (defaults?.market_policy_focus as string[]) || DEFAULT_PARAMS.market_policy_focus,
      planning_objective: (defaults?.planning_objective as string[]) || DEFAULT_PARAMS.planning_objective,
      forecast_target: (defaults?.forecast_target as string[]) || DEFAULT_PARAMS.forecast_target,
      coordination_scope: (defaults?.coordination_scope as string) || DEFAULT_PARAMS.coordination_scope,
      lifecycle_goal: (defaults?.lifecycle_goal as string) || DEFAULT_PARAMS.lifecycle_goal,
    }
  }

  function resetComposerParams(defaults?: Record<string, string | string[]>) {
    applyDefaultParams(defaults)
  }

  function applyScenarioPreset(scenario: string) {
    const preset = SCENARIO_PRESET_MAP[scenario]
    composerParams.value = {
      ...composerParams.value,
      scenario,
      ...(preset ?? {}),
    }
  }

  function sanitizeComposerParams(raw?: Partial<ComposerParams> | Record<string, unknown>) {
    const scenario = typeof raw?.scenario === 'string' ? raw.scenario : DEFAULT_PARAMS.scenario
    const preset = SCENARIO_PRESET_MAP[scenario] ?? {}
    const pickString = (key: keyof ComposerParams) =>
      typeof raw?.[key] === 'string' ? String(raw[key]) : (preset[key] as string | undefined) ?? DEFAULT_PARAMS[key]
    const pickArray = (key: keyof ComposerParams) =>
      Array.isArray(raw?.[key])
        ? (raw?.[key] as unknown[]).map((item) => String(item)).filter(Boolean)
        : ((preset[key] as string[] | undefined) ?? DEFAULT_PARAMS[key]) as string[]

    return {
      scenario,
      grid_environment: pickString('grid_environment') as string,
      equipment_type: pickString('equipment_type') as string,
      resource_type: pickString('resource_type') as string,
      data_basis: [...pickArray('data_basis')],
      target_capability: [...pickArray('target_capability')],
      market_policy_focus: [...pickArray('market_policy_focus')],
      planning_objective: [...pickArray('planning_objective')],
      forecast_target: [...pickArray('forecast_target')],
      coordination_scope: pickString('coordination_scope') as string,
      lifecycle_goal: pickString('lifecycle_goal') as string,
    } satisfies ComposerParams
  }

  async function applyImportedDraft(payload: { query: string; params?: Partial<ComposerParams> | Record<string, unknown> }) {
    await createNewConversation()
    composerParams.value = sanitizeComposerParams(payload.params)
    composerText.value = (payload.query || '').trim()
    importedDraftNotice.value = '已从客户需求分析报告导入方案草稿，请确认内容与参数后再发送。'
  }

  function clearImportedDraftNotice() {
    importedDraftNotice.value = ''
  }

  async function loadConversationList() {
    loadingConversations.value = true
    try {
      const data = await fetchConversationList()
      conversations.value = data.items
      if (currentConversationId.value && !data.items.some((item) => item.conversation_id === currentConversationId.value)) {
        currentConversationId.value = ''
      }
      if (!currentConversationId.value && data.items[0]) {
        currentConversationId.value = data.items[0].conversation_id
      }
    } finally {
      loadingConversations.value = false
    }
  }

  async function selectConversation(conversationId: string) {
    currentConversationId.value = conversationId
    clearWorkflowRibbonHideTimer()
    resetWorkflowStages()
    showWorkflowRibbon.value = false
    workflowAnchorMessageId.value = ''
    currentStepLabel.value = ''
    currentProgress.value = 0
    if (messages.value[conversationId]) return
    loadingMessages.value = true
    try {
      const data = await fetchConversationMessages(conversationId)
      messages.value[conversationId] = data.items.map((item) => ({
        ...item,
        content: item.content || item.query_text || '',
      }))
    } finally {
      loadingMessages.value = false
    }
  }

  async function createNewConversation() {
    closeStream()
    clearWorkflowRibbonHideTimer()
    currentConversationId.value = ''
    resetComposer()
    resetWorkflowStages()
    currentStepLabel.value = ''
    currentProgress.value = 0
    currentTaskId.value = ''
    currentAssistantMessageId.value = ''
    workflowAnchorMessageId.value = ''
    showWorkflowRibbon.value = false
    sending.value = false
    evidenceDrawerVisible.value = false
    activeEvidenceCards.value = []
  }

  async function deleteConversation(conversationId: string) {
    await deleteConversationRequest(conversationId)
    conversations.value = conversations.value.filter((item) => item.conversation_id !== conversationId)
    delete messages.value[conversationId]

    if (currentConversationId.value === conversationId) {
      currentConversationId.value = conversations.value[0]?.conversation_id || ''
      if (currentConversationId.value && !messages.value[currentConversationId.value]) {
        await selectConversation(currentConversationId.value)
      }
    }
  }

  async function ensureConversationForSubmit() {
    if (currentConversationId.value) return currentConversationId.value
    const conversation = await createConversation('')
    conversations.value.unshift(conversation)
    currentConversationId.value = conversation.conversation_id
    messages.value[conversation.conversation_id] = []
    return conversation.conversation_id
  }

  function patchConversation(conversationId: string, patch: Partial<ConversationItem>) {
    const index = conversations.value.findIndex((item) => item.conversation_id === conversationId)
    if (index === -1) return
    conversations.value[index] = {
      ...conversations.value[index],
      ...patch,
    }
  }

  function patchAssistantMessage(
    conversationId: string,
    assistantMessageId: string,
    patch: Partial<MessageItem>,
  ) {
    const list = messages.value[conversationId] ?? []
    const index = list.findIndex((item) => item.message_id === assistantMessageId)
    if (index === -1) return
    list[index] = { ...list[index], ...patch }
    messages.value[conversationId] = [...list]
  }

  function ensureAssistantMessage(conversationId: string, assistantMessageId: string) {
    const list = messages.value[conversationId] ?? []
    const exists = list.some((item) => item.message_id === assistantMessageId)
    if (!exists) {
      list.push({
        message_id: assistantMessageId,
        conversation_id: conversationId,
        role: 'assistant',
        status: 'running',
        query_text: '',
        summary: '',
        content: '',
        assumptions: [],
        evidence_cards: [],
        created_at: new Date().toISOString(),
      })
      messages.value[conversationId] = [...list]
    }
  }

  function closeStream() {
    if (eventSource) {
      eventSource.close()
      eventSource = null
    }
  }

  function setAssistantTerminalState(
    conversationId: string,
    assistantMessageId: string,
    status: 'failed' | 'stopped',
    content?: string,
  ) {
    patchAssistantMessage(conversationId, assistantMessageId, {
      status,
      content:
        content ||
        (status === 'stopped' ? '本次生成已被手动停止，你可以稍后继续生成。' : '生成过程中出现异常，请重试。'),
    })
  }

  function findRetryQuery(conversationId: string, assistantMessageId?: string) {
    const list = messages.value[conversationId] ?? []
    if (!list.length) return ''
    if (assistantMessageId) {
      const targetIndex = list.findIndex((item) => item.message_id === assistantMessageId)
      if (targetIndex > 0) {
        for (let index = targetIndex - 1; index >= 0; index -= 1) {
          const item = list[index]
          if (item.role === 'user') {
            return item.content || item.query_text || ''
          }
        }
      }
    }

    const lastUser = [...list].reverse().find((item) => item.role === 'user')
    return lastUser?.content || lastUser?.query_text || ''
  }

  function bindTaskStream(payload: SendMessageResult) {
    closeStream()
    clearWorkflowRibbonHideTimer()
    const conversationId = payload.conversation_id
    const assistantMessageId = payload.assistant_message_id
    currentTaskId.value = payload.task_id
    currentAssistantMessageId.value = assistantMessageId
    workflowAnchorMessageId.value = assistantMessageId
    showWorkflowRibbon.value = true
    currentProgress.value = 0
    currentStepLabel.value = '正在启动生成流程'
    workflowStages.value = [
      {
        key: 'request_sent',
        label: '请求已发送',
        status: 'completed',
      },
      {
        key: 'workflow_started',
        label: '正在启动生成流程',
        status: 'current',
      },
    ]
    eventSource = createTaskEventSource(payload.stream_url)

    eventSource.onmessage = (event) => {
      const envelope = JSON.parse(event.data) as StreamEnvelope
      ensureAssistantMessage(conversationId, assistantMessageId)

      switch (envelope.event) {
        case 'conversation_meta': {
          const data = envelope.data as { conversation_id: string; title: string }
          patchConversation(data.conversation_id, { title: data.title || '新会话' })
          break
        }
        case 'status': {
          const data = envelope.data as StatusStreamData
          showWorkflowRibbon.value = true
          currentStepLabel.value = data.message
          currentProgress.value = data.progress
          setCurrentWorkflowStage(data.step, data.message)
          patchAssistantMessage(conversationId, assistantMessageId, { status: 'running' })
          patchConversation(conversationId, { status: 'running' })
          break
        }
        case 'summary_chunk': {
          const data = envelope.data as ContentStreamData
          patchAssistantMessage(conversationId, assistantMessageId, { summary: data.content })
          break
        }
        case 'content_chunk': {
          const data = envelope.data as ContentStreamData
          patchAssistantMessage(conversationId, assistantMessageId, {
            content: data.content,
            status: 'completed',
          })
          break
        }
        case 'evidence_cards': {
          const data = envelope.data as EvidenceStreamData
          patchAssistantMessage(conversationId, assistantMessageId, { evidence_cards: data.items })
          break
        }
        case 'completed': {
          patchAssistantMessage(conversationId, assistantMessageId, { status: 'completed' })
          patchConversation(conversationId, { status: 'idle' })
          currentProgress.value = 100
          currentStepLabel.value = '生成完成'
          markWorkflowTerminal('completed')
          sending.value = false
          currentTaskId.value = ''
          currentAssistantMessageId.value = ''
          closeStream()
          scheduleWorkflowRibbonHide()
          break
        }
        case 'error': {
          setAssistantTerminalState(conversationId, assistantMessageId, 'failed')
          patchConversation(conversationId, { status: 'failed' })
          currentStepLabel.value = '生成失败'
          markWorkflowTerminal('failed')
          sending.value = false
          currentTaskId.value = ''
          currentAssistantMessageId.value = ''
          closeStream()
          break
        }
      }
    }

    eventSource.onerror = () => {
      currentStepLabel.value = '流式连接中断'
      showWorkflowRibbon.value = true
      if (sending.value) {
        markWorkflowTerminal('failed')
        setAssistantTerminalState(
          conversationId,
          assistantMessageId,
          'failed',
          '流式连接中断，结果可能未完整返回，请重新生成。',
        )
        patchConversation(conversationId, { status: 'failed' })
      }
      sending.value = false
      currentTaskId.value = ''
      currentAssistantMessageId.value = ''
      closeStream()
    }
  }

  async function submitQuery(queryText?: string) {
    const ensuredConversationId = await ensureConversationForSubmit()
    const query = (queryText ?? composerText.value).trim()
    if (!query || !ensuredConversationId) return

    const conversationId = ensuredConversationId
    const optimisticUserMessage: MessageItem = {
      message_id: `local-user-${Date.now()}`,
      conversation_id: conversationId,
      role: 'user',
      status: 'completed',
      query_text: query,
      content: query,
      created_at: new Date().toISOString(),
    }

    const nextMessages = [...(messages.value[conversationId] ?? []), optimisticUserMessage]
    messages.value[conversationId] = nextMessages
    patchConversation(conversationId, {
      last_user_message: query,
      status: 'running',
      last_message_at: new Date().toISOString(),
      title: currentConversation.value?.title || query.slice(0, 40),
    })

    sending.value = true
    currentStepLabel.value = '正在发送请求'
    currentProgress.value = 4
    try {
      const payload = await sendConversationMessage(conversationId, {
        query,
        params: composerParams.value,
      })
      resetComposer()
      bindTaskStream(payload)
    } catch (error) {
      const list = messages.value[conversationId] ?? []
      list.push({
        message_id: `local-assistant-error-${Date.now()}`,
        conversation_id: conversationId,
        role: 'assistant',
        status: 'failed',
        query_text: '',
        summary: '',
        content: '请求发送失败，请检查服务状态后重试。',
        assumptions: [],
        evidence_cards: [],
        created_at: new Date().toISOString(),
      })
      messages.value[conversationId] = [...list]
      sending.value = false
      currentTaskId.value = ''
      currentAssistantMessageId.value = ''
      currentStepLabel.value = '发送失败'
      currentProgress.value = 0
      patchConversation(conversationId, { status: 'failed' })
      ElMessage.error(error instanceof Error ? error.message : '发送失败，请稍后重试。')
    }
  }

  async function submitCurrentMessage() {
    await submitQuery()
  }

  async function stopCurrentTask() {
    if (!currentTaskId.value) return
    const conversationId = currentConversationId.value
    const assistantMessageId = currentAssistantMessageId.value
    await cancelTask(currentTaskId.value)
    if (conversationId && assistantMessageId) {
      setAssistantTerminalState(conversationId, assistantMessageId, 'stopped')
      patchConversation(conversationId, { status: 'idle' })
    }
    currentStepLabel.value = '已停止生成'
    markWorkflowTerminal('stopped')
    sending.value = false
    currentTaskId.value = ''
    currentAssistantMessageId.value = ''
    closeStream()
    ElMessage.info('已停止当前生成任务')
  }

  async function retryAssistantMessage(assistantMessageId: string) {
    const conversationId = currentConversationId.value
    if (!conversationId || sending.value) return
    const query = findRetryQuery(conversationId, assistantMessageId)
    if (!query) {
      ElMessage.warning('未找到可重试的原始问题，请重新输入。')
      return
    }
    composerText.value = query
    await submitQuery(query)
  }

  function openEvidence(cards: EvidenceCard[]) {
    activeEvidenceCards.value = cards
    evidenceDrawerVisible.value = true
  }

  function closeEvidence() {
    evidenceDrawerVisible.value = false
  }

  return {
    conversations,
    groupedConversations,
    currentConversationId,
    currentConversation,
    currentMessages,
    loadingConversations,
    loadingMessages,
    sending,
    currentTaskId,
    workflowAnchorMessageId,
    currentStepLabel,
    currentProgress,
    workflowStages,
    showWorkflowRibbon,
    evidenceDrawerVisible,
    activeEvidenceCards,
    composerText,
    composerParams,
    importedDraftNotice,
    applyDefaultParams,
    resetComposerParams,
    applyScenarioPreset,
    applyImportedDraft,
    clearImportedDraftNotice,
    loadConversationList,
    selectConversation,
    createNewConversation,
    deleteConversation,
    submitCurrentMessage,
    retryAssistantMessage,
    stopCurrentTask,
    openEvidence,
    closeEvidence,
    resetComposer,
    setComposerText,
  }
})
