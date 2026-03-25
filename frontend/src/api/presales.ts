import { apiRequest } from '@/api/http'
import type {
  FeishuDeliveryRecordItem,
  FeishuRecipientDepartmentItem,
  FeishuRecipientGroupItem,
  FeishuRecipientUserItem,
  FeishuSendPayload,
  FeishuSyncJobItem,
  FeishuTaskAuthStatus,
  PresalesArchivePayload,
  PresalesArchiveRecordItem,
  PresalesTaskItem,
  PresalesTaskFromDemandReportPayload,
  PresalesTaskFromSolutionPayload,
  PresalesTaskPayload,
} from '@/types/presales'

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

export function fetchPresalesTasks(params?: Record<string, string | number | undefined>) {
  return apiRequest<{ items: PresalesTaskItem[]; total: number }>(`/api/v1/presales/tasks${buildQuery(params)}`)
}

export function fetchPresalesTask(taskId: string) {
  return apiRequest<{ task: PresalesTaskItem }>(`/api/v1/presales/tasks/${taskId}`)
}

export function createPresalesTask(payload: PresalesTaskPayload) {
  return apiRequest<{ task: PresalesTaskItem }>('/api/v1/presales/tasks', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function createPresalesTaskFromDemandReport(payload: PresalesTaskFromDemandReportPayload) {
  return apiRequest<{ task: PresalesTaskItem }>('/api/v1/presales/tasks/from-demand-report', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function createPresalesTaskFromSolution(payload: PresalesTaskFromSolutionPayload) {
  return apiRequest<{ task: PresalesTaskItem }>('/api/v1/presales/tasks/from-solution', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function updatePresalesTask(taskId: string, payload: Partial<PresalesTaskPayload>) {
  return apiRequest<{ task: PresalesTaskItem }>(`/api/v1/presales/tasks/${taskId}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  })
}

export function completePresalesTask(taskId: string, summary = '') {
  return apiRequest<{ task: PresalesTaskItem }>(`/api/v1/presales/tasks/${taskId}/complete`, {
    method: 'POST',
    body: JSON.stringify({ summary }),
  })
}

export function sendPresalesTaskToFeishu(taskId: string, payload: FeishuSendPayload) {
  return apiRequest<{ delivery: FeishuDeliveryRecordItem }>(`/api/v1/presales/tasks/${taskId}/send-feishu`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function fetchPresalesArchives(params?: Record<string, string | number | undefined>) {
  return apiRequest<{ items: PresalesArchiveRecordItem[]; total: number }>(`/api/v1/presales/archive${buildQuery(params)}`)
}

export function createPresalesArchive(payload: PresalesArchivePayload) {
  return apiRequest<{ archive: PresalesArchiveRecordItem }>('/api/v1/presales/archive', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function fetchFeishuDeliveries(params?: Record<string, string | number | undefined>) {
  return apiRequest<{ items: FeishuDeliveryRecordItem[]; total: number }>(`/api/v1/presales/feishu/deliveries${buildQuery(params)}`)
}

export function fetchFeishuRecipients() {
  return apiRequest<{ departments: FeishuRecipientDepartmentItem[]; users: FeishuRecipientUserItem[]; groups: FeishuRecipientGroupItem[] }>(
    '/api/v1/presales/feishu/recipients',
  )
}

export function fetchFeishuTaskAuthStatus() {
  return apiRequest<FeishuTaskAuthStatus>('/api/v1/presales/feishu/user-auth/status')
}

export function fetchFeishuTaskAuthorizeUrl(nextPath = '/presales') {
  return apiRequest<{ authorize_url: string }>(`/api/v1/presales/feishu/user-auth/start${buildQuery({ next: nextPath })}`)
}

export function fetchFeishuSyncJobs() {
  return apiRequest<{ items: FeishuSyncJobItem[]; total: number }>('/api/v1/presales/feishu/sync-jobs')
}

export function createFeishuSyncJob(jobType: FeishuSyncJobItem['job_type']) {
  return apiRequest<{ job: FeishuSyncJobItem }>('/api/v1/presales/feishu/sync-jobs', {
    method: 'POST',
    body: JSON.stringify({ job_type: jobType }),
  })
}
