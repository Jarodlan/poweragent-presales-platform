<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowLeft, CirclePlus, CopyDocument, Key, Refresh, View } from '@element-plus/icons-vue'
import { useRouter } from 'vue-router'

import {
  archiveUser,
  createDepartment,
  createRole,
  createUser,
  deleteDepartment,
  deleteRole,
  fetchDepartments,
  fetchUserActivity,
  fetchPermissions,
  fetchRoles,
  fetchUsers,
  resetUserPassword,
  restoreUser,
  updateDepartment,
  updateRole,
  updateUser,
} from '@/api/admin'
import { useAuthStore } from '@/stores/auth'
import type {
  AuditLogItem,
  DepartmentItem,
  DepartmentPayload,
  PermissionItem,
  RoleItem,
  RolePayload,
  UserConversationActivityItem,
  UserItem,
  UserPayload,
  UserTaskActivityItem,
} from '@/types/admin'
import { formatDateTime, formatRelativeTime } from '@/utils/time'

const router = useRouter()
const authStore = useAuthStore()

const loading = reactive({
  users: false,
  roles: false,
  departments: false,
  permissions: false,
})

const users = ref<UserItem[]>([])
const roles = ref<RoleItem[]>([])
const departments = ref<DepartmentItem[]>([])
const permissions = ref<PermissionItem[]>([])
const loginHistory = ref<AuditLogItem[]>([])
const operationHistory = ref<AuditLogItem[]>([])
const conversationHistory = ref<UserConversationActivityItem[]>([])
const taskHistory = ref<UserTaskActivityItem[]>([])
const userActivityLoading = ref(false)
const activeTab = ref<'users' | 'roles' | 'departments'>('users')
const searchKeyword = ref('')
const userViewMode = ref<'active' | 'recycle'>('active')

const userDialogVisible = ref(false)
const roleDialogVisible = ref(false)
const departmentDialogVisible = ref(false)
const userDetailVisible = ref(false)
const userDetailTab = ref<'overview' | 'activity' | 'business'>('overview')
const userDialogMode = ref<'create' | 'edit'>('create')
const roleDialogMode = ref<'create' | 'edit'>('create')
const departmentDialogMode = ref<'create' | 'edit'>('create')
const editingUserId = ref<number | null>(null)
const editingRoleId = ref<number | null>(null)
const editingDepartmentId = ref<number | null>(null)
const selectedUser = ref<UserItem | null>(null)

const userFormRef = ref()
const roleFormRef = ref()
const departmentFormRef = ref()

const userForm = reactive<UserPayload>({
  username: '',
  email: '',
  display_name: '',
  employee_no: '',
  phone_number: '',
  job_title: '',
  department_id: null,
  account_status: 'active',
  data_scope: 'self',
  force_password_change: true,
  is_active: true,
  is_staff: false,
  remarks: '',
  password: '',
  role_ids: [],
})

const roleForm = reactive<RolePayload>({
  code: '',
  name: '',
  description: '',
  data_scope: 'self',
  permission_codes: [],
})

const departmentForm = reactive<DepartmentPayload>({
  name: '',
  code: '',
  description: '',
  status: 'active',
  parent_id: null,
  sort_order: 0,
})

const userRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  display_name: [{ required: true, message: '请输入显示名称', trigger: 'blur' }],
  password: [{ required: true, message: '请设置初始密码', trigger: 'blur' }],
}

const roleRules = {
  code: [{ required: true, message: '请输入角色编码', trigger: 'blur' }],
  name: [{ required: true, message: '请输入角色名称', trigger: 'blur' }],
}

const departmentRules = {
  name: [{ required: true, message: '请输入部门名称', trigger: 'blur' }],
  code: [{ required: true, message: '请输入部门编码', trigger: 'blur' }],
}

const canManageUsers = computed(() => authStore.canManageUsers)
const canManageRoles = computed(() => authStore.canManageRoles)
const canManageDepartments = computed(() => authStore.canManageDepartments)
const visibleTabs = computed(() => {
  const items: Array<{ label: string; name: 'users' | 'roles' | 'departments' }> = []
  if (canManageUsers.value) items.push({ label: '用户管理', name: 'users' })
  if (canManageRoles.value) items.push({ label: '角色管理', name: 'roles' })
  if (canManageDepartments.value) items.push({ label: '部门管理', name: 'departments' })
  return items
})

const permissionGroups = computed(() => {
  const map = new Map<string, PermissionItem[]>()
  permissions.value.forEach((item) => {
    if (!map.has(item.module)) map.set(item.module, [])
    map.get(item.module)?.push(item)
  })
  return Array.from(map.entries()).map(([module, items]) => ({ module, items }))
})

const filteredUsers = computed(() => {
  const keyword = searchKeyword.value.trim().toLowerCase()
  if (!keyword) return users.value
  return users.value.filter((item) =>
    [item.username, item.display_name, item.email, item.department?.name || '', item.employee_no || '']
      .join(' ')
      .toLowerCase()
      .includes(keyword),
  )
})

const activeUsers = computed(() => filteredUsers.value.filter((item) => item.account_status !== 'archived'))
const recycledUsers = computed(() => filteredUsers.value.filter((item) => item.account_status === 'archived'))
const displayedUsers = computed(() => (userViewMode.value === 'active' ? activeUsers.value : recycledUsers.value))

const filteredRoles = computed(() => {
  const keyword = searchKeyword.value.trim().toLowerCase()
  if (!keyword) return roles.value
  return roles.value.filter((item) => [item.code, item.name, item.description].join(' ').toLowerCase().includes(keyword))
})

const filteredDepartments = computed(() => {
  const keyword = searchKeyword.value.trim().toLowerCase()
  if (!keyword) return departments.value
  return departments.value.filter((item) => [item.name, item.code, item.parent_name || ''].join(' ').toLowerCase().includes(keyword))
})

const departmentTree = computed(() => {
  const map = new Map<number, DepartmentItem & { children?: Array<DepartmentItem & { children?: DepartmentItem[] }> }>()
  filteredDepartments.value.forEach((item) => {
    map.set(item.id, { ...item, children: [] })
  })

  const roots: Array<DepartmentItem & { children?: DepartmentItem[] }> = []
  map.forEach((item) => {
    if (item.parent_id && map.has(item.parent_id)) {
      map.get(item.parent_id)?.children?.push(item)
    } else {
      roots.push(item)
    }
  })

  const sortTree = (nodes: Array<DepartmentItem & { children?: DepartmentItem[] }>) => {
    nodes.sort((a, b) => {
      if (a.sort_order !== b.sort_order) return a.sort_order - b.sort_order
      return a.name.localeCompare(b.name)
    })
    nodes.forEach((node) => {
      if (node.children?.length) sortTree(node.children)
    })
  }

  sortTree(roots)
  return roots
})

async function loadUsers() {
  if (!canManageUsers.value) return
  loading.users = true
  try {
    const data = await fetchUsers(true)
    users.value = data.items
  } finally {
    loading.users = false
  }
}

async function loadRoles() {
  if (!canManageRoles.value && !canManageUsers.value) return
  loading.roles = true
  try {
    const data = await fetchRoles()
    roles.value = data.items
  } finally {
    loading.roles = false
  }
}

async function loadPermissions() {
  if (!canManageRoles.value && !canManageUsers.value) return
  loading.permissions = true
  try {
    const data = await fetchPermissions()
    permissions.value = data.items
  } finally {
    loading.permissions = false
  }
}

async function loadDepartments() {
  if (!canManageDepartments.value && !canManageUsers.value) return
  loading.departments = true
  try {
    const data = await fetchDepartments()
    departments.value = data.items
  } finally {
    loading.departments = false
  }
}

async function loadAdminData() {
  if (!visibleTabs.value.length) return
  activeTab.value = visibleTabs.value[0].name
  await Promise.all([loadUsers(), loadRoles(), loadPermissions(), loadDepartments()])
}

function resetUserForm() {
  Object.assign(userForm, {
    username: '',
    email: '',
    display_name: '',
    employee_no: '',
    phone_number: '',
    job_title: '',
    department_id: null,
    account_status: 'active',
    data_scope: 'self',
    force_password_change: true,
    is_active: true,
    is_staff: false,
    remarks: '',
    password: '',
    role_ids: [],
  })
  editingUserId.value = null
  userDialogMode.value = 'create'
}

function openCreateUser() {
  resetUserForm()
  userDialogVisible.value = true
}

function openEditUser(user: UserItem) {
  resetUserForm()
  userDialogMode.value = 'edit'
  editingUserId.value = user.id
  Object.assign(userForm, {
    username: user.username,
    email: user.email,
    display_name: user.display_name,
    employee_no: user.employee_no,
    phone_number: user.phone_number,
    job_title: user.job_title,
    department_id: user.department?.id ?? null,
    account_status: user.account_status,
    data_scope: user.data_scope,
    force_password_change: user.force_password_change,
    is_active: user.is_active,
    is_staff: user.is_staff,
    remarks: user.remarks || '',
    password: '',
    role_ids: user.roles.map((item) => item.role.id),
  })
  userDialogVisible.value = true
}

async function openUserDetail(user: UserItem) {
  selectedUser.value = user
  userDetailVisible.value = true
  userDetailTab.value = 'overview'
  userActivityLoading.value = true
  loginHistory.value = []
  operationHistory.value = []
  conversationHistory.value = []
  taskHistory.value = []
  try {
    const data = await fetchUserActivity(user.id)
    loginHistory.value = data.login_items
    operationHistory.value = data.operation_items
    conversationHistory.value = data.conversation_items
    taskHistory.value = data.task_items
  } catch (error) {
    console.error(error)
    ElMessage.error(error instanceof Error ? error.message : '加载用户历史数据失败')
  } finally {
    userActivityLoading.value = false
  }
}

async function submitUser() {
  await userFormRef.value?.validate()
  const payload: UserPayload = {
    ...userForm,
    password: userDialogMode.value === 'create' ? userForm.password : undefined,
  }
  if (userDialogMode.value === 'create') {
    await createUser(payload)
    ElMessage.success('用户已创建')
  } else if (editingUserId.value) {
    const updatePayload = { ...payload }
    delete updatePayload.password
    await updateUser(editingUserId.value, updatePayload)
    ElMessage.success('用户信息已更新')
  }
  userDialogVisible.value = false
  await loadUsers()
}

async function handleResetPassword(user: UserItem) {
  try {
    const { value } = await ElMessageBox.prompt(`为用户 ${user.display_name || user.username} 设置新密码`, '重置密码', {
      confirmButtonText: '确认重置',
      cancelButtonText: '取消',
      inputType: 'password',
      inputPattern: /^.{8,}$/,
      inputErrorMessage: '密码至少需要 8 位',
    })
    await resetUserPassword(user.id, value, true)
    ElMessage.success('密码已重置，用户下次登录将强制修改密码')
    await loadUsers()
  } catch {
    // user cancelled
  }
}

async function handleToggleUserStatus(user: UserItem) {
  const targetStatus = user.account_status === 'active' ? 'inactive' : 'active'
  const actionLabel = targetStatus === 'active' ? '恢复' : '停用'
  try {
    await ElMessageBox.confirm(
      `确认${actionLabel}用户「${user.display_name || user.username}」吗？`,
      `${actionLabel}用户`,
      {
        type: 'warning',
        confirmButtonText: actionLabel,
        cancelButtonText: '取消',
      },
    )
  } catch {
    return
  }

  await updateUser(user.id, { account_status: targetStatus })
  ElMessage.success(`用户已${actionLabel}`)
  await loadUsers()
  if (selectedUser.value?.id === user.id) {
    selectedUser.value = users.value.find((item) => item.id === user.id) || null
  }
}

async function handleArchiveUser(user: UserItem) {
  try {
    await ElMessageBox.confirm(
      `确认将用户「${user.display_name || user.username}」移入回收站吗？移入后该账号会被停用，并从常规列表中隐藏。`,
      '删除用户',
      {
        type: 'warning',
        confirmButtonText: '移入回收站',
        cancelButtonText: '取消',
      },
    )
  } catch {
    return
  }

  await archiveUser(user.id)
  ElMessage.success('用户已移入回收站')
  userDetailVisible.value = false
  selectedUser.value = null
  await loadUsers()
}

async function handleRestoreUser(user: UserItem) {
  try {
    await ElMessageBox.confirm(
      `确认恢复用户「${user.display_name || user.username}」吗？恢复后会回到${user.status_before_archive === 'active' ? '启用' : '停用'}状态。`,
      '恢复用户',
      {
        type: 'info',
        confirmButtonText: '恢复',
        cancelButtonText: '取消',
      },
    )
  } catch {
    return
  }

  await restoreUser(user.id)
  ElMessage.success('用户已恢复')
  await loadUsers()
}

function resetRoleForm() {
  Object.assign(roleForm, {
    code: '',
    name: '',
    description: '',
    data_scope: 'self',
    permission_codes: [],
  })
  editingRoleId.value = null
  roleDialogMode.value = 'create'
}

function openCreateRole() {
  resetRoleForm()
  roleDialogVisible.value = true
}

function openEditRole(role: RoleItem) {
  resetRoleForm()
  roleDialogMode.value = 'edit'
  editingRoleId.value = role.id
  Object.assign(roleForm, {
    code: role.code,
    name: role.name,
    description: role.description,
    data_scope: role.data_scope,
    permission_codes: role.permissions.map((item) => item.code),
  })
  roleDialogVisible.value = true
}

function handleCopyRole(role: RoleItem) {
  resetRoleForm()
  roleDialogMode.value = 'create'
  Object.assign(roleForm, {
    code: `${role.code}_copy`,
    name: `${role.name}-复制`,
    description: role.description,
    data_scope: role.data_scope,
    permission_codes: role.permissions.map((item) => item.code),
  })
  roleDialogVisible.value = true
}

async function submitRole() {
  await roleFormRef.value?.validate()
  if (roleDialogMode.value === 'create') {
    await createRole({ ...roleForm })
    ElMessage.success('角色已创建')
  } else if (editingRoleId.value) {
    await updateRole(editingRoleId.value, { ...roleForm })
    ElMessage.success('角色已更新')
  }
  roleDialogVisible.value = false
  await loadRoles()
}

async function handleDeleteRole(role: RoleItem) {
  try {
    await ElMessageBox.confirm(`确认删除角色「${role.name}」吗？`, '删除角色', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消',
    })
  } catch {
    return
  }
  await deleteRole(role.id)
  ElMessage.success('角色已删除')
  await loadRoles()
}

function resetDepartmentForm() {
  Object.assign(departmentForm, {
    name: '',
    code: '',
    description: '',
    status: 'active',
    parent_id: null,
    sort_order: 0,
  })
  editingDepartmentId.value = null
  departmentDialogMode.value = 'create'
}

function openCreateDepartment() {
  resetDepartmentForm()
  departmentDialogVisible.value = true
}

function openEditDepartment(department: DepartmentItem) {
  resetDepartmentForm()
  departmentDialogMode.value = 'edit'
  editingDepartmentId.value = department.id
  Object.assign(departmentForm, {
    name: department.name,
    code: department.code,
    description: department.description,
    status: department.status,
    parent_id: department.parent_id,
    sort_order: department.sort_order,
  })
  departmentDialogVisible.value = true
}

async function submitDepartment() {
  await departmentFormRef.value?.validate()
  if (departmentDialogMode.value === 'create') {
    await createDepartment({ ...departmentForm })
    ElMessage.success('部门已创建')
  } else if (editingDepartmentId.value) {
    await updateDepartment(editingDepartmentId.value, { ...departmentForm })
    ElMessage.success('部门已更新')
  }
  departmentDialogVisible.value = false
  await loadDepartments()
}

async function handleDeleteDepartment(item: DepartmentItem) {
  try {
    await ElMessageBox.confirm(`确认删除部门「${item.name}」吗？`, '删除部门', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消',
    })
  } catch {
    return
  }
  await deleteDepartment(item.id)
  ElMessage.success('部门已删除')
  await loadDepartments()
}

onMounted(loadAdminData)
</script>

<template>
  <div class="admin-shell">
    <header class="admin-header panel-card">
      <div>
        <p class="section-title">Access Control</p>
        <h1>组织与权限管理中心</h1>
        <p>统一管理部门、角色、用户和权限分配，支撑公司内部的方案生产与治理。</p>
      </div>
      <div class="admin-header__actions">
        <el-button plain @click="loadAdminData">
          <el-icon><Refresh /></el-icon>
          刷新数据
        </el-button>
        <el-button type="primary" plain @click="router.push('/modules')">
          <el-icon><ArrowLeft /></el-icon>
          返回模块入口
        </el-button>
      </div>
    </header>

    <section class="admin-toolbar panel-card">
      <el-input v-model="searchKeyword" placeholder="搜索用户、角色或部门" clearable class="admin-toolbar__search" />
      <div class="admin-toolbar__summary">
        <span>{{ users.length }} 个用户</span>
        <span>{{ roles.length }} 个角色</span>
        <span>{{ departments.length }} 个部门</span>
      </div>
    </section>

    <section class="admin-content panel-card">
      <el-tabs v-model="activeTab">
        <el-tab-pane v-if="canManageUsers" label="用户管理" name="users">
          <template #label>
            <span>用户管理</span>
          </template>
          <div class="tab-toolbar">
            <div>
              <h3>用户台账</h3>
              <p>管理内部员工账号、部门归属、角色分配与账户状态。</p>
            </div>
            <div class="tab-toolbar__actions">
              <el-radio-group v-model="userViewMode" size="small">
                <el-radio-button label="active">在岗用户（{{ activeUsers.length }}）</el-radio-button>
                <el-radio-button label="recycle">回收站（{{ recycledUsers.length }}）</el-radio-button>
              </el-radio-group>
              <el-button v-if="userViewMode === 'active'" type="primary" @click="openCreateUser">
                <el-icon><CirclePlus /></el-icon>
                新增用户
              </el-button>
            </div>
          </div>
          <el-table :data="displayedUsers" v-loading="loading.users" stripe>
            <el-table-column prop="username" label="用户名" min-width="120" />
            <el-table-column prop="display_name" label="显示名" min-width="120" />
            <el-table-column label="部门" min-width="120">
              <template #default="{ row }">
                {{ row.department?.name || '未设置' }}
              </template>
            </el-table-column>
            <el-table-column label="角色" min-width="220">
              <template #default="{ row }">
                <el-tag v-for="item in row.roles" :key="item.id" class="role-tag">{{ item.role.name }}</el-tag>
                <span v-if="!row.roles.length" class="muted">未分配</span>
              </template>
            </el-table-column>
            <el-table-column label="状态" width="110">
              <template #default="{ row }">
                <el-tag :type="row.account_status === 'active' ? 'success' : 'info'">
                  {{ row.account_status === 'active' ? '启用' : '停用' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="最近登录" min-width="170">
              <template #default="{ row }">
                {{ row.last_login ? formatDateTime(row.last_login) : '尚未登录' }}
              </template>
            </el-table-column>
            <el-table-column label="操作" width="320" fixed="right">
              <template #default="{ row }">
                <el-button text type="primary" @click="openUserDetail(row)">
                  <el-icon><View /></el-icon>
                  详情
                </el-button>
                <template v-if="row.account_status !== 'archived'">
                  <el-button text @click="openEditUser(row)">编辑</el-button>
                  <el-button text type="primary" @click="handleResetPassword(row)">
                    <el-icon><Key /></el-icon>
                    重置密码
                  </el-button>
                  <el-button
                    text
                    :type="row.account_status === 'active' ? 'danger' : 'success'"
                    @click="handleToggleUserStatus(row)"
                  >
                    {{ row.account_status === 'active' ? '停用' : '恢复' }}
                  </el-button>
                  <el-button text type="danger" @click="handleArchiveUser(row)">删除</el-button>
                </template>
                <template v-else>
                  <el-button text type="success" @click="handleRestoreUser(row)">恢复</el-button>
                </template>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <el-tab-pane v-if="canManageRoles" label="角色管理" name="roles">
          <div class="tab-toolbar">
            <div>
              <h3>角色与授权</h3>
              <p>定义平台角色、权限包与数据范围，让不同岗位的能力边界清晰可控。</p>
            </div>
            <el-button type="primary" @click="openCreateRole">
              <el-icon><CirclePlus /></el-icon>
              新增角色
            </el-button>
          </div>
          <el-table :data="filteredRoles" v-loading="loading.roles || loading.permissions" stripe>
            <el-table-column prop="name" label="角色名称" min-width="150" />
            <el-table-column prop="code" label="角色编码" min-width="150" />
            <el-table-column label="数据范围" width="130">
              <template #default="{ row }">
                {{ row.data_scope === 'all' ? '全部' : row.data_scope === 'department' ? '本部门' : '仅本人' }}
              </template>
            </el-table-column>
            <el-table-column label="权限数" width="100">
              <template #default="{ row }">{{ row.permissions.length }}</template>
            </el-table-column>
            <el-table-column label="系统角色" width="110">
              <template #default="{ row }">
                <el-tag :type="row.is_system ? 'warning' : 'info'">{{ row.is_system ? '是' : '否' }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="description" label="说明" min-width="220" />
            <el-table-column label="操作" width="160" fixed="right">
              <template #default="{ row }">
                <el-button text type="primary" @click="handleCopyRole(row)">
                  <el-icon><CopyDocument /></el-icon>
                  复制
                </el-button>
                <el-button text @click="openEditRole(row)">编辑</el-button>
                <el-button text type="danger" :disabled="row.is_system" @click="handleDeleteRole(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <el-tab-pane v-if="canManageDepartments" label="部门管理" name="departments">
          <div class="tab-toolbar">
            <div>
              <h3>部门组织</h3>
              <p>维护组织结构和父子部门关系，为内容归属和后续统计分析打基础。</p>
            </div>
            <el-button type="primary" @click="openCreateDepartment">
              <el-icon><CirclePlus /></el-icon>
              新增部门
            </el-button>
          </div>
          <el-table
            :data="departmentTree"
            v-loading="loading.departments"
            stripe
            row-key="id"
            default-expand-all
            :tree-props="{ children: 'children' }"
          >
            <el-table-column prop="name" label="部门名称" min-width="160" />
            <el-table-column prop="code" label="部门编码" min-width="140" />
            <el-table-column label="上级部门" min-width="140">
              <template #default="{ row }">
                {{ row.parent_name || '根部门' }}
              </template>
            </el-table-column>
            <el-table-column label="状态" width="110">
              <template #default="{ row }">
                <el-tag :type="row.status === 'active' ? 'success' : 'info'">{{ row.status === 'active' ? '启用' : '停用' }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="sort_order" label="排序" width="90" />
            <el-table-column label="创建时间" min-width="170">
              <template #default="{ row }">
                {{ formatRelativeTime(row.created_at) }}
              </template>
            </el-table-column>
            <el-table-column label="操作" width="160" fixed="right">
              <template #default="{ row }">
                <el-button text @click="openEditDepartment(row)">编辑</el-button>
                <el-button text type="danger" @click="handleDeleteDepartment(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
      </el-tabs>
    </section>

    <el-dialog v-model="userDialogVisible" :title="userDialogMode === 'create' ? '新增用户' : '编辑用户'" width="760px">
      <el-form ref="userFormRef" :model="userForm" :rules="userRules" label-width="96px" class="dialog-form">
        <div class="dialog-grid two-cols">
          <el-form-item label="用户名" prop="username"><el-input v-model="userForm.username" :disabled="userDialogMode === 'edit'" /></el-form-item>
          <el-form-item label="显示名" prop="display_name"><el-input v-model="userForm.display_name" /></el-form-item>
          <el-form-item label="邮箱"><el-input v-model="userForm.email" /></el-form-item>
          <el-form-item label="工号"><el-input v-model="userForm.employee_no" /></el-form-item>
          <el-form-item label="手机号"><el-input v-model="userForm.phone_number" /></el-form-item>
          <el-form-item label="岗位"><el-input v-model="userForm.job_title" /></el-form-item>
          <el-form-item label="所属部门"><el-select v-model="userForm.department_id" clearable><el-option v-for="item in departments" :key="item.id" :label="item.name" :value="item.id" /></el-select></el-form-item>
          <el-form-item label="角色"><el-select v-model="userForm.role_ids" multiple clearable><el-option v-for="item in roles" :key="item.id" :label="item.name" :value="item.id" /></el-select></el-form-item>
          <el-form-item v-if="userDialogMode === 'create'" label="初始密码" prop="password"><el-input v-model="userForm.password" type="password" show-password /></el-form-item>
          <el-form-item label="账户状态"><el-select v-model="userForm.account_status"><el-option label="启用" value="active" /><el-option label="停用" value="inactive" /></el-select></el-form-item>
          <el-form-item label="数据范围"><el-select v-model="userForm.data_scope"><el-option label="仅本人" value="self" /><el-option label="本部门" value="department" /><el-option label="全部" value="all" /></el-select></el-form-item>
          <el-form-item label="允许后台"><el-switch v-model="userForm.is_staff" /></el-form-item>
          <el-form-item label="首次改密"><el-switch v-model="userForm.force_password_change" /></el-form-item>
        </div>
        <el-form-item label="备注"><el-input v-model="userForm.remarks" type="textarea" :rows="3" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="userDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitUser">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="roleDialogVisible" :title="roleDialogMode === 'create' ? '新增角色' : '编辑角色'" width="820px">
      <el-form ref="roleFormRef" :model="roleForm" :rules="roleRules" label-width="96px" class="dialog-form">
        <div class="dialog-grid two-cols">
          <el-form-item label="角色编码" prop="code"><el-input v-model="roleForm.code" :disabled="roleDialogMode === 'edit' && roles.find((item) => item.id === editingRoleId)?.is_system" /></el-form-item>
          <el-form-item label="角色名称" prop="name"><el-input v-model="roleForm.name" /></el-form-item>
          <el-form-item label="数据范围"><el-select v-model="roleForm.data_scope"><el-option label="仅本人" value="self" /><el-option label="本部门" value="department" /><el-option label="全部" value="all" /></el-select></el-form-item>
          <el-form-item label="说明"><el-input v-model="roleForm.description" /></el-form-item>
        </div>
        <el-form-item label="权限配置">
          <div class="permission-groups">
            <section v-for="group in permissionGroups" :key="group.module" class="permission-group panel-card">
              <header>
                <strong>{{ group.module }}</strong>
              </header>
              <el-checkbox-group v-model="roleForm.permission_codes">
                <el-checkbox v-for="item in group.items" :key="item.code" :label="item.code">
                  <div class="permission-item">
                    <span>{{ item.name }}</span>
                    <small>{{ item.code }}</small>
                  </div>
                </el-checkbox>
              </el-checkbox-group>
            </section>
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="roleDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitRole">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="departmentDialogVisible" :title="departmentDialogMode === 'create' ? '新增部门' : '编辑部门'" width="680px">
      <el-form ref="departmentFormRef" :model="departmentForm" :rules="departmentRules" label-width="96px" class="dialog-form">
        <div class="dialog-grid two-cols">
          <el-form-item label="部门名称" prop="name"><el-input v-model="departmentForm.name" /></el-form-item>
          <el-form-item label="部门编码" prop="code"><el-input v-model="departmentForm.code" /></el-form-item>
          <el-form-item label="上级部门"><el-select v-model="departmentForm.parent_id" clearable><el-option v-for="item in departments.filter((item) => item.id !== editingDepartmentId)" :key="item.id" :label="item.name" :value="item.id" /></el-select></el-form-item>
          <el-form-item label="状态"><el-select v-model="departmentForm.status"><el-option label="启用" value="active" /><el-option label="停用" value="inactive" /></el-select></el-form-item>
          <el-form-item label="排序"><el-input-number v-model="departmentForm.sort_order" :min="0" :max="999" /></el-form-item>
        </div>
        <el-form-item label="说明"><el-input v-model="departmentForm.description" type="textarea" :rows="3" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="departmentDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitDepartment">保存</el-button>
      </template>
    </el-dialog>

    <el-drawer v-model="userDetailVisible" size="760px" title="用户详情">
      <template v-if="selectedUser">
        <section class="detail-panel">
          <div class="detail-hero panel-card">
            <div>
              <h3>{{ selectedUser.display_name || selectedUser.username }}</h3>
              <p>{{ selectedUser.job_title || '未设置岗位' }} · {{ selectedUser.department?.name || '未设置部门' }}</p>
            </div>
            <el-tag :type="selectedUser.account_status === 'active' ? 'success' : 'info'">
              {{ selectedUser.account_status === 'active' ? '启用' : '停用' }}
            </el-tag>
          </div>

          <el-tabs v-model="userDetailTab" class="detail-tabs">
            <el-tab-pane label="概览" name="overview">
              <div class="detail-grid">
                <div class="panel-card detail-card">
                  <h4>基础信息</h4>
                  <dl>
                    <dt>用户名</dt><dd>{{ selectedUser.username }}</dd>
                    <dt>邮箱</dt><dd>{{ selectedUser.email || '未设置' }}</dd>
                    <dt>工号</dt><dd>{{ selectedUser.employee_no || '未设置' }}</dd>
                    <dt>手机号</dt><dd>{{ selectedUser.phone_number || '未设置' }}</dd>
                    <dt>数据范围</dt><dd>{{ selectedUser.data_scope_resolved === 'all' ? '全部' : selectedUser.data_scope_resolved === 'department' ? '本部门' : '仅本人' }}</dd>
                    <dt>首次改密</dt><dd>{{ selectedUser.force_password_change ? '是' : '否' }}</dd>
                    <dt>最近登录</dt><dd>{{ selectedUser.last_login ? formatDateTime(selectedUser.last_login) : '尚未登录' }}</dd>
                    <dt>最近登录IP</dt><dd>{{ selectedUser.last_login_ip || '无记录' }}</dd>
                    <dt>归档时间</dt><dd>{{ selectedUser.archived_at ? formatDateTime(selectedUser.archived_at) : '未归档' }}</dd>
                  </dl>
                </div>

                <div class="panel-card detail-card">
                  <h4>角色与权限</h4>
                  <div class="detail-tags">
                    <el-tag v-for="item in selectedUser.roles" :key="item.id" class="role-tag">{{ item.role.name }}</el-tag>
                    <span v-if="!selectedUser.roles.length" class="muted">未分配角色</span>
                  </div>
                  <p class="detail-subtitle">权限清单</p>
                  <div class="detail-tags">
                    <el-tag v-for="code in selectedUser.permissions" :key="code" type="info" effect="plain">{{ code }}</el-tag>
                  </div>
                </div>
              </div>

              <section class="panel-card detail-card">
                <h4>备注</h4>
                <p class="detail-remarks">{{ selectedUser.remarks || '暂无备注' }}</p>
              </section>
            </el-tab-pane>

            <el-tab-pane label="活动记录" name="activity">
              <section class="panel-card detail-card">
                <div class="detail-card__head">
                  <h4>登录历史</h4>
                  <span v-if="userActivityLoading" class="muted">加载中...</span>
                </div>
                <div v-if="loginHistory.length" class="timeline">
                  <article v-for="item in loginHistory" :key="item.id" class="timeline__item">
                    <div class="timeline__dot" />
                    <div>
                      <strong>{{ item.action === 'auth.login' ? '登录成功' : '主动退出' }}</strong>
                      <p>{{ formatDateTime(item.created_at) }} · {{ item.actor_name }}</p>
                    </div>
                  </article>
                </div>
                <p v-else class="muted">暂无登录历史</p>
              </section>

              <section class="panel-card detail-card">
                <div class="detail-card__head">
                  <h4>操作历史</h4>
                  <span class="muted">最近 30 条</span>
                </div>
                <div v-if="operationHistory.length" class="timeline">
                  <article v-for="item in operationHistory" :key="item.id" class="timeline__item">
                    <div class="timeline__dot timeline__dot--secondary" />
                    <div>
                      <strong>{{ item.action }}</strong>
                      <p>{{ formatDateTime(item.created_at) }} · 操作人：{{ item.actor_name }}</p>
                      <p class="timeline__meta">{{ JSON.stringify(item.detail_json || {}) }}</p>
                    </div>
                  </article>
                </div>
                <p v-else class="muted">暂无操作历史</p>
              </section>
            </el-tab-pane>

            <el-tab-pane label="业务记录" name="business">
              <div class="detail-grid detail-grid--records">
                <section class="panel-card detail-card">
                  <div class="detail-card__head">
                    <h4>会话历史</h4>
                    <span class="muted">最近 20 条</span>
                  </div>
                  <div v-if="conversationHistory.length" class="activity-list">
                    <article v-for="item in conversationHistory" :key="item.conversation_id" class="activity-card">
                      <div class="activity-card__head">
                        <strong class="activity-card__title">{{ item.title || '未命名会话' }}</strong>
                        <el-tag :type="item.status === 'running' ? 'warning' : item.status === 'failed' ? 'danger' : 'success'" effect="plain">
                          {{ item.status === 'running' ? '生成中' : item.status === 'failed' ? '失败' : '完成/空闲' }}
                        </el-tag>
                      </div>
                      <p class="activity-card__body">{{ item.last_user_message || '暂无用户问题摘要' }}</p>
                      <small>最近更新时间：{{ formatDateTime(item.updated_at) }}</small>
                    </article>
                  </div>
                  <p v-else class="muted">暂无会话历史</p>
                </section>

                <section class="panel-card detail-card">
                  <div class="detail-card__head">
                    <h4>生成任务历史</h4>
                    <span class="muted">最近 20 条</span>
                  </div>
                  <div v-if="taskHistory.length" class="activity-list">
                    <article v-for="item in taskHistory" :key="item.task_id" class="activity-card">
                      <div class="activity-card__head">
                        <strong class="activity-card__title">{{ item.conversation_title || '未命名会话任务' }}</strong>
                        <el-tag
                          :type="
                            item.status === 'completed'
                              ? 'success'
                              : item.status === 'failed'
                                ? 'danger'
                                : item.status === 'cancelled'
                                  ? 'info'
                                  : 'warning'
                          "
                          effect="plain"
                        >
                          {{ item.status }}
                        </el-tag>
                      </div>
                      <p class="activity-card__body">{{ item.current_step || '未记录阶段' }}</p>
                      <p v-if="item.assistant_summary" class="activity-card__summary">{{ item.assistant_summary }}</p>
                      <p v-else-if="item.error_message" class="activity-card__summary activity-card__summary--error">{{ item.error_message }}</p>
                      <small>创建时间：{{ formatDateTime(item.created_at) }}</small>
                    </article>
                  </div>
                  <p v-else class="muted">暂无生成任务历史</p>
                </section>
              </div>
            </el-tab-pane>
          </el-tabs>
        </section>
      </template>
    </el-drawer>
  </div>
</template>

<style scoped>
.admin-shell {
  display: flex;
  flex-direction: column;
  gap: 18px;
  padding: 24px;
}

.admin-header,
.admin-toolbar,
.admin-content {
  padding: 20px 22px;
}

.admin-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;
}

.admin-header h1 {
  margin: 6px 0 10px;
  font-size: 32px;
}

.admin-header p {
  margin: 0;
  max-width: 720px;
  color: var(--muted);
  line-height: 1.7;
}

.admin-header__actions,
.admin-toolbar__summary {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.admin-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.admin-toolbar__search {
  max-width: 360px;
}

.admin-toolbar__summary span {
  color: var(--muted);
  font-size: 13px;
}

.tab-toolbar {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 18px;
}

.tab-toolbar__actions {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.tab-toolbar h3 {
  margin: 0 0 6px;
  font-size: 20px;
}

.tab-toolbar p {
  margin: 0;
  color: var(--muted);
}

.role-tag {
  margin: 0 6px 6px 0;
}

.muted {
  color: var(--muted);
}

.detail-panel {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.detail-tabs {
  margin-top: -4px;
}

.detail-hero {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  padding: 18px 20px;
}

.detail-hero h3 {
  margin: 0 0 6px;
  font-size: 24px;
}

.detail-hero p {
  margin: 0;
  color: var(--muted);
}

.detail-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.detail-grid--records {
  align-items: start;
}

.detail-card {
  padding: 18px 20px;
}

.detail-card h4 {
  margin: 0 0 14px;
  font-size: 16px;
}

.detail-card__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
}

.detail-card dl {
  display: grid;
  grid-template-columns: 90px minmax(0, 1fr);
  gap: 10px 14px;
  margin: 0;
}

.detail-card dt {
  color: var(--muted);
  font-size: 13px;
}

.detail-card dd {
  margin: 0;
  font-size: 14px;
  word-break: break-word;
}

.detail-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.detail-subtitle {
  margin: 16px 0 10px;
  color: var(--muted);
  font-size: 13px;
}

.detail-remarks {
  margin: 0;
  line-height: 1.7;
  color: var(--text);
}

.timeline {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.timeline__item {
  display: grid;
  grid-template-columns: 14px minmax(0, 1fr);
  gap: 12px;
}

.timeline__item strong {
  display: block;
  margin-bottom: 4px;
}

.timeline__item p {
  margin: 0;
  color: var(--muted);
  line-height: 1.6;
}

.timeline__dot {
  width: 12px;
  height: 12px;
  border-radius: 999px;
  margin-top: 4px;
  background: var(--success);
  box-shadow: 0 0 0 4px rgba(33, 121, 107, 0.12);
}

.timeline__dot--secondary {
  background: var(--accent);
  box-shadow: 0 0 0 4px rgba(15, 93, 140, 0.12);
}

.timeline__meta {
  font-family: 'SFMono-Regular', 'JetBrains Mono', Consolas, monospace;
  font-size: 12px;
  word-break: break-word;
}

.activity-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.activity-card {
  padding: 14px 16px;
  border-radius: 16px;
  border: 1px solid rgba(24, 50, 71, 0.08);
  background: rgba(255, 255, 255, 0.72);
  min-width: 0;
}

.activity-card__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 8px;
}

.activity-card p,
.activity-card small {
  margin: 0;
  line-height: 1.6;
}

.activity-card p {
  color: var(--text);
}

.activity-card small,
.activity-card__summary {
  color: var(--muted);
}

.activity-card__title {
  display: -webkit-box;
  overflow: hidden;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  line-height: 1.5;
}

.activity-card__body,
.activity-card__summary {
  display: -webkit-box;
  overflow: hidden;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  word-break: break-word;
}

.activity-card__summary {
  margin-top: 8px !important;
  font-size: 13px;
}

.activity-card__summary--error {
  color: var(--danger);
}

.dialog-form {
  padding-top: 8px;
}

.dialog-grid {
  display: grid;
  gap: 8px 18px;
}

.dialog-grid.two-cols {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.permission-groups {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
  width: 100%;
}

.permission-group {
  padding: 14px 16px;
  border-radius: 18px;
}

.permission-group header {
  margin-bottom: 12px;
}

.permission-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.permission-item small {
  color: var(--muted);
}

:deep(.el-checkbox) {
  align-items: flex-start;
  margin-right: 0;
  margin-bottom: 12px;
}

@media (max-width: 1080px) {
  .dialog-grid.two-cols,
  .permission-groups,
  .detail-grid {
    grid-template-columns: minmax(0, 1fr);
  }

  .admin-header,
  .admin-toolbar,
  .tab-toolbar {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
