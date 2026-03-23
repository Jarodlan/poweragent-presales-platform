export interface CustomerDemandSessionItem {
  id: string
  owner: number
  owner_display_name: string
  department: number | null
  department_name: string
  customer_name: string
  session_title: string
  industry: string
  region: string
  topic: string
  customer_type: string
  knowledge_enabled: boolean
  knowledge_scope: Record<string, unknown>
  status: string
  recording_started_at: string | null
  recording_stopped_at: string | null
  analysis_started_at: string | null
  analysis_finished_at: string | null
  raw_segment_count: number
  normalized_segment_count: number
  latest_stage_version: number
  latest_report_id: string | null
  remarks: string
  created_at: string
  updated_at: string
}

export interface CustomerDemandSegmentItem {
  id: string
  session: string
  sequence_no: number
  speaker_label: string
  raw_text: string
  normalized_text: string
  final_text: string
  asr_provider: string
  llm_provider: string
  confidence_score: string | number | null
  semantic_score: string | number | null
  semantic_payload?: Record<string, unknown>
  review_flag: boolean
  issues_json: string[]
  raw_start_ms: number | null
  raw_end_ms: number | null
  segment_status: string
  created_at: string
  updated_at: string
}

export interface CustomerDemandReviewSegmentPayload {
  decision: 'accept' | 'discard'
  edited_text?: string
  note?: string
}

export interface CustomerDemandStageSummaryItem {
  id: string
  session: string
  summary_version: number
  trigger_type: string
  covered_segment_start: number
  covered_segment_end: number
  summary_markdown: string
  summary_payload: Record<string, unknown>
  llm_model: string
  created_by: number | null
  created_at: string
}

export interface CustomerDemandReportItem {
  id: string
  session: string
  report_version: number
  report_title: string
  report_markdown: string
  report_html: string
  report_payload: Record<string, unknown>
  digging_suggestions_markdown: string
  digging_suggestions_payload: Record<string, unknown>
  recommended_questions_markdown: string
  knowledge_enabled: boolean
  used_knowledge_sources: CustomerDemandKnowledgeSource[]
  llm_model: string
  status: string
  created_by: number | null
  created_at: string
  updated_at: string
}

export interface CustomerDemandKnowledgeSource {
  source_type: string
  source_label: string
  title: string
  snippet: string
  score: number
  metadata: Record<string, unknown>
}

export interface CustomerDemandTaskItem {
  id: string
  session: string
  task_type: string
  status: string
  current_step: string
  current_step_label: string
  progress: number
  request_payload: Record<string, unknown>
  result_payload: Record<string, unknown>
  error_message: string
  started_by: number | null
  started_at: string | null
  finished_at: string | null
  created_at: string
  updated_at: string
}

export interface CustomerDemandSessionListData {
  items: CustomerDemandSessionItem[]
  total: number
}

export interface CustomerDemandSegmentListData {
  items: CustomerDemandSegmentItem[]
}

export interface CustomerDemandStageSummaryListData {
  items: CustomerDemandStageSummaryItem[]
}

export interface CustomerDemandCreateSessionPayload {
  customer_name: string
  session_title: string
  industry?: string
  region?: string
  topic?: string
  customer_type?: string
  knowledge_enabled?: boolean
  knowledge_scope?: Record<string, unknown>
  remarks?: string
}

export type CustomerDemandUpdateSessionPayload = Partial<CustomerDemandCreateSessionPayload>

export interface CustomerDemandManualSegmentPayload {
  sequence_no: number
  speaker_label?: string
  raw_text: string
  normalized_text: string
  final_text: string
  asr_provider?: string
  segment_status?: string
  review_flag?: boolean
  issues_json?: string[]
}

export interface CustomerDemandAudioUploadResult {
  accepted: boolean
  chunk_index: number
  session_id: string
  segment: CustomerDemandSegmentItem | null
  adapter_metadata: Record<string, unknown>
  reason?: string
  auto_task?: CustomerDemandTaskItem | null
}

export interface CustomerDemandSegmentCreateResult {
  segment: CustomerDemandSegmentItem
  auto_task?: CustomerDemandTaskItem | null
}

export interface CustomerDemandTriggerStageSummaryResult {
  task: CustomerDemandTaskItem
}

export interface CustomerDemandAnalyzeResult {
  task: CustomerDemandTaskItem
}

export interface CustomerDemandExportResult {
  session_id: string
  report_id: string
  format: string
  content: string
}
