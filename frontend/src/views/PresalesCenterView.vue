<script setup lang="ts">
import { computed, nextTick, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowLeft, ChatDotRound, CirclePlus, Document, FolderOpened, Promotion, Refresh, Upload } from '@element-plus/icons-vue'
import { useRouter } from 'vue-router'

import {
  completePresalesTask,
  createFeishuSyncJob,
  createPresalesTask,
  fetchFeishuDeliveries,
  fetchFeishuRecipients,
  fetchFeishuSyncJobs,
  fetchPresalesArchives,
  fetchPresalesTask,
  fetchPresalesTasks,
  sendPresalesTaskToFeishu,
  updatePresalesTask,
} from '@/api/presales'
import { useAuthStore } from '@/stores/auth'
import type {
  FeishuDeliveryRecordItem,
  FeishuRecipientDepartmentItem,
  FeishuRecipientGroupItem,
  FeishuRecipientUserItem,
  FeishuSyncJobItem,
  PresalesArchiveRecordItem,
  PresalesTaskItem,
  PresalesTaskPayload,
} from '@/types/presales'
import { formatDateTime, formatRelativeTime } from '@/utils/time'

const router = useRouter()
const authStore = useAuthStore()

const activeTab = ref<'tasks' | 'archive' | 'deliveries' | 'sync'>('tasks')
const loading = reactive({
  tasks: false,
  archives: false,
  deliveries: false,
  syncJobs: false,
  taskSubmit: false,
  sending: false,
  syncing: false,
})

const tasks = ref<PresalesTaskItem[]>([])
const archives = ref<PresalesArchiveRecordItem[]>([])
const deliveries = ref<FeishuDeliveryRecordItem[]>([])
const syncJobs = ref<FeishuSyncJobItem[]>([])
const feishuDepartments = ref<FeishuRecipientDepartmentItem[]>([])
const feishuUsers = ref<FeishuRecipientUserItem[]>([])
const feishuGroups = ref<FeishuRecipientGroupItem[]>([])

const taskFilters = reactive({
  keyword: '',
  status: '',
  priority: '',
})

const archiveFilters = reactive({
  keyword: '',
  archive_type: '',
})

const deliveryFilters = reactive({
  delivery_status: '',
  target_type: '',
})

const taskDrawerVisible = ref(false)
const taskDialogVisible = ref(false)
const sendDialogVisible = ref(false)
const deliveryDrawerVisible = ref(false)
const memberTreeRef = ref()
const editingMode = ref<'create' | 'edit'>('create')
const selectedTask = ref<PresalesTaskItem | null>(null)
const selectedDelivery = ref<FeishuDeliveryRecordItem | null>(null)

const taskFormRef = ref()
const taskForm = reactive<PresalesTaskPayload>({
  task_title: '',
  task_type: 'follow_up',
  task_description: '',
  customer_name: '',
  priority: 'medium',
  due_at: null,
  next_follow_up_at: null,
  source_type: 'manual',
})

const sendFormRef = ref()
const sendForm = reactive({
  member_keys: [] as string[],
  group_chat_ids: [] as string[],
  message_text: '',
})

const taskRules = {
  task_title: [{ required: true, message: '请输入任务标题', trigger: 'blur' }],
}

const sendRules = computed(() => ({
  message_text: [{ required: true, message: '请输入消息内容', trigger: 'blur' }],
}))

const statusTagTypeMap: Record<string, 'success' | 'warning' | 'info' | 'danger'> = {
  pending: 'warning',
  in_progress: 'info',
  completed: 'success',
  cancelled: 'danger',
  reassigned: 'warning',
  archived: 'info',
}

const priorityTagTypeMap: Record<string, 'success' | 'warning' | 'info' | 'danger'> = {
  low: 'info',
  medium: 'success',
  high: 'warning',
  urgent: 'danger',
}

const deliveryTagTypeMap: Record<string, 'success' | 'warning' | 'info' | 'danger'> = {
  queued: 'warning',
  sent: 'success',
  partial: 'info',
  failed: 'danger',
  cancelled: 'info',
}

const syncStatusTagTypeMap: Record<string, 'success' | 'warning' | 'info' | 'danger'> = {
  pending: 'warning',
  running: 'info',
  completed: 'success',
  partial: 'warning',
  failed: 'danger',
}

const taskSummary = computed(() => {
  const total = tasks.value.length
  const inProgress = tasks.value.filter((item) => item.status === 'in_progress').length
  const pending = tasks.value.filter((item) => item.status === 'pending').length
  const overdue = tasks.value.filter((item) => item.next_follow_up_at && new Date(item.next_follow_up_at).getTime() < Date.now() && item.status !== 'completed').length
  return { total, inProgress, pending, overdue }
})

const canManagePresales = computed(() => authStore.hasPermission('presales_task.manage') || authStore.user?.is_superuser)
const canManageArchive = computed(() => authStore.hasPermission('presales_archive.manage') || authStore.user?.is_superuser)
const canManageFeishuSync = computed(() => authStore.hasPermission('feishu_sync.manage') || authStore.user?.is_superuser)
const canManageFeishuDelivery = computed(() => authStore.hasPermission('feishu_delivery.manage') || authStore.hasPermission('presales_task.manage') || authStore.user?.is_superuser)
const selectedFeishuGroups = computed(() => feishuGroups.value.filter((item) => sendForm.group_chat_ids.includes(item.chat_id)))
const feishuMemberTree = computed(() => {
  const nodeMap = new Map<string, { key: string; label: string; disabled: boolean; children: any[] }>()
  feishuDepartments.value.forEach((department) => {
    nodeMap.set(`dept-${department.id}`, {
      key: `dept-${department.id}`,
      label: department.name,
      disabled: true,
      children: [],
    })
  })

  const roots: Array<{ key: string; label: string; disabled: boolean; children: any[] }> = []
  feishuDepartments.value.forEach((department) => {
    const current = nodeMap.get(`dept-${department.id}`)
    if (!current) return
    if (department.parent_id && nodeMap.has(`dept-${department.parent_id}`)) {
      nodeMap.get(`dept-${department.parent_id}`)?.children.push(current)
    } else {
      roots.push(current)
    }
  })

  feishuUsers.value.forEach((user) => {
    const userNode = {
      key: `user-${user.id}`,
      label: user.display_name || user.username,
      disabled: !(user.feishu_open_id || user.feishu_user_id),
      isLeaf: true,
    }
    if (user.department_id && nodeMap.has(`dept-${user.department_id}`)) {
      nodeMap.get(`dept-${user.department_id}`)?.children.push(userNode)
    } else {
      roots.push({
        key: `orphan-${user.id}`,
        label: '未归属部门',
        disabled: true,
        children: [userNode],
      })
    }
  })

  return roots
})

function formatJson(value: Record<string, unknown> | null | undefined) {
  return JSON.stringify(value || {}, null, 2)
}

function formatZhDateTime(value?: string | null) {
  if (!value) return '未设置'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '未设置'
  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date)
}

function resolveUserLabel(user?: { display_name?: string; username?: string } | null) {
  if (!user) return '未分配'
  return user.display_name || user.username || '未命名成员'
}

function resolveTaskTypeLabel(value: string) {
  const map: Record<string, string> = {
    follow_up: '跟进任务',
    proposal_review: '方案评审',
    customer_revisit: '客户回访',
    internal_alignment: '内部对齐',
    materials_prepare: '材料准备',
    manual: '手工任务',
  }
  return map[value] || value
}

function resolveArchiveTypeLabel(value: string) {
  const map: Record<string, string> = {
    meeting_recording: '会议录音',
    demand_report: '需求分析报告',
    stage_summary: '阶段整理',
    solution_markdown: '方案 Markdown',
    solution_html: '方案 HTML',
    solution_pdf: '方案 PDF',
    attachment: '附件',
  }
  return map[value] || value
}

function resolveBusinessTypeLabel(value: string) {
  const map: Record<string, string> = {
    presales_task: '售前任务',
    demand_report: '需求分析报告',
    solution_result: '解决方案结果',
    archive_record: '归档记录',
  }
  return map[value] || value
}

function resolveSyncSourceLabel(value?: string | null) {
  const map: Record<string, string> = {
    feishu: '飞书同步',
    platform: '平台本地',
    manual: '人工维护',
  }
  return map[value || 'platform'] || value || '平台本地'
}

function resolveTaskStatusLabel(value: string) {
  const map: Record<string, string> = {
    pending: '待处理',
    in_progress: '进行中',
    completed: '已完成',
    cancelled: '已取消',
    reassigned: '已转派',
    archived: '已归档',
  }
  return map[value] || value
}

function resolvePriorityLabel(value: string) {
  const map: Record<string, string> = {
    low: '低',
    medium: '中',
    high: '高',
    urgent: '紧急',
  }
  return map[value] || value
}

function resolveDeliveryStatusLabel(value: string) {
  const map: Record<string, string> = {
    not_sent: '未发送',
    queued: '排队中',
    sent: '发送成功',
    partial: '部分成功',
    failed: '发送失败',
    cancelled: '已取消',
  }
  return map[value] || value
}

function resolveTargetTypeLabel(value: string) {
  const map: Record<string, string> = {
    user: '成员',
    group: '群聊',
    department_owner: '部门负责人',
  }
  return map[value] || value
}

function resolveSyncJobTypeLabel(value: string) {
  const map: Record<string, string> = {
    sync_departments: '同步部门',
    sync_users: '同步用户',
    full_sync: '全量同步',
    offboarding_reconcile: '离职对账',
  }
  return map[value] || value
}

function resolveSyncJobStatusLabel(value: string) {
  const map: Record<string, string> = {
    pending: '待执行',
    running: '执行中',
    completed: '已完成',
    partial: '部分完成',
    failed: '执行失败',
  }
  return map[value] || value
}

function resolveActivityTypeLabel(value: string) {
  const map: Record<string, string> = {
    created: '创建任务',
    updated: '更新任务',
    completed: '完成任务',
    reassigned: '转派任务',
    feishu_delivery: '发送飞书',
  }
  return map[value] || value
}

async function loadTasks() {
  loading.tasks = true
  try {
    const data = await fetchPresalesTasks({
      keyword: taskFilters.keyword || undefined,
      status: taskFilters.status || undefined,
      priority: taskFilters.priority || undefined,
    })
    tasks.value = data.items
  } finally {
    loading.tasks = false
  }
}

async function loadArchives() {
  loading.archives = true
  try {
    const data = await fetchPresalesArchives({
      keyword: archiveFilters.keyword || undefined,
      archive_type: archiveFilters.archive_type || undefined,
    })
    archives.value = data.items
  } finally {
    loading.archives = false
  }
}

async function loadDeliveries() {
  loading.deliveries = true
  try {
    const data = await fetchFeishuDeliveries({
      delivery_status: deliveryFilters.delivery_status || undefined,
      target_type: deliveryFilters.target_type || undefined,
    })
    deliveries.value = data.items
  } finally {
    loading.deliveries = false
  }
}

async function loadSyncJobs() {
  loading.syncJobs = true
  try {
    const data = await fetchFeishuSyncJobs()
    syncJobs.value = data.items
  } finally {
    loading.syncJobs = false
  }
}

async function loadFeishuRecipients() {
  try {
    const data = await fetchFeishuRecipients()
    feishuDepartments.value = data.departments
    feishuUsers.value = data.users
    feishuGroups.value = data.groups
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '飞书成员列表加载失败')
  }
}

async function loadAll() {
  await Promise.all([loadTasks(), loadArchives(), loadDeliveries(), loadSyncJobs(), loadFeishuRecipients()])
}

async function openTaskDrawer(taskId: string) {
  const data = await fetchPresalesTask(taskId)
  selectedTask.value = data.task
  taskDrawerVisible.value = true
}

function resetTaskForm() {
  taskForm.task_title = ''
  taskForm.task_type = 'follow_up'
  taskForm.task_description = ''
  taskForm.customer_name = ''
  taskForm.priority = 'medium'
  taskForm.due_at = null
  taskForm.next_follow_up_at = null
  taskForm.source_type = 'manual'
  taskForm.source_id = ''
  taskForm.source_version = null
  taskForm.owner_user_id = authStore.user?.id || null
  taskForm.owner_department_id = authStore.user?.department?.id || null
  taskForm.assignee_user_id = authStore.user?.id || null
  taskForm.collaborator_user_ids = []
  taskForm.status = 'pending'
  taskForm.payload_json = {}
}

function openCreateTaskDialog() {
  editingMode.value = 'create'
  resetTaskForm()
  taskDialogVisible.value = true
}

function openEditTaskDialog(task: PresalesTaskItem) {
  editingMode.value = 'edit'
  selectedTask.value = task
  taskForm.task_title = task.task_title
  taskForm.task_type = task.task_type
  taskForm.task_description = task.task_description
  taskForm.customer_name = task.customer_name
  taskForm.priority = task.priority
  taskForm.due_at = task.due_at
  taskForm.next_follow_up_at = task.next_follow_up_at
  taskForm.source_type = task.source_type
  taskForm.source_id = task.source_id
  taskForm.source_version = task.source_version
  taskForm.owner_user_id = task.owner_user?.id || authStore.user?.id || null
  taskForm.owner_department_id = task.owner_department?.id || authStore.user?.department?.id || null
  taskForm.assignee_user_id = task.assignee_user?.id || authStore.user?.id || null
  taskForm.collaborator_user_ids = task.collaborator_user_ids || []
  taskForm.status = task.status
  taskForm.payload_json = task.payload_json || {}
  taskDialogVisible.value = true
}

async function submitTaskForm() {
  await taskFormRef.value?.validate()
  loading.taskSubmit = true
  try {
    const payload = {
      ...taskForm,
      due_at: taskForm.due_at || null,
      next_follow_up_at: taskForm.next_follow_up_at || null,
    }
    if (editingMode.value === 'create') {
      await createPresalesTask(payload)
      ElMessage.success('售前任务已创建')
    } else if (selectedTask.value) {
      await updatePresalesTask(selectedTask.value.id, payload)
      ElMessage.success('售前任务已更新')
    }
    taskDialogVisible.value = false
    await loadTasks()
    if (selectedTask.value && editingMode.value === 'edit') {
      await openTaskDrawer(selectedTask.value.id)
    }
  } finally {
    loading.taskSubmit = false
  }
}

async function completeTask(task: PresalesTaskItem) {
  const result = await ElMessageBox.prompt('可以补充一行完成说明，留给团队后续追溯。', '完成售前任务', {
    confirmButtonText: '确认完成',
    cancelButtonText: '取消',
    inputPlaceholder: '例如：已与客户确认下周二演示，方案评审通过',
  }).catch(() => null)
  if (!result) return
  await completePresalesTask(task.id, result.value || '')
  ElMessage.success('任务已标记为完成')
  await loadTasks()
  if (selectedTask.value?.id === task.id) {
    await openTaskDrawer(task.id)
  }
}

function buildDefaultFeishuText(task: PresalesTaskItem) {
  const lines = [
    `售前任务：${task.task_title}`,
    task.customer_name ? `客户：${task.customer_name}` : '',
    task.task_description ? `说明：${task.task_description}` : '',
    task.next_follow_up_at ? `下次回访：${formatZhDateTime(task.next_follow_up_at)}` : '',
    task.due_at ? `到期时间：${formatZhDateTime(task.due_at)}` : '',
  ].filter(Boolean)
  return lines.join('\n')
}

function resetSendForm() {
  sendForm.member_keys = []
  sendForm.group_chat_ids = []
  sendForm.message_text = ''
}

function syncCheckedMemberKeys() {
  const checkedKeys = (memberTreeRef.value?.getCheckedKeys?.(false) || []) as string[]
  sendForm.member_keys = checkedKeys
    .filter((key) => typeof key === 'string' && key.startsWith('user-'))
    .map((key) => String(key).replace('user-', ''))
}

async function openSendDialog(task: PresalesTaskItem) {
  selectedTask.value = task
  const preferredUser = task.assignee_user?.feishu_open_id
    ? task.assignee_user
    : task.owner_user?.feishu_open_id
      ? task.owner_user
      : authStore.user?.feishu_open_id
        ? authStore.user
        : null
  resetSendForm()
  if (preferredUser) {
    const preferredRecipient = feishuUsers.value.find(
      (item) =>
        (preferredUser.feishu_open_id && item.feishu_open_id === preferredUser.feishu_open_id) ||
        (preferredUser.feishu_user_id && item.feishu_user_id === preferredUser.feishu_user_id) ||
        (item.platform_user_id && item.platform_user_id === preferredUser.id),
    )
    if (preferredRecipient) {
      sendForm.member_keys = [preferredRecipient.id]
    }
  }
  sendForm.message_text = buildDefaultFeishuText(task)
  sendDialogVisible.value = true
  await nextTick()
  memberTreeRef.value?.setCheckedKeys?.(sendForm.member_keys.map((id) => `user-${id}`), false)
}

async function submitSendDialog() {
  if (!selectedTask.value) return
  await sendFormRef.value?.validate()
  if (!sendForm.member_keys.length && !sendForm.group_chat_ids.length) {
    ElMessage.warning('请至少选择一位成员或一个群聊')
    return
  }
  loading.sending = true
  try {
    const payloadBase = {
      message_type: 'interactive_card' as const,
      message_payload: {
        text: sendForm.message_text,
        title: selectedTask.value.task_title,
        summary: selectedTask.value.customer_name,
      },
    }

    let successCount = 0
    const failedTargets: string[] = []

    const selectedMembers = feishuUsers.value.filter((item) => sendForm.member_keys.includes(item.id))
    for (const member of selectedMembers) {
      const targetId = member.feishu_open_id || member.feishu_user_id || ''
      const targetName = member.display_name || member.username || '未命名成员'
      if (!targetId) {
        failedTargets.push(targetName)
        continue
      }
      try {
        await sendPresalesTaskToFeishu(selectedTask.value.id, {
          target_type: 'user',
          target_id: targetId,
          target_name: targetName,
          ...payloadBase,
        })
        successCount += 1
      } catch (error) {
        failedTargets.push(targetName)
        console.error(error)
      }
    }

    for (const group of selectedFeishuGroups.value) {
      try {
        await sendPresalesTaskToFeishu(selectedTask.value.id, {
          target_type: 'group',
          target_id: group.chat_id,
          target_name: group.name || '',
          ...payloadBase,
        })
        successCount += 1
      } catch (error) {
        failedTargets.push(group.name || group.chat_id)
        console.error(error)
      }
    }

    if (!successCount) {
      throw new Error(`飞书发送失败：${failedTargets.join('、') || '没有有效的发送对象'}`)
    }
    if (failedTargets.length) {
      ElMessage.warning(`已成功发送 ${successCount} 条，以下对象发送失败：${failedTargets.join('、')}`)
    } else {
      ElMessage.success(`已成功发送 ${successCount} 条飞书消息`)
    }
    sendDialogVisible.value = false
    await Promise.all([loadTasks(), loadDeliveries()])
    if (selectedTask.value) {
      await openTaskDrawer(selectedTask.value.id)
    }
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '飞书发送失败')
  } finally {
    loading.sending = false
  }
}

async function runSync(jobType: FeishuSyncJobItem['job_type']) {
  loading.syncing = true
  try {
    await createFeishuSyncJob(jobType)
    ElMessage.success('飞书同步任务已执行')
    await loadSyncJobs()
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '飞书同步失败')
  } finally {
    loading.syncing = false
  }
}

function openDeliveryDrawer(item: FeishuDeliveryRecordItem) {
  selectedDelivery.value = item
  deliveryDrawerVisible.value = true
}

onMounted(loadAll)
</script>

<template>
  <div class="presales-shell">
    <header class="presales-header panel-card">
      <div>
        <p class="section-title">Presales Center</p>
        <h1>售前闭环中心</h1>
        <p>承接需求分析、解决方案输出后的任务流转、飞书协同、资料归档和身份同步，先把内部售前闭环跑顺。</p>
      </div>
      <div class="presales-header__actions">
        <div class="presales-user panel-card">
          <strong>{{ authStore.displayName || '未登录用户' }}</strong>
          <p>{{ authStore.user?.department?.name || '未设置部门' }} · {{ resolveSyncSourceLabel(authStore.user?.sync_source) }}</p>
        </div>
        <el-button plain @click="loadAll">
          <el-icon><Refresh /></el-icon>
          刷新数据
        </el-button>
        <el-button type="primary" plain @click="router.push('/modules')">
          <el-icon><ArrowLeft /></el-icon>
          返回模块入口
        </el-button>
      </div>
    </header>

    <section class="presales-summary">
      <article class="summary-card panel-card">
        <span>任务总数</span>
        <strong>{{ taskSummary.total }}</strong>
        <p>当前售前任务池</p>
      </article>
      <article class="summary-card panel-card">
        <span>处理中</span>
        <strong>{{ taskSummary.inProgress }}</strong>
        <p>正在推进的任务</p>
      </article>
      <article class="summary-card panel-card">
        <span>待启动</span>
        <strong>{{ taskSummary.pending }}</strong>
        <p>尚未进入执行的任务</p>
      </article>
      <article class="summary-card panel-card summary-card--warning">
        <span>回访压力</span>
        <strong>{{ taskSummary.overdue }}</strong>
        <p>已到期或回访超时</p>
      </article>
    </section>

    <section class="presales-tabs panel-card">
      <el-tabs v-model="activeTab">
        <el-tab-pane label="售前任务" name="tasks">
          <div class="toolbar-row">
            <div class="toolbar-grid">
              <el-input v-model="taskFilters.keyword" placeholder="搜索任务标题、说明或客户" clearable />
              <el-select v-model="taskFilters.status" clearable placeholder="全部状态">
                <el-option label="待处理" value="pending" />
                <el-option label="进行中" value="in_progress" />
                <el-option label="已完成" value="completed" />
                <el-option label="已取消" value="cancelled" />
              </el-select>
              <el-select v-model="taskFilters.priority" clearable placeholder="全部优先级">
                <el-option label="低" value="low" />
                <el-option label="中" value="medium" />
                <el-option label="高" value="high" />
                <el-option label="紧急" value="urgent" />
              </el-select>
            </div>
            <div class="toolbar-actions">
              <el-button plain @click="loadTasks">查询任务</el-button>
              <el-button v-if="canManagePresales" type="primary" @click="openCreateTaskDialog">
                <el-icon><CirclePlus /></el-icon>
                新建任务
              </el-button>
            </div>
          </div>

          <el-table :data="tasks" v-loading="loading.tasks" class="presales-table" empty-text="暂无售前任务">
            <el-table-column label="任务" min-width="260">
              <template #default="{ row }">
                <div class="task-cell">
                  <strong>{{ row.task_title }}</strong>
                  <p>{{ row.customer_name || '未填写客户' }} · {{ resolveTaskTypeLabel(row.task_type) }}</p>
                </div>
              </template>
            </el-table-column>
            <el-table-column label="负责人" min-width="180">
              <template #default="{ row }">{{ resolveUserLabel(row.assignee_user || row.owner_user) }}</template>
            </el-table-column>
            <el-table-column label="状态" width="110">
              <template #default="{ row }">
                <el-tag :type="statusTagTypeMap[row.status] || 'info'" effect="light">{{ resolveTaskStatusLabel(row.status) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="优先级" width="100">
              <template #default="{ row }">
                <el-tag :type="priorityTagTypeMap[row.priority] || 'info'" effect="plain">{{ resolvePriorityLabel(row.priority) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="飞书状态" width="110">
              <template #default="{ row }">
                <el-tag :type="deliveryTagTypeMap[row.feishu_delivery_status] || 'info'" effect="plain">{{ resolveDeliveryStatusLabel(row.feishu_delivery_status) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="回访时间" min-width="160">
              <template #default="{ row }">{{ row.next_follow_up_at ? formatZhDateTime(row.next_follow_up_at) : '未安排' }}</template>
            </el-table-column>
            <el-table-column label="更新时间" min-width="160">
              <template #default="{ row }">{{ formatRelativeTime(row.updated_at) }}</template>
            </el-table-column>
            <el-table-column label="操作" width="260" fixed="right">
              <template #default="{ row }">
                <div class="row-actions">
                  <el-button text type="primary" @click="openTaskDrawer(row.id)">详情</el-button>
                  <el-button v-if="canManagePresales" text @click="openEditTaskDialog(row)">编辑</el-button>
                  <el-button v-if="canManageFeishuDelivery" text type="success" @click="openSendDialog(row)">发送飞书</el-button>
                  <el-button v-if="canManagePresales && row.status !== 'completed'" text type="warning" @click="completeTask(row)">完成</el-button>
                </div>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <el-tab-pane label="归档记录" name="archive">
          <div class="toolbar-row">
            <div class="toolbar-grid">
              <el-input v-model="archiveFilters.keyword" placeholder="搜索文件名、标题或客户" clearable />
              <el-select v-model="archiveFilters.archive_type" clearable placeholder="全部归档类型">
                <el-option label="会议录音" value="meeting_recording" />
                <el-option label="需求分析报告" value="demand_report" />
                <el-option label="阶段整理" value="stage_summary" />
                <el-option label="方案 PDF" value="solution_pdf" />
                <el-option label="附件" value="attachment" />
              </el-select>
            </div>
            <div class="toolbar-actions">
              <el-button plain @click="loadArchives">查询归档</el-button>
            </div>
          </div>

          <el-table :data="archives" v-loading="loading.archives" class="presales-table" empty-text="暂无归档记录">
            <el-table-column label="归档内容" min-width="280">
              <template #default="{ row }">
                <div class="task-cell">
                  <strong>{{ row.source_title }}</strong>
                  <p>{{ row.customer_name || '未关联客户' }} · {{ resolveArchiveTypeLabel(row.archive_type) }}</p>
                </div>
              </template>
            </el-table-column>
            <el-table-column label="文件名" min-width="220" prop="file_name" />
            <el-table-column label="存储" min-width="120">
              <template #default="{ row }">{{ row.storage_provider }}<span v-if="row.feishu_shared"> · 已分享</span></template>
            </el-table-column>
            <el-table-column label="上传人" min-width="120">
              <template #default="{ row }">{{ resolveUserLabel(row.uploaded_by) }}</template>
            </el-table-column>
            <el-table-column label="创建时间" min-width="160">
              <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <el-tab-pane label="飞书发送" name="deliveries">
          <div class="toolbar-row">
            <div class="toolbar-grid">
              <el-select v-model="deliveryFilters.delivery_status" clearable placeholder="全部发送状态">
                <el-option label="排队中" value="queued" />
                <el-option label="发送成功" value="sent" />
                <el-option label="部分成功" value="partial" />
                <el-option label="发送失败" value="failed" />
              </el-select>
              <el-select v-model="deliveryFilters.target_type" clearable placeholder="全部目标类型">
                <el-option label="用户" value="user" />
                <el-option label="群" value="group" />
              </el-select>
            </div>
            <div class="toolbar-actions">
              <el-button plain @click="loadDeliveries">刷新发送记录</el-button>
            </div>
          </div>

          <el-table :data="deliveries" v-loading="loading.deliveries" class="presales-table" empty-text="暂无飞书发送记录">
            <el-table-column label="业务对象" min-width="220">
              <template #default="{ row }">
                <div class="task-cell">
                  <strong>{{ resolveBusinessTypeLabel(row.business_type) }}</strong>
                  <p>{{ row.business_id }}</p>
                </div>
              </template>
            </el-table-column>
            <el-table-column label="发送目标" min-width="220">
              <template #default="{ row }">
                <div class="task-cell">
                  <strong>{{ row.target_name || row.target_id }}</strong>
                  <p>{{ resolveTargetTypeLabel(row.target_type) }} · {{ row.target_id }}</p>
                </div>
              </template>
            </el-table-column>
            <el-table-column label="状态" width="110">
              <template #default="{ row }">
                <el-tag :type="deliveryTagTypeMap[row.delivery_status] || 'info'" effect="light">{{ resolveDeliveryStatusLabel(row.delivery_status) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作人" min-width="120">
              <template #default="{ row }">{{ resolveUserLabel(row.operator_user) }}</template>
            </el-table-column>
            <el-table-column label="时间" min-width="160">
              <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
            </el-table-column>
            <el-table-column label="操作" width="120" fixed="right">
              <template #default="{ row }">
                <el-button text type="primary" @click="openDeliveryDrawer(row)">查看详情</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <el-tab-pane label="身份同步" name="sync">
          <div class="sync-actions panel-card">
            <div>
              <strong>飞书身份与部门同步</strong>
              <p>用于同步飞书用户、部门以及离职状态，当前建议先通过白名单部门控制同步范围。</p>
            </div>
            <div class="toolbar-actions">
              <el-button :loading="loading.syncing" plain @click="runSync('sync_departments')">
                <el-icon><FolderOpened /></el-icon>
                同步部门
              </el-button>
              <el-button :loading="loading.syncing" plain @click="runSync('sync_users')">
                <el-icon><ChatDotRound /></el-icon>
                同步用户
              </el-button>
              <el-button v-if="canManageFeishuSync" :loading="loading.syncing" type="primary" @click="runSync('full_sync')">
                <el-icon><Upload /></el-icon>
                全量同步
              </el-button>
            </div>
          </div>

          <el-table :data="syncJobs" v-loading="loading.syncJobs" class="presales-table" empty-text="暂无同步任务">
            <el-table-column label="任务类型" min-width="160">
              <template #default="{ row }">{{ resolveSyncJobTypeLabel(row.job_type) }}</template>
            </el-table-column>
            <el-table-column label="状态" width="110">
              <template #default="{ row }">
                <el-tag :type="syncStatusTagTypeMap[row.status] || 'info'" effect="plain">{{ resolveSyncJobStatusLabel(row.status) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="部门数" width="90" prop="synced_department_count" />
            <el-table-column label="用户数" width="90" prop="synced_user_count" />
            <el-table-column label="停用数" width="90" prop="disabled_user_count" />
            <el-table-column label="错误数" width="90" prop="error_count" />
            <el-table-column label="执行人" min-width="120">
              <template #default="{ row }">{{ resolveUserLabel(row.operator_user) }}</template>
            </el-table-column>
            <el-table-column label="创建时间" min-width="160">
              <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
            </el-table-column>
            <el-table-column label="摘要" min-width="260">
              <template #default="{ row }">
                <span>{{ row.summary_json && Object.keys(row.summary_json).length ? formatJson(row.summary_json) : row.error_message || '无摘要' }}</span>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
      </el-tabs>
    </section>

    <el-dialog v-model="taskDialogVisible" :title="editingMode === 'create' ? '新建售前任务' : '编辑售前任务'" width="620px">
      <el-form ref="taskFormRef" :model="taskForm" :rules="taskRules" label-width="96px">
        <el-form-item label="任务标题" prop="task_title">
          <el-input v-model="taskForm.task_title" placeholder="例如：常州园区方案回访与演示安排" />
        </el-form-item>
        <el-form-item label="任务类型">
          <el-select v-model="taskForm.task_type">
            <el-option label="跟进任务" value="follow_up" />
            <el-option label="方案评审" value="proposal_review" />
            <el-option label="客户回访" value="customer_revisit" />
            <el-option label="内部对齐" value="internal_alignment" />
            <el-option label="材料准备" value="materials_prepare" />
            <el-option label="手工任务" value="manual" />
          </el-select>
        </el-form-item>
        <el-form-item label="客户名称">
          <el-input v-model="taskForm.customer_name" placeholder="例如：常州大通工业园" />
        </el-form-item>
        <el-form-item label="优先级">
          <el-select v-model="taskForm.priority">
            <el-option label="低" value="low" />
            <el-option label="中" value="medium" />
            <el-option label="高" value="high" />
            <el-option label="紧急" value="urgent" />
          </el-select>
        </el-form-item>
        <el-form-item label="到期时间">
          <el-date-picker v-model="taskForm.due_at" type="datetime" placeholder="可选" value-format="YYYY-MM-DDTHH:mm:ssZ" />
        </el-form-item>
        <el-form-item label="回访时间">
          <el-date-picker v-model="taskForm.next_follow_up_at" type="datetime" placeholder="可选" value-format="YYYY-MM-DDTHH:mm:ssZ" />
        </el-form-item>
        <el-form-item label="任务说明">
          <el-input v-model="taskForm.task_description" type="textarea" :rows="5" placeholder="补充这次跟进要完成的关键动作、客户关注点和输出物。" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="taskDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="loading.taskSubmit" @click="submitTaskForm">{{ editingMode === 'create' ? '创建任务' : '保存修改' }}</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="sendDialogVisible" title="发送到飞书" width="620px">
        <el-form ref="sendFormRef" :model="sendForm" :rules="sendRules" label-width="98px">
          <el-alert
            title="成员和群聊可以同时选择，系统会分别发送并记录结果。"
            type="info"
            :closable="false"
            show-icon
            class="send-dialog-tip"
          />
          <el-form-item label="选择成员">
            <div class="member-tree-picker">
              <el-tree
                ref="memberTreeRef"
                :data="feishuMemberTree"
                node-key="key"
                show-checkbox
                check-on-click-node
                default-expand-all
                :props="{ label: 'label', children: 'children', disabled: 'disabled' }"
                @check="syncCheckedMemberKeys"
              />
            </div>
          </el-form-item>
          <el-form-item label="选择群聊">
            <el-select
              v-model="sendForm.group_chat_ids"
              placeholder="可多选群聊"
              filterable
              clearable
              multiple
              collapse-tags
              collapse-tags-tooltip
            >
              <el-option
                v-for="item in feishuGroups"
                :key="item.chat_id"
                :label="item.name"
                :value="item.chat_id"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="附加说明" prop="message_text">
            <el-input
              v-model="sendForm.message_text"
              type="textarea"
              :rows="8"
              placeholder="这段内容会作为卡片里的补充说明展示给收件人。"
            />
          </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="sendDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="loading.sending" @click="submitSendDialog">
          <el-icon><Promotion /></el-icon>
          发送消息
        </el-button>
      </template>
    </el-dialog>

    <el-drawer v-model="taskDrawerVisible" size="720px" :with-header="false">
      <div v-if="selectedTask" class="drawer-shell">
        <div class="drawer-head">
          <div>
            <p class="section-title">任务详情</p>
            <h2>{{ selectedTask.task_title }}</h2>
            <p>{{ selectedTask.customer_name || '未填写客户' }} · {{ resolveTaskTypeLabel(selectedTask.task_type) }}</p>
          </div>
          <div class="drawer-head__actions">
            <el-button v-if="canManagePresales" plain @click="openEditTaskDialog(selectedTask)">编辑任务</el-button>
            <el-button v-if="canManageFeishuDelivery" type="primary" plain @click="openSendDialog(selectedTask)">发送飞书</el-button>
          </div>
        </div>

        <div class="drawer-grid">
          <div class="panel-card drawer-card">
            <strong>任务概览</strong>
            <dl class="detail-list">
              <div><dt>状态</dt><dd><el-tag :type="statusTagTypeMap[selectedTask.status] || 'info'">{{ resolveTaskStatusLabel(selectedTask.status) }}</el-tag></dd></div>
              <div><dt>优先级</dt><dd><el-tag :type="priorityTagTypeMap[selectedTask.priority] || 'info'" effect="plain">{{ resolvePriorityLabel(selectedTask.priority) }}</el-tag></dd></div>
              <div><dt>负责人</dt><dd>{{ resolveUserLabel(selectedTask.assignee_user || selectedTask.owner_user) }}</dd></div>
              <div><dt>下次回访</dt><dd>{{ selectedTask.next_follow_up_at ? formatZhDateTime(selectedTask.next_follow_up_at) : '未安排' }}</dd></div>
              <div><dt>飞书状态</dt><dd>{{ resolveDeliveryStatusLabel(selectedTask.feishu_delivery_status) }}</dd></div>
            </dl>
          </div>
          <div class="panel-card drawer-card">
            <strong>任务说明</strong>
            <p class="drawer-text">{{ selectedTask.task_description || '暂无补充说明。' }}</p>
          </div>
        </div>

        <section class="panel-card drawer-card">
          <div class="section-head">
            <strong>任务活动</strong>
            <span>{{ selectedTask.activities.length }} 条</span>
          </div>
          <div v-if="!selectedTask.activities.length" class="empty-inline">暂无活动记录</div>
          <div v-else class="activity-list">
            <article v-for="item in selectedTask.activities" :key="item.id" class="activity-item">
              <div class="activity-item__meta">
                <strong>{{ item.summary }}</strong>
                <span>{{ formatZhDateTime(item.created_at) }}</span>
              </div>
              <p>{{ resolveUserLabel(item.operator_user) }} · {{ resolveActivityTypeLabel(item.activity_type) }}</p>
            </article>
          </div>
        </section>

        <section v-if="selectedTask.latest_feishu_delivery" class="panel-card drawer-card">
          <div class="section-head">
            <strong>最近一次飞书发送</strong>
            <el-tag :type="deliveryTagTypeMap[selectedTask.latest_feishu_delivery.delivery_status] || 'info'">{{ resolveDeliveryStatusLabel(selectedTask.latest_feishu_delivery.delivery_status) }}</el-tag>
          </div>
          <pre class="json-card">{{ formatJson(selectedTask.latest_feishu_delivery.response_payload) }}</pre>
        </section>
      </div>
    </el-drawer>

    <el-drawer v-model="deliveryDrawerVisible" size="680px" :with-header="false">
      <div v-if="selectedDelivery" class="drawer-shell">
        <div class="drawer-head">
          <div>
            <p class="section-title">飞书发送详情</p>
            <h2>{{ selectedDelivery.target_name || selectedDelivery.target_id }}</h2>
            <p>{{ resolveBusinessTypeLabel(selectedDelivery.business_type) }} · {{ formatZhDateTime(selectedDelivery.created_at) }}</p>
          </div>
        </div>
        <section class="panel-card drawer-card">
          <div class="section-head">
            <strong>请求载荷</strong>
            <el-tag :type="deliveryTagTypeMap[selectedDelivery.delivery_status] || 'info'">{{ resolveDeliveryStatusLabel(selectedDelivery.delivery_status) }}</el-tag>
          </div>
          <pre class="json-card">{{ formatJson(selectedDelivery.request_payload) }}</pre>
        </section>
        <section class="panel-card drawer-card">
          <div class="section-head">
            <strong>响应结果</strong>
            <span>{{ selectedDelivery.error_message || '调用成功' }}</span>
          </div>
          <pre class="json-card">{{ formatJson(selectedDelivery.response_payload) }}</pre>
        </section>
      </div>
    </el-drawer>
  </div>
</template>

<style scoped>
.presales-shell {
  display: flex;
  flex-direction: column;
  gap: 18px;
  padding: 24px;
}

.presales-header,
.presales-tabs,
.summary-card,
.sync-actions,
.drawer-card {
  padding: 22px 24px;
}

.presales-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 18px;
}

.presales-header h1 {
  margin: 8px 0 10px;
  font-size: 34px;
}

.presales-header p,
.summary-card p,
.sync-actions p,
.task-cell p,
.drawer-text {
  margin: 0;
  color: var(--muted);
  line-height: 1.7;
}

.presales-header__actions {
  display: flex;
  align-items: stretch;
  justify-content: flex-end;
  gap: 12px;
  flex-wrap: wrap;
}

.presales-user {
  min-width: 240px;
  padding: 14px 16px;
  border-radius: 18px;
}

.presales-summary {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 16px;
}

.summary-card {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.summary-card span {
  color: var(--muted);
  font-size: 13px;
}

.summary-card strong {
  font-size: 30px;
  line-height: 1;
}

.summary-card--warning {
  border-color: rgba(207, 115, 24, 0.16);
}

.toolbar-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 18px;
}

.toolbar-grid {
  flex: 1;
  display: grid;
  grid-template-columns: minmax(220px, 2fr) repeat(2, minmax(140px, 1fr));
  gap: 12px;
}

.toolbar-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.presales-table {
  width: 100%;
}

.task-cell {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.task-cell strong {
  font-size: 14px;
  line-height: 1.5;
}

.row-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.member-tree-picker {
  width: 100%;
  max-height: 320px;
  overflow: auto;
  padding: 10px 12px;
  border-radius: 16px;
  border: 1px solid rgba(24, 50, 71, 0.12);
  background: rgba(255, 255, 255, 0.82);
}

.send-dialog-tip {
  margin-bottom: 18px;
}

.sync-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 18px;
}

.drawer-shell {
  display: flex;
  flex-direction: column;
  gap: 18px;
  padding: 20px;
}

.drawer-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.drawer-head h2 {
  margin: 8px 0 10px;
  font-size: 24px;
}

.drawer-head__actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.drawer-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.detail-list {
  display: grid;
  gap: 10px;
  margin: 14px 0 0;
}

.detail-list div {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.detail-list dt {
  color: var(--muted);
}

.detail-list dd {
  margin: 0;
  text-align: right;
}

.section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.activity-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.activity-item {
  padding: 12px 14px;
  border-radius: 14px;
  background: rgba(17, 87, 133, 0.05);
}

.activity-item__meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 6px;
}

.activity-item p,
.empty-inline {
  margin: 0;
  color: var(--muted);
}

.json-card {
  margin: 0;
  padding: 14px 16px;
  border-radius: 16px;
  background: rgba(11, 33, 54, 0.92);
  color: #d4e8ff;
  font-size: 12px;
  line-height: 1.6;
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-word;
}

@media (max-width: 960px) {
  .presales-header,
  .toolbar-row,
  .sync-actions,
  .drawer-head {
    flex-direction: column;
  }

  .toolbar-grid,
  .drawer-grid {
    grid-template-columns: 1fr;
  }
}
</style>
