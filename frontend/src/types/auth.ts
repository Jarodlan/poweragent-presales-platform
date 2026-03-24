export interface DepartmentSummary {
  id: number
  name: string
  code: string
  status: string
  parent_id: number | null
}

export interface UserRoleAssignment {
  id: number
  role: {
    id: number
    code: string
    name: string
    description: string
    data_scope: string
    is_system: boolean
    permissions: Array<{
      code: string
      name: string
      module: string
      action: string
      resource_scope: string
      description: string
    }>
  }
  department: DepartmentSummary | null
  assigned_at: string
}

export interface CurrentUser {
  id: number
  username: string
  email: string
  display_name: string
  employee_no: string
  phone_number: string
  job_title: string
  department: DepartmentSummary | null
  account_status: string
  data_scope: string
  data_scope_resolved: string
  feishu_user_id: string | null
  feishu_open_id: string | null
  sync_source: string
  sync_status: string
  force_password_change: boolean
  is_active: boolean
  is_staff: boolean
  is_superuser: boolean
  roles: UserRoleAssignment[]
  permissions: string[]
  last_login: string | null
  last_login_ip: string | null
  remarks: string
  archived_at: string | null
  status_before_archive: string
}

export interface LoginPayload {
  username: string
  password: string
}

export interface LoginResult {
  token: string
  token_type: string
  expires_at: string
  expires_in_days: number
  user: CurrentUser
}

export const SOLUTION_WORKSPACE_PERMISSION_CODES = [
  'solution.access',
  'conversation.view',
  'conversation.manage_department',
  'conversation.manage_all',
  'task.view',
  'task.manage_department',
  'task.manage_all',
]

export const CUSTOMER_DEMAND_PERMISSION_CODES = [
  'customer_demand.access',
  'customer_demand.view',
  'customer_demand.create',
  'customer_demand.manage_all',
  'customer_demand.export',
]

export const KNOWLEDGE_BASE_PERMISSION_CODES = ['knowledge.access', 'knowledge.manage']
export const ACCESS_ADMIN_PERMISSION_CODES = ['access_admin.access', 'platform.manage']
export const AUDIT_CENTER_PERMISSION_CODES = ['audit.access', 'audit.view']
export const PRESALES_CENTER_PERMISSION_CODES = ['presales_center.access', 'presales_task.view', 'presales_task.manage']
