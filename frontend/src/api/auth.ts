import { apiRequest } from './http'
import type { CurrentUser, LoginPayload, LoginResult } from '@/types/auth'

export function login(payload: LoginPayload) {
  return apiRequest<LoginResult>('/api/v1/auth/login', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function fetchCurrentUser() {
  return apiRequest<CurrentUser>('/api/v1/auth/me')
}

export function logout() {
  return apiRequest<{ logged_out: boolean }>('/api/v1/auth/logout', {
    method: 'POST',
  })
}
