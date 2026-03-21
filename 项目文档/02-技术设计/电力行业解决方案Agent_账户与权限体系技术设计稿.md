# 电力行业解决方案Agent 账户与权限体系技术设计稿

## 1. 文档目标

本技术设计稿用于指导 Django 平台层实现账户、角色、权限、部门与资源访问控制能力，配合已有的会话、任务、审计模型，形成内部员工可用的统一账号体系。

对应的产品设计基础见：

- `账户与权限体系设计文档`

本稿重点回答以下研发问题：

1. 后端应新增哪些模型
2. 认证方式如何落地
3. 权限校验在哪里执行
4. 会话/任务如何做 owner + department 访问控制
5. 超级管理员如何通过脚本初始化
6. 前端需要对接哪些接口

## 2. 技术边界

### 2.1 所属层次

本方案仅作用于：

- `backend/platform/` Django 平台层

不直接改动：

- `backend/agent_service/` 的模型层
- `RAGFlow` 内部账号体系

### 2.2 当前基础

当前平台已有：

- 自定义 `accounts.User(AbstractUser)`
- `Conversation`
- `Message`
- `GenerationTask`
- `AuditLog`

当前缺失：

- Department
- Role
- Permission
- 用户角色绑定
- 登录接口
- 统一鉴权中间件/权限判断工具
- 基于 owner/department 的资源访问控制

## 3. 认证方案

## 3.1 首期推荐

首期建议采用：

- `JWT Access Token + Refresh Token`

原因：

- 前后端分离更自然
- 便于后续扩展到独立前端、移动端、SSO
- 与 Django DRF 结合成熟

推荐实现：

- `djangorestframework-simplejwt`

## 3.2 Token 设计建议

### Access Token

- 有效期：`2h`
- 内容：
  - `user_id`
  - `username`
  - `display_name`
  - `department_id`
  - `role_codes`
  - `data_scope`

### Refresh Token

- 有效期：`7d ~ 14d`
- 服务端支持吊销或黑名单机制

## 3.3 登录方式

首期支持：

- `username + password`
- `employee_no + password`

实现建议：

- 登录时允许传 `login_name`
- 后端按顺序匹配：
  1. `username=login_name`
  2. `employee_no=login_name`

## 4. 数据模型设计

## 4.1 User 模型扩展

基于现有 `accounts.User` 追加字段：

```python
class User(AbstractUser):
    display_name = models.CharField(max_length=128, blank=True)
    employee_no = models.CharField(max_length=32, unique=True, null=True, blank=True)
    mobile = models.CharField(max_length=32, blank=True)
    avatar_url = models.URLField(blank=True)
    job_title = models.CharField(max_length=128, blank=True)

    department = models.ForeignKey(
        'accounts.Department',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='users',
    )
    manager = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='team_members',
    )

    account_status = models.CharField(
        max_length=16,
        choices=[
            ('pending', 'Pending'),
            ('active', 'Active'),
            ('disabled', 'Disabled'),
            ('locked', 'Locked'),
        ],
        default='pending',
    )
    data_scope = models.CharField(
        max_length=16,
        choices=[
            ('self', 'Self'),
            ('department', 'Department'),
            ('all', 'All'),
        ],
        default='self',
    )
    must_change_password = models.BooleanField(default=True)
    password_changed_at = models.DateTimeField(null=True, blank=True)
    last_login_ip = models.GenericIPAddressField(null=True, blank=True)
    failed_login_count = models.PositiveIntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)

    created_by = models.ForeignKey(
        'self', null=True, blank=True, on_delete=models.SET_NULL, related_name='created_users'
    )
    updated_by = models.ForeignKey(
        'self', null=True, blank=True, on_delete=models.SET_NULL, related_name='updated_users'
    )
    remark = models.TextField(blank=True)
```

## 4.2 Department

```python
class Department(models.Model):
    name = models.CharField(max_length=128)
    code = models.CharField(max_length=64, unique=True)
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL)
    manager = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    status = models.CharField(max_length=16, default='active')
    sort_order = models.IntegerField(default=0)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

## 4.3 Role

```python
class Role(models.Model):
    code = models.CharField(max_length=64, unique=True)
    name = models.CharField(max_length=128)
    scope_type = models.CharField(max_length=16, default='platform')
    description = models.TextField(blank=True)
    is_system_builtin = models.BooleanField(default=False)
    status = models.CharField(max_length=16, default='active')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

## 4.4 Permission

```python
class PermissionCode(models.Model):
    code = models.CharField(max_length=128, unique=True)
    name = models.CharField(max_length=128)
    module = models.CharField(max_length=64)
    description = models.TextField(blank=True)
    is_system_builtin = models.BooleanField(default=False)
```

## 4.5 关系表

```python
class UserRole(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    role = models.ForeignKey('accounts.Role', on_delete=models.CASCADE)
    assigned_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='assigned_roles')
    assigned_at = models.DateTimeField(auto_now_add=True)

class RolePermission(models.Model):
    role = models.ForeignKey('accounts.Role', on_delete=models.CASCADE)
    permission = models.ForeignKey('accounts.PermissionCode', on_delete=models.CASCADE)
```

约束建议：

- `UserRole(user, role)` 唯一
- `RolePermission(role, permission)` 唯一

## 4.6 现有业务模型补充字段

### Conversation

建议补：

```python
owner = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
department = models.ForeignKey('accounts.Department', null=True, blank=True, on_delete=models.SET_NULL)
visibility = models.CharField(max_length=16, default='private')
```

### GenerationTask

建议补：

```python
owner = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
department = models.ForeignKey('accounts.Department', null=True, blank=True, on_delete=models.SET_NULL)
```

### AuditLog

建议补：

```python
department = models.ForeignKey('accounts.Department', null=True, blank=True, on_delete=models.SET_NULL)
ip_address = models.GenericIPAddressField(null=True, blank=True)
user_agent = models.TextField(blank=True)
result_status = models.CharField(max_length=32, blank=True)
```

## 5. 权限判断设计

## 5.1 判断维度

访问控制拆成两层：

1. `功能权限`
- 是否允许访问某接口

2. `数据权限`
- 是否允许访问这条资源

## 5.2 功能权限判断

建议提供统一方法：

```python
def user_has_permission(user, code: str) -> bool:
    ...
```

逻辑：

1. `is_superuser` 直接通过
2. 查用户关联角色
3. 汇总角色关联的权限码
4. 判断权限码是否存在

建议增加缓存层：

- 按 `user_id` 缓存权限集合
- 角色变更后主动清缓存

## 5.3 数据权限判断

建议统一封装：

```python
def can_access_conversation(user, conversation) -> bool:
    ...

def can_access_task(user, task) -> bool:
    ...
```

规则建议：

### 普通用户

- 只能看 `owner_id == user.id`

### 部门管理员

- 能看本部门资源

### 平台管理员 / 超级管理员

- 可看全局资源

### visibility 补充

- `private`：仅本人/管理员
- `department`：本部门可见
- `platform`：平台内可见，首期仅管理员使用

## 6. 模块划分建议

建议在 `apps/accounts/` 下增加：

- `models.py`
- `serializers.py`
- `permissions.py`
- `selectors.py`
- `services.py`
- `views_auth.py`
- `views_user.py`
- `views_role.py`
- `views_department.py`
- `urls.py`
- `management/commands/bootstrap_super_admin.py`
- `management/commands/bootstrap_rbac.py`

## 7. 接口设计建议

## 7.1 认证接口

### 登录

`POST /api/v1/auth/login`

请求：

```json
{
  "login_name": "admin",
  "password": "***"
}
```

响应：

```json
{
  "access_token": "...",
  "refresh_token": "...",
  "user": {
    "user_id": "...",
    "username": "admin",
    "display_name": "系统管理员",
    "department": {
      "id": "...",
      "name": "平台管理部"
    },
    "roles": ["super_admin"],
    "permissions": ["user.view", "role.assign"]
  }
}
```

### 刷新 Token

`POST /api/v1/auth/refresh`

### 当前用户信息

`GET /api/v1/auth/me`

### 登出

`POST /api/v1/auth/logout`

## 7.2 用户接口

- `GET /api/v1/users`
- `POST /api/v1/users`
- `GET /api/v1/users/{id}`
- `PATCH /api/v1/users/{id}`
- `POST /api/v1/users/{id}/disable`
- `POST /api/v1/users/{id}/enable`
- `POST /api/v1/users/{id}/reset-password`
- `POST /api/v1/users/{id}/roles`

## 7.3 部门接口

- `GET /api/v1/departments`
- `POST /api/v1/departments`
- `PATCH /api/v1/departments/{id}`
- `GET /api/v1/departments/tree`

## 7.4 角色与权限接口

- `GET /api/v1/roles`
- `POST /api/v1/roles`
- `PATCH /api/v1/roles/{id}`
- `GET /api/v1/permissions`
- `POST /api/v1/roles/{id}/permissions`

## 8. 超级管理员初始化命令设计

## 8.1 命令

```bash
python manage.py bootstrap_super_admin \
  --username admin \
  --password 'StrongPassword123!' \
  --display-name '系统管理员' \
  --employee-no A0001 \
  --email admin@company.com
```

## 8.2 实现逻辑

1. 检查 `Role(super_admin)` 是否存在，不存在则提示先执行 `bootstrap_rbac`
2. 检查用户名或工号是否已存在
3. 创建用户
4. 设置：
   - `is_superuser = True`
   - `is_staff = True`
   - `is_active = True`
   - `account_status = active`
   - `must_change_password = False`
5. 绑定 `super_admin` 角色
6. 写审计日志

## 8.3 幂等建议

支持参数：

- `--reset-password`
- `--update-profile`

## 9. 内置 RBAC 初始化设计

## 9.1 命令

```bash
python manage.py bootstrap_rbac
```

## 9.2 初始化内容

### 部门（可选）

首期可初始化一个默认平台部门：

- `platform_admin_dept`

### 角色

- `super_admin`
- `platform_admin`
- `department_admin`
- `power_user`
- `employee`

### 权限码

写入产品文档中定义的权限集合。

### 绑定关系

按内置矩阵写入 `RolePermission`。

## 10. DRF 权限落地建议

建议封装 3 类权限类：

### 10.1 功能权限类

```python
class HasPermissionCode(BasePermission):
    required_code = ''
```

### 10.2 会话资源权限类

```python
class CanAccessConversation(BasePermission):
    ...
```

### 10.3 任务资源权限类

```python
class CanAccessTask(BasePermission):
    ...
```

## 11. 与现有会话/任务接口的改造建议

当前会话与任务接口默认是匿名可访问口径，应改为：

1. 接口统一要求登录
2. 创建会话时自动写入：
   - `owner=request.user`
   - `department=request.user.department`
3. 创建任务时自动写入：
   - `owner=request.user`
   - `department=request.user.department`
4. 查询列表时按数据范围过滤

## 12. 审计设计建议

以下动作必须写审计日志：

- 登录成功/失败
- 登出
- 创建账户
- 停用账户
- 重置密码
- 角色分配
- 部门调整
- 删除/批量删除资源
- 超级管理员初始化
- RBAC 初始化

建议统一封装审计方法：

```python
def write_audit_log(*, user, action, resource_type, resource_id, detail_json=None, result_status='success'):
    ...
```

## 13. 前端对接建议

前端首期至少需要：

- 登录页
- 获取当前用户信息接口
- 根据权限动态控制导航和按钮可见性
- 用户管理页
- 部门管理页
- 角色管理页

建议前端把权限码缓存到 store 中，例如：

```ts
permissions: string[]
roleCodes: string[]
```

并提供：

```ts
hasPermission(code: string): boolean
```

## 14. 数据迁移建议

迁移顺序建议：

1. 扩展 `User`
2. 新增 `Department`
3. 新增 `Role / PermissionCode / UserRole / RolePermission`
4. 给 `Conversation / Task / AuditLog` 加 owner/department 等字段
5. 跑 `bootstrap_rbac`
6. 跑 `bootstrap_super_admin`
7. 再切换接口到“必须登录”模式

## 15. 风险与注意事项

### 15.1 不建议直接依赖 Django Group 代替 Role

原因：

- 后续还需要 `scope_type`、内置角色标识、运营描述等业务字段
- 自定义 Role 更清晰

### 15.2 不建议只用前端控制权限

所有权限必须以后端为准，前端仅做体验层隐藏。

### 15.3 不建议一开始做过度复杂的数据范围

首期建议先做：

- `self`
- `department`
- `all`

足够覆盖内部使用场景。

## 16. 推荐落地顺序

1. 模型与 migration
2. RBAC 初始化命令
3. 超级管理员初始化命令
4. 登录/刷新/当前用户接口
5. 用户/部门/角色管理接口
6. 会话/任务 owner + department 访问控制
7. 前端登录与权限页面

一句话总结：

`技术落地上，建议采用“JWT 认证 + 自定义 Role/Permission + Department + owner/department 数据控制 + management command 初始化”的方案。`
