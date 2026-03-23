import { createRouter, createWebHistory } from 'vue-router'

import AdminAccessView from '@/views/AdminAccessView.vue'
import AuditLogView from '@/views/AuditLogView.vue'
import CustomerDemandView from '@/views/CustomerDemandView.vue'
import CustomerDemandReportView from '@/views/CustomerDemandReportView.vue'
import LoginView from '@/views/LoginView.vue'
import PlatformModulesView from '@/views/PlatformModulesView.vue'
import WorkspaceView from '@/views/WorkspaceView.vue'
import { useAuthStore } from '@/stores/auth'
import { pinia } from '@/stores'
import {
  ACCESS_ADMIN_PERMISSION_CODES,
  AUDIT_CENTER_PERMISSION_CODES,
  CUSTOMER_DEMAND_PERMISSION_CODES,
  SOLUTION_WORKSPACE_PERMISSION_CODES,
} from '@/types/auth'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: LoginView,
      meta: { public: true },
    },
    {
      path: '/modules',
      name: 'modules',
      component: PlatformModulesView,
    },
    {
      path: '/',
      name: 'workspace',
      component: WorkspaceView,
      meta: {
        requiredAnyPermission: SOLUTION_WORKSPACE_PERMISSION_CODES,
      },
    },
    {
      path: '/customer-demand',
      name: 'customer-demand',
      component: CustomerDemandView,
      meta: {
        requiredAnyPermission: CUSTOMER_DEMAND_PERMISSION_CODES,
      },
    },
    {
      path: '/customer-demand/:sessionId/report',
      name: 'customer-demand-report',
      component: CustomerDemandReportView,
      meta: {
        requiredAnyPermission: CUSTOMER_DEMAND_PERMISSION_CODES,
      },
    },
    {
      path: '/admin/access',
      name: 'admin-access',
      component: AdminAccessView,
      meta: {
        requiredAnyPermission: ACCESS_ADMIN_PERMISSION_CODES,
      },
    },
    {
      path: '/admin/audit',
      name: 'admin-audit',
      component: AuditLogView,
      meta: {
        requiredAnyPermission: AUDIT_CENTER_PERMISSION_CODES,
      },
    },
  ],
})

router.beforeEach(async (to) => {
  const authStore = useAuthStore(pinia)
  await authStore.bootstrap()

  if (to.meta.public) {
    if (to.name === 'login' && authStore.isAuthenticated) {
      return { name: 'modules' }
    }
    return true
  }

  if (!authStore.isAuthenticated) {
    return {
      name: 'login',
      query: { redirect: to.fullPath },
    }
  }

  const requiredAnyPermission = (to.meta.requiredAnyPermission as string[] | undefined) || []
  if (requiredAnyPermission.length && !authStore.hasAnyPermission(requiredAnyPermission)) {
    return { name: 'modules' }
  }

  return true
})

export default router
