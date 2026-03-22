import { apiRequest } from '@/api/http'
import type {
  DepartmentItem,
  DepartmentPayload,
  PermissionItem,
  RoleItem,
  RolePayload,
  UserItem,
  UserPayload,
} from '@/types/admin'

export function fetchUsers() {
  return apiRequest<{ items: UserItem[] }>('/api/v1/users')
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
