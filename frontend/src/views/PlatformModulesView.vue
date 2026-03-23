<script setup lang="ts">
import {
  ChatDotRound,
  Cpu,
  Document,
  FolderOpened,
  Grid,
  Setting,
  SwitchButton,
} from '@element-plus/icons-vue'
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

import EmptyState from '@/components/common/EmptyState.vue'
import { fetchPlatformModules } from '@/api/platform'
import { useAuthStore } from '@/stores/auth'
import type { PlatformModuleItem } from '@/types/platform'

const router = useRouter()
const authStore = useAuthStore()

const loading = ref(false)
const modules = ref<PlatformModuleItem[]>([])

const iconMap = {
  Grid,
  Cpu,
  ChatDotRound,
  FolderOpened,
  Setting,
  Document,
} as const

const moduleCountLabel = computed(() => `${modules.value.length} 个可用模块`)
const roleNames = computed(() => authStore.user?.roles.map((item) => item.role.name).join(' / ') || '未分配角色')

async function loadModules() {
  loading.value = true
  try {
    const data = await fetchPlatformModules()
    modules.value = data.items
  } finally {
    loading.value = false
  }
}

async function openModule(item: PlatformModuleItem) {
  if (item.route_type === 'external') {
    window.open(item.route_target, item.open_mode === 'new_tab' ? '_blank' : '_self', 'noopener')
    return
  }
  await router.push(item.route_target)
}

async function handleLogout() {
  await authStore.logout()
  ElMessage.success('已退出登录')
  await router.replace('/login')
}

function resolveIcon(name: string) {
  return iconMap[name as keyof typeof iconMap] || Grid
}

onMounted(loadModules)
</script>

<template>
  <div class="modules-shell">
    <header class="modules-header panel-card">
      <div>
        <p class="section-title">PowerAgent</p>
        <h1>统一模块入口</h1>
        <p>登录后先从这里进入有权限使用的业务模块与管理模块，平台级入口不再分散在各个工作台内部。</p>
      </div>
      <div class="modules-header__actions">
        <div class="modules-user panel-card">
          <strong>{{ authStore.displayName || '未登录用户' }}</strong>
          <p>{{ authStore.user?.department?.name || '未设置部门' }} · {{ roleNames }}</p>
        </div>
        <el-button plain @click="loadModules">刷新模块</el-button>
        <el-button type="primary" plain @click="handleLogout">
          <el-icon><SwitchButton /></el-icon>
          退出登录
        </el-button>
      </div>
    </header>

    <section class="modules-summary panel-card">
      <div>
        <strong>当前平台首页</strong>
        <p>按权限展示功能模块，减少从某个工作台再绕去其他模块的情况。</p>
      </div>
      <el-tag type="info" effect="plain">{{ moduleCountLabel }}</el-tag>
    </section>

    <section class="modules-content">
      <div v-if="loading" class="modules-loading panel-card">正在加载模块入口...</div>
      <div v-else-if="!modules.length" class="modules-empty">
        <EmptyState
          title="当前没有可用模块"
          description="当前账户已经登录，但还没有被授予任何模块入口权限，请联系平台管理员开通。"
        />
      </div>
      <div v-else class="modules-grid">
        <article
          v-for="item in modules"
          :key="item.module_id"
          class="modules-card panel-card"
          @click="openModule(item)"
        >
          <div class="modules-card__icon">
            <el-icon><component :is="resolveIcon(item.icon)" /></el-icon>
          </div>
          <div class="modules-card__body">
            <div class="modules-card__head">
              <strong>{{ item.name }}</strong>
              <el-tag v-if="item.route_type === 'external'" size="small" effect="light">外部平台</el-tag>
            </div>
            <p>{{ item.description }}</p>
          </div>
          <div class="modules-card__foot">
            <span>{{ item.route_type === 'external' ? '将在新标签页打开' : '进入工作台' }}</span>
            <el-button type="primary" text @click.stop="openModule(item)">
              {{ item.route_type === 'external' ? '打开模块' : '进入模块' }}
            </el-button>
          </div>
        </article>
      </div>
    </section>
  </div>
</template>

<style scoped>
.modules-shell {
  display: flex;
  flex-direction: column;
  gap: 18px;
  padding: 24px;
}

.modules-header,
.modules-summary,
.modules-loading,
.modules-card {
  padding: 22px 24px;
}

.modules-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;
}

.modules-header h1 {
  margin: 8px 0 10px;
  font-size: 34px;
}

.modules-header p,
.modules-summary p,
.modules-card p {
  margin: 0;
  color: var(--muted);
  line-height: 1.7;
}

.modules-header__actions {
  display: flex;
  align-items: stretch;
  gap: 12px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.modules-user {
  min-width: 240px;
  padding: 14px 16px;
  border-radius: 20px;
}

.modules-user strong {
  display: block;
  font-size: 14px;
}

.modules-user p {
  margin-top: 4px;
  font-size: 12px;
}

.modules-summary {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.modules-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 18px;
}

.modules-card {
  display: flex;
  flex-direction: column;
  gap: 18px;
  min-height: 220px;
  cursor: pointer;
  transition:
    transform 0.2s ease,
    box-shadow 0.2s ease,
    border-color 0.2s ease;
}

.modules-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 18px 36px rgba(16, 56, 88, 0.12);
  border-color: rgba(33, 98, 163, 0.16);
}

.modules-card__icon {
  width: 52px;
  height: 52px;
  display: grid;
  place-items: center;
  border-radius: 18px;
  background: rgba(16, 101, 163, 0.08);
  color: var(--brand-strong);
  font-size: 24px;
}

.modules-card__body {
  display: flex;
  flex-direction: column;
  gap: 10px;
  flex: 1;
}

.modules-card__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.modules-card__head strong {
  font-size: 18px;
}

.modules-card__foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  color: var(--muted);
  font-size: 13px;
}

.modules-empty,
.modules-loading {
  min-height: 220px;
}

@media (max-width: 960px) {
  .modules-shell {
    padding: 18px;
  }

  .modules-header,
  .modules-summary {
    flex-direction: column;
    align-items: flex-start;
  }

  .modules-header__actions {
    width: 100%;
    justify-content: flex-start;
  }

  .modules-user {
    width: 100%;
  }
}
</style>
