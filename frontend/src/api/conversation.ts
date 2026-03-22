import { apiRequest } from './http'
import type { ConversationItem, MessageItem } from '@/types/conversation'
import type { SendMessageResult } from '@/types/task'

interface ConversationListData {
  items: ConversationItem[]
  page: number
  page_size: number
  has_more: boolean
}

interface MessageListData {
  conversation_id: string
  items: MessageItem[]
  page: number
  page_size: number
  has_more: boolean
}

export function fetchConversationList() {
  return apiRequest<ConversationListData>('/api/v1/conversations?page=1&page_size=20')
}

export function createConversation(title = '') {
  return apiRequest<ConversationItem>('/api/v1/conversations', {
    method: 'POST',
    body: JSON.stringify({ title }),
  })
}

export function fetchConversationDetail(conversationId: string) {
  return apiRequest<ConversationItem>(`/api/v1/conversations/${conversationId}`)
}

export function deleteConversation(conversationId: string) {
  return apiRequest<{ conversation_id: string; deleted: boolean }>(`/api/v1/conversations/${conversationId}`, {
    method: 'DELETE',
  })
}

export function fetchConversationMessages(conversationId: string) {
  return apiRequest<MessageListData>(`/api/v1/conversations/${conversationId}/messages?page=1&page_size=50`)
}

export function sendConversationMessage(
  conversationId: string,
  payload: { query: string; params: Record<string, unknown> },
) {
  return apiRequest<SendMessageResult>(`/api/v1/conversations/${conversationId}/messages`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}
