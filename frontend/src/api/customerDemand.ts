import { apiRequest } from './http'
import type {
  CustomerDemandAnalyzeResult,
  CustomerDemandAudioUploadResult,
  CustomerDemandCreateSessionPayload,
  CustomerDemandExportResult,
  CustomerDemandManualSegmentPayload,
  CustomerDemandReportItem,
  CustomerDemandReviewSegmentPayload,
  CustomerDemandSegmentListData,
  CustomerDemandSessionItem,
  CustomerDemandSessionListData,
  CustomerDemandStageSummaryListData,
  CustomerDemandTaskItem,
  CustomerDemandTriggerStageSummaryResult,
  CustomerDemandUpdateSessionPayload,
} from '@/types/customerDemand'

export function fetchCustomerDemandSessions(params?: {
  keyword?: string
  status?: string
  industry?: string
  region?: string
}) {
  const query = new URLSearchParams()
  Object.entries(params || {}).forEach(([key, value]) => {
    if (value) query.set(key, String(value))
  })
  const suffix = query.toString() ? `?${query.toString()}` : ''
  return apiRequest<CustomerDemandSessionListData>(`/api/v1/customer-demand/sessions${suffix}`)
}

export function createCustomerDemandSession(payload: CustomerDemandCreateSessionPayload) {
  return apiRequest<CustomerDemandSessionItem>('/api/v1/customer-demand/sessions', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function fetchCustomerDemandSessionDetail(sessionId: string) {
  return apiRequest<CustomerDemandSessionItem>(`/api/v1/customer-demand/sessions/${sessionId}`)
}

export function updateCustomerDemandSession(sessionId: string, payload: CustomerDemandUpdateSessionPayload) {
  return apiRequest<CustomerDemandSessionItem>(`/api/v1/customer-demand/sessions/${sessionId}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  })
}

export function startCustomerDemandSession(sessionId: string) {
  return apiRequest<{ session_id: string; status: string; asr_upload_url: string; stream_url: string }>(
    `/api/v1/customer-demand/sessions/${sessionId}/start`,
    {
      method: 'POST',
    },
  )
}

export function pauseCustomerDemandSession(sessionId: string) {
  return apiRequest<{ session_id: string; status: string }>(`/api/v1/customer-demand/sessions/${sessionId}/pause`, {
    method: 'POST',
  })
}

export function stopCustomerDemandSession(sessionId: string) {
  return apiRequest<{ session_id: string; status: string; recording_stopped_at: string }>(
    `/api/v1/customer-demand/sessions/${sessionId}/stop`,
    {
      method: 'POST',
    },
  )
}

export function fetchCustomerDemandSegments(sessionId: string) {
  return apiRequest<CustomerDemandSegmentListData>(`/api/v1/customer-demand/sessions/${sessionId}/segments`)
}

export function createCustomerDemandManualSegment(sessionId: string, payload: CustomerDemandManualSegmentPayload) {
  return apiRequest(`/api/v1/customer-demand/sessions/${sessionId}/segments`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function uploadCustomerDemandAudioChunk(sessionId: string, payload: {
  file: File
  chunkIndex: number
  provider?: string
  language?: string
  audioFs?: number
}) {
  const formData = new FormData()
  formData.append('audio_chunk', payload.file)
  formData.append('chunk_index', String(payload.chunkIndex))
  formData.append('provider', payload.provider || 'qwen')
  formData.append('language', payload.language || 'zh')
  formData.append('audio_fs', String(payload.audioFs || 16000))

  return apiRequest<CustomerDemandAudioUploadResult>(`/api/v1/customer-demand/sessions/${sessionId}/segments/audio`, {
    method: 'POST',
    body: formData,
  })
}

export function reviewCustomerDemandSegment(sessionId: string, segmentId: string, payload: CustomerDemandReviewSegmentPayload) {
  return apiRequest(`/api/v1/customer-demand/sessions/${sessionId}/segments/${segmentId}/review`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function fetchCustomerDemandStageSummaries(sessionId: string) {
  return apiRequest<CustomerDemandStageSummaryListData>(`/api/v1/customer-demand/sessions/${sessionId}/stage-summaries`)
}

export function triggerCustomerDemandStageSummary(sessionId: string, triggerType = 'manual') {
  return apiRequest<CustomerDemandTriggerStageSummaryResult>(`/api/v1/customer-demand/sessions/${sessionId}/stage-summary`, {
    method: 'POST',
    body: JSON.stringify({ trigger_type: triggerType }),
  })
}

export function triggerCustomerDemandAnalyze(sessionId: string, knowledgeEnabled: boolean) {
  return apiRequest<CustomerDemandAnalyzeResult>(`/api/v1/customer-demand/sessions/${sessionId}/analyze`, {
    method: 'POST',
    body: JSON.stringify({ knowledge_enabled: knowledgeEnabled }),
  })
}

export function fetchCustomerDemandReport(sessionId: string) {
  return apiRequest<CustomerDemandReportItem | null>(`/api/v1/customer-demand/sessions/${sessionId}/report`)
}

export function fetchCustomerDemandTask(taskId: string) {
  return apiRequest<CustomerDemandTaskItem>(`/api/v1/customer-demand/tasks/${taskId}`)
}

export function exportCustomerDemandReport(sessionId: string, format = 'markdown') {
  return apiRequest<CustomerDemandExportResult>(`/api/v1/customer-demand/sessions/${sessionId}/export`, {
    method: 'POST',
    body: JSON.stringify({ format }),
  })
}
