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
  force_password_change: boolean
  is_active: boolean
  is_staff: boolean
  is_superuser: boolean
  roles: UserRoleAssignment[]
  permissions: string[]
  last_login: string | null
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
