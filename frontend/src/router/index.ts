import { createRouter, createWebHistory } from 'vue-router'

import AdminAccessView from '@/views/AdminAccessView.vue'
import AuditLogView from '@/views/AuditLogView.vue'
import CustomerDemandView from '@/views/CustomerDemandView.vue'
import LoginView from '@/views/LoginView.vue'
import WorkspaceView from '@/views/WorkspaceView.vue'
import { useAuthStore } from '@/stores/auth'
import { pinia } from '@/stores'

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
      path: '/',
      name: 'workspace',
      component: WorkspaceView,
    },
    {
      path: '/customer-demand',
      name: 'customer-demand',
      component: CustomerDemandView,
      meta: {
        requiredAnyPermission: ['customer_demand.view'],
      },
    },
    {
      path: '/admin/access',
      name: 'admin-access',
      component: AdminAccessView,
      meta: {
        requiredAnyPermission: ['platform.manage'],
      },
    },
    {
      path: '/admin/audit',
      name: 'admin-audit',
      component: AuditLogView,
      meta: {
        requiredAnyPermission: ['audit.view'],
      },
    },
  ],
})

router.beforeEach(async (to) => {
  const authStore = useAuthStore(pinia)
  await authStore.bootstrap()

  if (to.meta.public) {
    if (to.name === 'login' && authStore.isAuthenticated) {
      return { name: 'workspace' }
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
    return { name: 'workspace' }
  }

  return true
})

export default router
