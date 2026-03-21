export type ConversationStatus = 'idle' | 'running' | 'failed'
export type MessageRole = 'user' | 'assistant' | 'system'
export type MessageStatus = 'pending' | 'running' | 'completed' | 'failed'

export interface EvidenceCard {
  source_type: string
  title: string
  summary?: string
  metadata?: Record<string, unknown>
}

export interface ConversationItem {
  conversation_id: string
  title: string
  status: ConversationStatus
  last_user_message: string
  last_message_at: string | null
  created_at: string
  updated_at: string
}

export interface AssistantMessage {
  message_id: string
  conversation_id: string
  role: MessageRole
  status: MessageStatus
  query_text: string
  summary: string
  content: string
  assumptions: string[]
  evidence_cards: EvidenceCard[]
  created_at: string
}

export interface UserMessage {
  message_id: string
  conversation_id: string
  role: MessageRole
  status: MessageStatus
  query_text: string
  summary?: string
  content: string
  assumptions?: string[]
  evidence_cards?: EvidenceCard[]
  created_at: string
}

export type MessageItem = AssistantMessage | UserMessage
