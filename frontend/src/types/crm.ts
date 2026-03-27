export interface CrmRecordItem {
  provider: string
  base_id: string
  table: string
  record_id: string
  name: string
  industry?: string
  region?: string
  level?: string
  owner_name?: string
  last_followup_at?: string
  customer_record_id?: string
  customer_name?: string
  stage?: string
  amount?: string
  next_followup_at?: string
}

export interface CrmBindPayload {
  provider?: string
  crm_customer_record_id?: string
  crm_opportunity_record_id?: string
}

export interface CrmBoundState {
  crm_provider?: string
  crm_base_id?: string
  crm_customer_record_id?: string
  crm_customer_snapshot?: Record<string, unknown>
  crm_opportunity_record_id?: string
  crm_opportunity_snapshot?: Record<string, unknown>
  crm_bound_at?: string | null
  crm_last_writeback_at?: string | null
  crm_last_writeback_status?: string
}

export interface CrmWritebackRecordItem {
  id: string
  provider: string
  object_type: string
  object_id: string
  target_table: string
  target_record_id: string
  action: string
  status: string
  request_payload: Record<string, unknown>
  response_payload: Record<string, unknown>
  error_message: string
  created_by: number | null
  created_at: string
  updated_at: string
}

export interface CrmWritebackPayload {
  write_target?: 'followup' | 'attachment'
  mode?: 'append' | 'update'
  confirmed: boolean
  sync_next_followup?: boolean
}
