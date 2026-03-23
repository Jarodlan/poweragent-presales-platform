import { apiRequest } from '@/api/http'
import type {
  AuditLogItem,
  DepartmentItem,
  DepartmentPayload,
  PermissionItem,
  RoleItem,
  RolePayload,
  UserConversationActivityItem,
  UserItem,
  UserTaskActivityItem,
  UserPayload,
} from '@/types/admin'

export function fetchUsers(includeArchived = false) {
  const suffix = includeArchived ? '?include_archived=1' : ''
  return apiRequest<{ items: UserItem[] }>(`/api/v1/users${suffix}`)
}

export function createUser(payload: UserPayload) {
  return apiRequest<UserItem>('/api/v1/users', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function updateUser(userId: number, payload: Partial<UserPayload>) {
  return apiRequest<UserItem>(`/api/v1/users/${userId}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  })
}

export function archiveUser(userId: number) {
  return apiRequest<{ archived: boolean }>(`/api/v1/users/${userId}`, {
    method: 'DELETE',
  })
}

export function restoreUser(userId: number) {
  return apiRequest<UserItem>(`/api/v1/users/${userId}/restore`, {
    method: 'POST',
  })
}

export function fetchUserActivity(userId: number) {
  return apiRequest<{
    login_items: AuditLogItem[]
    operation_items: AuditLogItem[]
    conversation_items: UserConversationActivityItem[]
    task_items: UserTaskActivityItem[]
  }>(`/api/v1/users/${userId}/activity`)
}

export function resetUserPassword(userId: number, password: string, forcePasswordChange = true) {
  return apiRequest<{ reset: boolean }>(`/api/v1/users/${userId}/reset-password`, {
    method: 'POST',
    body: JSON.stringify({ password, force_password_change: forcePasswordChange }),
  })
}

export function fetchRoles() {
  return apiRequest<{ items: RoleItem[] }>('/api/v1/roles')
}

export function createRole(payload: RolePayload) {
  return apiRequest<RoleItem>('/api/v1/roles', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function updateRole(roleId: number, payload: Partial<RolePayload>) {
  return apiRequest<RoleItem>(`/api/v1/roles/${roleId}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  })
}

export function deleteRole(roleId: number) {
  return apiRequest<{ deleted: boolean }>(`/api/v1/roles/${roleId}`, {
    method: 'DELETE',
  })
}

export function fetchPermissions() {
  return apiRequest<{ items: PermissionItem[] }>('/api/v1/permissions')
}

export function fetchDepartments() {
  return apiRequest<{ items: DepartmentItem[] }>('/api/v1/departments')
}

export function createDepartment(payload: DepartmentPayload) {
  return apiRequest<DepartmentItem>('/api/v1/departments', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function updateDepartment(departmentId: number, payload: Partial<DepartmentPayload>) {
  return apiRequest<DepartmentItem>(`/api/v1/departments/${departmentId}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  })
}

export function deleteDepartment(departmentId: number) {
  return apiRequest<{ deleted: boolean }>(`/api/v1/departments/${departmentId}`, {
    method: 'DELETE',
  })
}

export function fetchAuditLogs(params?: {
  action?: string
  resource_type?: string
  actor_id?: number | string
  keyword?: string
  start_date?: string
  end_date?: string
}) {
  const query = new URLSearchParams()
  if (params?.start_date) query.set('start_date', params.start_date)
  if (params?.end_date) query.set('end_date', params.end_date)
  if (params?.action) query.set('action', params.action)
  if (params?.resource_type) query.set('resource_type', params.resource_type)
  if (params?.actor_id) query.set('actor_id', String(params.actor_id))
  if (params?.keyword) query.set('keyword', params.keyword)
  const suffix = query.toString() ? `?${query.toString()}` : ''
  return apiRequest<{ items: AuditLogItem[] }>(`/api/v1/audit/logs${suffix}`)
}
