import { createRouter, createWebHistory } from 'vue-router'

import WorkspaceView from '@/views/WorkspaceView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'workspace',
      component: WorkspaceView,
    },
  ],
})

export default router
