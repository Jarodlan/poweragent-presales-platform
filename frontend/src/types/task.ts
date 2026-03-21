import type { EvidenceCard } from './conversation'

export interface SendMessageResult {
  conversation_id: string
  user_message_id: string
  assistant_message_id: string
  task_id: string
  status: string
  stream_url: string
  result_url: string
}

export interface StreamEnvelope<T = unknown> {
  event: string
  data: T
}

export interface StatusStreamData {
  conversation_id: string
  assistant_message_id: string
  task_id: string
  step: string
  message: string
  progress: number
}

export interface ContentStreamData {
  task_id: string
  content: string
}

export interface EvidenceStreamData {
  task_id: string
  items: EvidenceCard[]
}
