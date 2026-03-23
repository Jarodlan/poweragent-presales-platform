import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

import { fetchCurrentUser, login as loginRequest, logout as logoutRequest } from '@/api/auth'
import { clearStoredAuth, getStoredToken, setStoredToken } from '@/api/http'
import {
  CUSTOMER_DEMAND_PERMISSION_CODES,
  SOLUTION_WORKSPACE_PERMISSION_CODES,
  type CurrentUser,
} from '@/types/auth'

const LAST_USERNAME_KEY = 'poweragent_last_username'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(getStoredToken())
  const user = ref<CurrentUser | null>(null)
  const bootstrapped = ref(false)
  const loading = ref(false)
  const lastUsername = ref(localStorage.getItem(LAST_USERNAME_KEY) || '')

  const isAuthenticated = computed(() => Boolean(token.value && user.value))
  const displayName = computed(() => user.value?.display_name || user.value?.username || '')
  const permissionCodes = computed(() => new Set(user.value?.permissions || []))
  const canManageUsers = computed(() => Boolean(user.value?.is_superuser || permissionCodes.value.has('user.manage')))
  const canManageRoles = computed(() => Boolean(user.value?.is_superuser || permissionCodes.value.has('role.manage')))
  const canManageDepartments = computed(() => Boolean(user.value?.is_superuser || permissionCodes.value.has('department.manage')))
  const canViewAudit = computed(() => Boolean(user.value?.is_superuser || permissionCodes.value.has('audit.view')))
  const canManageAccess = computed(() => Boolean(user.value?.is_superuser || permissionCodes.value.has('platform.manage')))
  const canViewCustomerDemand = computed(() => Boolean(user.value?.is_superuser || CUSTOMER_DEMAND_PERMISSION_CODES.some((code) => permissionCodes.value.has(code))))
  const canAccessSolutionWorkspace = computed(
    () => Boolean(user.value?.is_superuser || SOLUTION_WORKSPACE_PERMISSION_CODES.some((code) => permissionCodes.value.has(code))),
  )
  const canAccessKnowledgeBase = computed(() => Boolean(user.value?.is_superuser || permissionCodes.value.has('knowledge.manage')))

  async function bootstrap() {
    if (bootstrapped.value) return
    token.value = getStoredToken()
    if (!token.value) {
      bootstrapped.value = true
      return
    }
    loading.value = true
    try {
      user.value = await fetchCurrentUser()
    } catch {
      clearStoredAuth()
      token.value = ''
      user.value = null
    } finally {
      bootstrapped.value = true
      loading.value = false
    }
  }

  async function login(username: string, password: string) {
    loading.value = true
    try {
      const data = await loginRequest({ username, password })
      token.value = data.token
      user.value = data.user
      setStoredToken(data.token)
      localStorage.setItem(LAST_USERNAME_KEY, username)
      lastUsername.value = username
      bootstrapped.value = true
      return data.user
    } finally {
      loading.value = false
    }
  }

  async function logout() {
    try {
      if (token.value) {
        await logoutRequest()
      }
    } catch {
      // ignore logout failures; local cleanup still matters
    } finally {
      clearStoredAuth()
      token.value = ''
      user.value = null
      bootstrapped.value = true
    }
  }

  function hasPermission(code: string) {
    return Boolean(user.value?.is_superuser || permissionCodes.value.has(code))
  }

  function hasAnyPermission(codes: string[]) {
    return Boolean(user.value?.is_superuser || codes.some((code) => permissionCodes.value.has(code)))
  }

  return {
    token,
    user,
    loading,
    bootstrapped,
    isAuthenticated,
    displayName,
    permissionCodes,
    canManageUsers,
    canManageRoles,
    canManageDepartments,
    canViewAudit,
    canManageAccess,
    canViewCustomerDemand,
    canAccessSolutionWorkspace,
    canAccessKnowledgeBase,
    lastUsername,
    bootstrap,
    login,
    logout,
    hasPermission,
    hasAnyPermission,
  }
})
