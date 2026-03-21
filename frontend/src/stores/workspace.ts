import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

import {
  createConversation,
  fetchConversationList,
  fetchConversationMessages,
  sendConversationMessage,
} from '@/api/conversation'
import { cancelTask } from '@/api/task'
import { createTaskEventSource } from '@/utils/sse'
import { groupConversationLabel } from '@/utils/time'
import type { ConversationItem, EvidenceCard, MessageItem } from '@/types/conversation'
import type { ContentStreamData, EvidenceStreamData, SendMessageResult, StatusStreamData, StreamEnvelope } from '@/types/task'

interface ComposerParams {
  grid_environment: string
  equipment_type: string
  data_basis: string[]
  target_capability: string[]
}

const DEFAULT_PARAMS: ComposerParams = {
  grid_environment: 'distribution_network',
  equipment_type: 'comprehensive',
  data_basis: ['scada', 'online_monitoring', 'historical_workorder'],
  target_capability: ['fault_diagnosis', 'root_cause_analysis'],
}

export const useWorkspaceStore = defineStore('workspace', () => {
  const conversations = ref<ConversationItem[]>([])
  const messages = ref<Record<string, MessageItem[]>>({})
  const currentConversationId = ref<string>('')
  const loadingConversations = ref(false)
  const loadingMessages = ref(false)
  const sending = ref(false)
  const currentTaskId = ref<string>('')
  const currentStepLabel = ref('')
  const currentProgress = ref(0)
  const evidenceDrawerVisible = ref(false)
  const activeEvidenceCards = ref<EvidenceCard[]>([])
  const composerText = ref('')
  const composerParams = ref<ComposerParams>({ ...DEFAULT_PARAMS })
  let eventSource: EventSource | null = null

  const groupedConversations = computed(() => {
    const groups = new Map<string, ConversationItem[]>()
    for (const item of conversations.value) {
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

  function applyDefaultParams(defaults?: Record<string, string | string[]>) {
    composerParams.value = {
      grid_environment: (defaults?.grid_environment as string) || DEFAULT_PARAMS.grid_environment,
      equipment_type: (defaults?.equipment_type as string) || DEFAULT_PARAMS.equipment_type,
      data_basis: (defaults?.data_basis as string[]) || DEFAULT_PARAMS.data_basis,
      target_capability: (defaults?.target_capability as string[]) || DEFAULT_PARAMS.target_capability,
    }
  }

  async function loadConversationList() {
    loadingConversations.value = true
    try {
      const data = await fetchConversationList()
      conversations.value = data.items
      if (!currentConversationId.value && data.items[0]) {
        currentConversationId.value = data.items[0].conversation_id
      }
    } finally {
      loadingConversations.value = false
    }
  }

  async function selectConversation(conversationId: string) {
    currentConversationId.value = conversationId
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
    const conversation = await createConversation('')
    conversations.value.unshift(conversation)
    currentConversationId.value = conversation.conversation_id
    messages.value[conversation.conversation_id] = []
    resetComposer()
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

  function bindTaskStream(payload: SendMessageResult) {
    closeStream()
    currentTaskId.value = payload.task_id
    currentProgress.value = 0
    currentStepLabel.value = '正在启动生成流程'
    eventSource = createTaskEventSource(payload.stream_url)

    eventSource.onmessage = (event) => {
      const envelope = JSON.parse(event.data) as StreamEnvelope
      const conversationId = payload.conversation_id
      const assistantMessageId = payload.assistant_message_id
      ensureAssistantMessage(conversationId, assistantMessageId)

      switch (envelope.event) {
        case 'conversation_meta': {
          const data = envelope.data as { conversation_id: string; title: string }
          patchConversation(data.conversation_id, { title: data.title || '新会话' })
          break
        }
        case 'status': {
          const data = envelope.data as StatusStreamData
          currentStepLabel.value = data.message
          currentProgress.value = data.progress
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
          sending.value = false
          currentTaskId.value = ''
          closeStream()
          break
        }
        case 'error': {
          patchAssistantMessage(conversationId, assistantMessageId, {
            status: 'failed',
            content: '生成过程中出现异常，请重试。',
          })
          patchConversation(conversationId, { status: 'failed' })
          currentStepLabel.value = '生成失败'
          sending.value = false
          currentTaskId.value = ''
          closeStream()
          break
        }
      }
    }

    eventSource.onerror = () => {
      currentStepLabel.value = '流式连接中断'
      sending.value = false
      closeStream()
    }
  }

  async function submitCurrentMessage() {
    if (!currentConversationId.value) {
      await createNewConversation()
    }
    const query = composerText.value.trim()
    if (!query || !currentConversationId.value) return

    const conversationId = currentConversationId.value
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

    const payload = await sendConversationMessage(conversationId, {
      query,
      params: composerParams.value,
    })
    resetComposer()
    bindTaskStream(payload)
  }

  async function stopCurrentTask() {
    if (!currentTaskId.value) return
    await cancelTask(currentTaskId.value)
    currentStepLabel.value = '已停止生成'
    sending.value = false
    closeStream()
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
    currentStepLabel,
    currentProgress,
    evidenceDrawerVisible,
    activeEvidenceCards,
    composerText,
    composerParams,
    applyDefaultParams,
    loadConversationList,
    selectConversation,
    createNewConversation,
    submitCurrentMessage,
    stopCurrentTask,
    openEvidence,
    closeEvidence,
    resetComposer,
  }
})
