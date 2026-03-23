<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
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
const hasSearched = ref(false)
const filters = reactive({
  keyword: '',
  action: '',
  resource_type: '',
  actor_id: '',
  date_range: [] as [Date, Date] | [],
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
  if (!Array.isArray(filters.date_range) || filters.date_range.length !== 2) {
    ElMessage.warning('请先选择日期范围，再执行审计日志查询')
    return
  }
  loading.value = true
  try {
    const [startDate, endDate] = filters.date_range
    const data = await fetchAuditLogs({
      start_date: formatDateParam(startDate),
      end_date: formatDateParam(endDate),
      keyword: filters.keyword || undefined,
      action: filters.action || undefined,
      resource_type: filters.resource_type || undefined,
      actor_id: filters.actor_id || undefined,
    })
    logs.value = data.items
    hasSearched.value = true
  } finally {
    loading.value = false
  }
}

function resetFilters() {
  filters.keyword = ''
  filters.action = ''
  filters.resource_type = ''
  filters.actor_id = ''
  filters.date_range = []
  logs.value = []
  hasSearched.value = false
}

function formatDateParam(date: Date) {
  const year = date.getFullYear()
  const month = `${date.getMonth() + 1}`.padStart(2, '0')
  const day = `${date.getDate()}`.padStart(2, '0')
  return `${year}-${month}-${day}`
}

onMounted(async () => {
  await loadUsers()
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
      <div class="audit-filters__intro">
        <strong>检索条件</strong>
        <p>请先选择日期范围，再按动作、资源类型、操作人和关键词缩小结果范围。</p>
      </div>
      <div class="audit-filters__layout">
        <div class="audit-filter-field audit-filter-field--wide">
          <label>日期范围</label>
          <el-date-picker
            v-model="filters.date_range"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            value-format=""
            class="audit-filters__date"
          />
        </div>
        <div class="audit-filter-field audit-filter-field--full">
          <label>关键词</label>
          <el-input v-model="filters.keyword" placeholder="搜索动作、资源、操作者或细节" clearable class="audit-filters__keyword" />
        </div>
        <div class="audit-filter-grid">
          <div class="audit-filter-field">
            <label>动作类型</label>
            <el-select v-model="filters.action" clearable placeholder="全部动作">
              <el-option v-for="item in actionOptions" :key="item" :label="item" :value="item" />
            </el-select>
          </div>
          <div class="audit-filter-field">
            <label>资源类型</label>
            <el-select v-model="filters.resource_type" clearable placeholder="全部资源">
              <el-option v-for="item in resourceTypeOptions" :key="item" :label="item" :value="item" />
            </el-select>
          </div>
          <div class="audit-filter-field">
            <label>操作人</label>
            <el-select v-model="filters.actor_id" clearable placeholder="全部人员" :loading="usersLoading">
              <el-option v-for="item in users" :key="item.id" :label="item.display_name || item.username" :value="String(item.id)" />
            </el-select>
          </div>
        </div>
        <div class="audit-filters__actions">
          <el-button type="primary" :disabled="!filters.date_range.length" @click="loadLogs">查询日志</el-button>
          <el-button @click="resetFilters">重置</el-button>
        </div>
      </div>
    </section>

    <section class="audit-summary panel-card">
      <span v-if="hasSearched">共 {{ logs.length }} 条日志</span>
      <span v-else>请先选择日期范围并执行查询</span>
      <span v-if="hasSearched && logs.length">最新时间：{{ formatDateTime(logs[0].created_at) }}</span>
    </section>

    <section class="audit-content panel-card" v-loading="loading">
      <div v-if="!hasSearched" class="audit-empty">
        审计日志默认不直接展示，请先选择日期范围，再结合动作、资源和操作人进行检索。
      </div>
      <div v-else-if="!logs.length" class="audit-empty">
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
.audit-filters__actions,
.audit-summary {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.audit-filters {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.audit-filters__intro strong {
  font-size: 16px;
}

.audit-filters__intro p {
  margin: 6px 0 0;
  color: var(--muted);
  font-size: 13px;
}

.audit-filters__layout {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.audit-filter-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
}

.audit-filter-field {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-width: 0;
}

.audit-filter-field label {
  font-size: 13px;
  font-weight: 600;
  color: var(--muted);
}

.audit-filter-field--wide {
  max-width: 460px;
}

.audit-filter-field--full {
  width: 100%;
}

.audit-filters__keyword {
  width: 100%;
}

.audit-filters__date {
  width: 100%;
}

.audit-filters__actions {
  justify-content: flex-end;
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
  .audit-item__meta {
    flex-direction: column;
    align-items: stretch;
  }

  .audit-filter-grid {
    grid-template-columns: minmax(0, 1fr);
  }

  .audit-filters__actions {
    justify-content: flex-start;
  }
}
</style>
