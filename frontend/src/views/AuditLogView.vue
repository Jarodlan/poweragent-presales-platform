<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ArrowLeft, Refresh } from '@element-plus/icons-vue'
import { useRouter } from 'vue-router'

import { fetchAuditLogs, fetchUsers } from '@/api/admin'
import type { AuditLogItem, UserItem } from '@/types/admin'
import { formatDateTime, formatRelativeTime } from '@/utils/time'

const router = useRouter()
const loading = ref(false)
const usersLoading = ref(false)
const logs = ref<AuditLogItem[]>([])
const users = ref<UserItem[]>([])
const filters = reactive({
  keyword: '',
  action: '',
  resource_type: '',
  actor_id: '',
})

const actionOptions = [
  'auth.login',
  'auth.logout',
  'user.create',
  'user.update',
  'user.reset_password',
  'user.archive',
  'user.restore',
  'role.create',
  'role.update',
  'role.delete',
  'department.create',
  'department.update',
  'department.delete',
]

const resourceTypeOptions = ['user', 'role', 'department']

const groupedLogs = computed(() => {
  const map = new Map<string, AuditLogItem[]>()
  logs.value.forEach((item) => {
    const key = formatDateTime(item.created_at).split(' ')[0]
    if (!map.has(key)) map.set(key, [])
    map.get(key)?.push(item)
  })
  return Array.from(map.entries()).map(([date, items]) => ({ date, items }))
})

async function loadUsers() {
  usersLoading.value = true
  try {
    const data = await fetchUsers(true)
    users.value = data.items
  } finally {
    usersLoading.value = false
  }
}

async function loadLogs() {
  loading.value = true
  try {
    const data = await fetchAuditLogs({
      keyword: filters.keyword || undefined,
      action: filters.action || undefined,
      resource_type: filters.resource_type || undefined,
      actor_id: filters.actor_id || undefined,
    })
    logs.value = data.items
  } finally {
    loading.value = false
  }
}

function resetFilters() {
  filters.keyword = ''
  filters.action = ''
  filters.resource_type = ''
  filters.actor_id = ''
  loadLogs()
}

onMounted(async () => {
  await Promise.all([loadUsers(), loadLogs()])
})
</script>

<template>
  <div class="audit-shell">
    <header class="audit-header panel-card">
      <div>
        <p class="section-title">Audit Center</p>
        <h1>审计日志中心</h1>
        <p>查看账户、角色、部门等关键管理动作，支撑安全审计与问题追踪。</p>
      </div>
      <div class="audit-header__actions">
        <el-button plain @click="loadLogs">
          <el-icon><Refresh /></el-icon>
          刷新日志
        </el-button>
        <el-button type="primary" plain @click="router.push('/modules')">
          <el-icon><ArrowLeft /></el-icon>
          返回模块入口
        </el-button>
      </div>
    </header>

    <section class="audit-filters panel-card">
      <el-input v-model="filters.keyword" placeholder="搜索动作、资源、操作者或细节" clearable class="audit-filters__keyword" />
      <el-select v-model="filters.action" clearable placeholder="动作类型">
        <el-option v-for="item in actionOptions" :key="item" :label="item" :value="item" />
      </el-select>
      <el-select v-model="filters.resource_type" clearable placeholder="资源类型">
        <el-option v-for="item in resourceTypeOptions" :key="item" :label="item" :value="item" />
      </el-select>
      <el-select v-model="filters.actor_id" clearable placeholder="操作人" :loading="usersLoading">
        <el-option v-for="item in users" :key="item.id" :label="item.display_name || item.username" :value="String(item.id)" />
      </el-select>
      <div class="audit-filters__actions">
        <el-button type="primary" @click="loadLogs">筛选</el-button>
        <el-button @click="resetFilters">重置</el-button>
      </div>
    </section>

    <section class="audit-summary panel-card">
      <span>共 {{ logs.length }} 条日志</span>
      <span v-if="logs.length">最新时间：{{ formatDateTime(logs[0].created_at) }}</span>
    </section>

    <section class="audit-content panel-card" v-loading="loading">
      <div v-if="!logs.length" class="audit-empty">
        暂无匹配日志，换个筛选条件试试。
      </div>
      <div v-else class="audit-groups">
        <section v-for="group in groupedLogs" :key="group.date" class="audit-group">
          <div class="audit-group__head">
            <strong>{{ group.date }}</strong>
            <span>{{ group.items.length }} 条</span>
          </div>
          <article v-for="item in group.items" :key="item.id" class="audit-item">
            <div class="audit-item__meta">
              <div>
                <strong>{{ item.action }}</strong>
                <p>{{ item.actor_name }}（{{ item.actor_username }}） · {{ formatRelativeTime(item.created_at) }}</p>
              </div>
              <el-tag type="info" effect="plain">{{ item.resource_type }} / {{ item.resource_id }}</el-tag>
            </div>
            <p class="audit-item__time">{{ formatDateTime(item.created_at) }}</p>
            <pre class="audit-item__detail">{{ JSON.stringify(item.detail_json || {}, null, 2) }}</pre>
          </article>
        </section>
      </div>
    </section>
  </div>
</template>

<style scoped>
.audit-shell {
  display: flex;
  flex-direction: column;
  gap: 18px;
  padding: 24px;
}

.audit-header,
.audit-filters,
.audit-summary,
.audit-content {
  padding: 20px 22px;
}

.audit-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;
}

.audit-header h1 {
  margin: 6px 0 10px;
  font-size: 32px;
}

.audit-header p,
.audit-summary span,
.audit-empty {
  color: var(--muted);
}

.audit-header__actions,
.audit-filters,
.audit-filters__actions,
.audit-summary {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.audit-filters__keyword {
  min-width: 280px;
  flex: 1;
}

.audit-groups {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.audit-group__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.audit-item {
  padding: 16px 18px;
  border-radius: 18px;
  border: 1px solid rgba(24, 50, 71, 0.08);
  background: rgba(255, 255, 255, 0.7);
}

.audit-item + .audit-item {
  margin-top: 12px;
}

.audit-item__meta {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.audit-item__meta strong {
  display: block;
  margin-bottom: 6px;
}

.audit-item__meta p,
.audit-item__time {
  margin: 0;
  color: var(--muted);
}

.audit-item__time {
  margin-top: 10px;
  font-size: 13px;
}

.audit-item__detail {
  margin: 12px 0 0;
  padding: 12px;
  border-radius: 14px;
  background: rgba(15, 93, 140, 0.06);
  color: var(--text);
  overflow: auto;
  font-family: 'SFMono-Regular', 'JetBrains Mono', Consolas, monospace;
  font-size: 12px;
  line-height: 1.6;
}

@media (max-width: 1080px) {
  .audit-header,
  .audit-filters,
  .audit-item__meta {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
