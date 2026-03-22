import type { DepartmentSummary, CurrentUser } from '@/types/auth'

export interface PermissionItem {
  code: string
  name: string
  module: string
  action: string
  resource_scope: string
  description: string
}

export interface RoleItem {
  id: number
  code: string
  name: string
  description: string
  data_scope: string
  is_system: boolean
  permissions: PermissionItem[]
  created_at: string
  updated_at: string
}

export interface DepartmentItem extends DepartmentSummary {
  description: string
  parent_name: string | null
  sort_order: number
  created_at: string
  updated_at: string
}

export interface UserItem extends CurrentUser {}

export interface RolePayload {
  code: string
  name: string
  description: string
  data_scope: string
  permission_codes: string[]
}

export interface DepartmentPayload {
  name: string
  code: string
  description: string
  status: string
  parent_id: number | null
  sort_order: number
}

export interface UserPayload {
  username: string
  email: string
  display_name: string
  employee_no: string
  phone_number: string
  job_title: string
  department_id: number | null
  account_status: string
  data_scope: string
  force_password_change: boolean
  is_active: boolean
  is_staff: boolean
  remarks: string
  password?: string
  role_ids: number[]
}
