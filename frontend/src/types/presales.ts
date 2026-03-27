import type { DepartmentSummary } from '@/types/auth'

export interface PresalesUserSummary {
  id: number
  username: string
  display_name: string
  email: string
  phone_number: string
  department: DepartmentSummary | null
  feishu_user_id: string | null
  feishu_open_id: string | null
  sync_source: string
  sync_status: string
}

export interface PresalesTaskActivityItem {
  id: string
  activity_type: string
  operator_user: PresalesUserSummary | null
  from_status: string
  to_status: string
  summary: string
  details_markdown: string
  payload_json: Record<string, unknown>
  created_at: string
}

export interface FeishuDeliveryRecordItem {
  id: string
  business_type: string
  business_id: string
  target_type: 'user' | 'group' | 'department_owner'
  target_id: string
  target_name: string
  message_type: 'text' | 'post' | 'interactive_card'
  request_payload: Record<string, unknown>
  response_payload: Record<string, unknown>
  delivery_status: 'queued' | 'sent' | 'partial' | 'failed' | 'cancelled'
  error_code: string
  error_message: string
  retry_count: number
  operator_user: PresalesUserSummary | null
  created_at: string
  updated_at: string
}

export interface PresalesTaskItem {
  id: string
  task_title: string
  task_type: string
  task_description: string
  source_type: string
  source_id: string
  source_version: number | null
  customer_name: string
  customer_id: string
  owner_user: PresalesUserSummary | null
  owner_department: DepartmentSummary | null
  assignee_user: PresalesUserSummary | null
  collaborator_user_ids: number[]
  status: string
  priority: string
  due_at: string | null
  next_follow_up_at: string | null
  crm_provider: string
  crm_base_id: string
  crm_customer_record_id: string
  crm_customer_snapshot: Record<string, unknown>
  crm_opportunity_record_id: string
  crm_opportunity_snapshot: Record<string, unknown>
  crm_bound_at: string | null
  crm_last_writeback_at: string | null
  crm_last_writeback_status: string
  followup_status: string
  feishu_delivery_status: string
  latest_feishu_delivery: FeishuDeliveryRecordItem | null
  payload_json: Record<string, unknown>
  is_archived: boolean
  archived_at: string | null
  created_by: number
  created_at: string
  updated_at: string
  activities: PresalesTaskActivityItem[]
}

export interface PresalesArchiveRecordItem {
  id: string
  archive_type: string
  source_type: string
  source_id: string
  source_version: number | null
  customer_name: string
  source_title: string
  file_name: string
  mime_type: string
  storage_provider: string
  storage_path: string
  storage_bucket: string
  archive_status: string
  feishu_shared: boolean
  crm_provider: string
  crm_base_id: string
  crm_customer_record_id: string
  crm_customer_snapshot: Record<string, unknown>
  crm_opportunity_record_id: string
  crm_opportunity_snapshot: Record<string, unknown>
  crm_bound_at: string | null
  crm_last_writeback_at: string | null
  crm_last_writeback_status: string
  metadata_json: Record<string, unknown>
  uploaded_by: PresalesUserSummary | null
  created_at: string
  updated_at: string
}

export interface FeishuSyncJobItem {
  id: string
  job_type: 'sync_departments' | 'sync_users' | 'full_sync' | 'offboarding_reconcile'
  trigger_type: 'scheduled' | 'manual' | 'startup'
  status: 'pending' | 'running' | 'completed' | 'partial' | 'failed'
  started_at: string | null
  finished_at: string | null
  synced_user_count: number
  synced_department_count: number
  disabled_user_count: number
  error_count: number
  summary_json: Record<string, unknown>
  error_message: string
  operator_user: PresalesUserSummary | null
  created_at: string
  updated_at: string
}

export interface FeishuRecipientDepartmentItem {
  id: number
  name: string
  code: string
  parent_id: number | null
  feishu_department_id: string | null
}

export interface FeishuRecipientUserItem {
  id: string
  platform_user_id: number | null
  display_name: string
  username: string
  department_id: number | null
  feishu_open_id: string | null
  feishu_user_id: string | null
  sync_status: string
}

export interface FeishuRecipientGroupItem {
  chat_id: string
  name: string
}

export interface FeishuTaskAuthStatus {
  authorized: boolean
  auth_status: string
  authorized_at: string | null
  feishu_open_id: string | null
  feishu_user_id: string | null
}

export interface PresalesTaskPayload {
  task_title: string
  task_type?: string
  task_description?: string
  source_type?: string
  source_id?: string
  source_version?: number | null
  customer_name?: string
  customer_id?: string
  owner_user_id?: number | null
  owner_department_id?: number | null
  assignee_user_id?: number | null
  collaborator_user_ids?: number[]
  status?: string
  priority?: string
  due_at?: string | null
  next_follow_up_at?: string | null
  payload_json?: Record<string, unknown>
}

export interface PresalesTaskFromDemandReportPayload {
  report_id: string
  task_title: string
  task_description?: string
  assignee_user_id?: number | null
  priority?: string
  due_at?: string | null
  next_follow_up_at?: string | null
  collaborator_user_ids?: number[]
  payload_json?: Record<string, unknown>
}

export interface PresalesTaskFromSolutionPayload {
  source_id: string
  source_title: string
  customer_name?: string
  task_title: string
  task_description?: string
  assignee_user_id?: number | null
  priority?: string
  due_at?: string | null
  next_follow_up_at?: string | null
  collaborator_user_ids?: number[]
  payload_json?: Record<string, unknown>
}

export interface PresalesArchivePayload {
  archive_type: string
  source_type: string
  source_id?: string
  source_version?: number | null
  customer_name?: string
  source_title: string
  file_name?: string
  mime_type?: string
  storage_provider?: string
  storage_path: string
  storage_bucket?: string
  metadata_json?: Record<string, unknown>
}

export interface FeishuSendPayload {
  target_type: 'user' | 'group'
  target_id: string
  target_name?: string
  message_type?: 'text' | 'post' | 'interactive_card'
  message_payload?: {
    text?: string
    title?: string
    summary?: string
    [key: string]: unknown
  }
}
