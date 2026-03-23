from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PermissionSeed:
    code: str
    name: str
    module: str
    action: str
    resource_scope: str
    description: str


PERMISSION_SEEDS = [
    PermissionSeed("solution.access", "进入解决方案智能体", "solution", "access", "self", "进入解决方案智能体模块。"),
    PermissionSeed("customer_demand.access", "进入客户需求分析智能体", "customer_demand_module", "access", "self", "进入客户需求分析智能体模块。"),
    PermissionSeed("knowledge.access", "进入知识库管理", "knowledge", "access", "platform", "进入知识库管理模块。"),
    PermissionSeed("access_admin.access", "进入组织与权限管理", "access_admin", "access", "platform", "进入组织与权限管理模块。"),
    PermissionSeed("audit.access", "进入审计日志中心", "audit_center", "access", "platform", "进入审计日志中心模块。"),
    PermissionSeed("platform.manage", "平台管理", "platform", "manage", "platform", "管理平台配置与系统能力。"),
    PermissionSeed("user.manage", "用户管理", "user", "manage", "platform", "创建、编辑、停用用户。"),
    PermissionSeed("role.manage", "角色管理", "role", "manage", "platform", "创建、编辑角色及授权。"),
    PermissionSeed("department.manage", "部门管理", "department", "manage", "platform", "管理部门树与负责人。"),
    PermissionSeed("conversation.view", "查看会话", "conversation", "view", "self", "查看解决方案会话。"),
    PermissionSeed("conversation.manage_department", "管理部门会话", "conversation", "manage_department", "department", "管理本部门会话。"),
    PermissionSeed("conversation.manage_all", "管理全部会话", "conversation", "manage_all", "platform", "管理全部会话。"),
    PermissionSeed("task.view", "查看任务", "task", "view", "self", "查看生成任务。"),
    PermissionSeed("task.manage_department", "管理部门任务", "task", "manage_department", "department", "管理本部门任务。"),
    PermissionSeed("task.manage_all", "管理全部任务", "task", "manage_all", "platform", "管理全部任务。"),
    PermissionSeed("customer_demand.view", "查看客户需求会话", "customer_demand", "view", "self", "查看客户需求分析会话。"),
    PermissionSeed("customer_demand.create", "创建客户需求会话", "customer_demand", "create", "self", "创建客户需求分析会话。"),
    PermissionSeed("customer_demand.manage_all", "管理全部客户需求会话", "customer_demand", "manage_all", "platform", "管理全部客户需求分析会话。"),
    PermissionSeed("customer_demand.export", "导出客户需求报告", "customer_demand", "export", "platform", "导出客户需求分析报告。"),
    PermissionSeed("template.manage", "模板管理", "template", "manage", "platform", "管理场景模板与路由配置。"),
    PermissionSeed("knowledge.manage", "知识库配置", "knowledge", "manage", "platform", "配置知识库路由与数据源。"),
    PermissionSeed("audit.view", "查看审计日志", "audit", "view", "platform", "查看审计日志。"),
]


ROLE_SEEDS = {
    "super_admin": {
        "name": "超级管理员",
        "description": "拥有全部平台能力。",
        "data_scope": "all",
        "permissions": [seed.code for seed in PERMISSION_SEEDS],
    },
    "platform_admin": {
        "name": "平台管理员",
        "description": "负责平台配置、知识库和模板管理。",
        "data_scope": "all",
        "permissions": [
            "solution.access",
            "customer_demand.access",
            "knowledge.access",
            "access_admin.access",
            "audit.access",
            "platform.manage",
            "user.manage",
            "role.manage",
            "department.manage",
            "conversation.manage_all",
            "task.manage_all",
            "customer_demand.manage_all",
            "customer_demand.export",
            "template.manage",
            "knowledge.manage",
            "audit.view",
        ],
    },
    "department_admin": {
        "name": "部门管理员",
        "description": "管理本部门成员、会话与任务。",
        "data_scope": "department",
        "permissions": [
            "solution.access",
            "customer_demand.access",
            "conversation.manage_department",
            "task.manage_department",
            "conversation.view",
            "task.view",
            "customer_demand.view",
            "customer_demand.create",
        ],
    },
    "power_user": {
        "name": "高级用户",
        "description": "可创建和查看本人的解决方案任务。",
        "data_scope": "self",
        "permissions": [
            "solution.access",
            "customer_demand.access",
            "conversation.view",
            "task.view",
            "customer_demand.view",
            "customer_demand.create",
        ],
    },
    "employee": {
        "name": "普通员工",
        "description": "可使用基础解决方案生成能力。",
        "data_scope": "self",
        "permissions": [
            "solution.access",
            "customer_demand.access",
            "conversation.view",
            "task.view",
            "customer_demand.view",
            "customer_demand.create",
        ],
    },
}
