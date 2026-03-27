import { apiRequest } from '@/api/http'
import type { CrmBindPayload, CrmRecordItem, CrmWritebackPayload, CrmWritebackRecordItem } from '@/types/crm'

function buildQuery(params?: Record<string, string | number | undefined>) {
  const query = new URLSearchParams()
  Object.entries(params || {}).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      query.set(key, String(value))
    }
  })
  const suffix = query.toString()
  return suffix ? `?${suffix}` : ''
}

export function fetchCrmCustomers(params?: {
  keyword?: string
  owner_name?: string
}) {
  return apiRequest<{ items: CrmRecordItem[]; total: number }>(`/api/v1/crm/customers${buildQuery(params)}`)
}

export function fetchCrmOpportunities(params?: {
  keyword?: string
  owner_name?: string
  customer_record_id?: string
  stage?: string
}) {
  return apiRequest<{ items: CrmRecordItem[]; total: number }>(`/api/v1/crm/opportunities${buildQuery(params)}`)
}

export function fetchCrmWritebackRecords(params?: {
  object_type?: string
  object_id?: string
}) {
  return apiRequest<{ items: CrmWritebackRecordItem[]; total: number }>(`/api/v1/crm/writebacks${buildQuery(params)}`)
}

export function bindCustomerDemandSessionCrm(sessionId: string, payload: CrmBindPayload) {
  return apiRequest(`/api/v1/customer-demand/sessions/${sessionId}/crm-bind`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function writebackCustomerDemandReportCrm(reportId: string, payload: CrmWritebackPayload) {
  return apiRequest<{ record: CrmWritebackRecordItem }>(`/api/v1/customer-demand/reports/${reportId}/crm-writeback`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function bindConversationCrm(conversationId: string, payload: CrmBindPayload) {
  return apiRequest(`/api/v1/conversations/${conversationId}/crm-bind`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function writebackConversationCrm(conversationId: string, payload: CrmWritebackPayload) {
  return apiRequest<{ record: CrmWritebackRecordItem }>(`/api/v1/conversations/${conversationId}/crm-writeback`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function bindPresalesTaskCrm(taskId: string, payload: CrmBindPayload) {
  return apiRequest(`/api/v1/presales/tasks/${taskId}/crm-bind`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function writebackPresalesTaskCrm(taskId: string, payload: CrmWritebackPayload) {
  return apiRequest<{ record: CrmWritebackRecordItem }>(`/api/v1/presales/tasks/${taskId}/crm-writeback`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function writebackPresalesArchiveCrm(archiveId: string, payload: CrmWritebackPayload) {
  return apiRequest<{ record: CrmWritebackRecordItem }>(`/api/v1/presales/archive/${archiveId}/crm-writeback`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}
