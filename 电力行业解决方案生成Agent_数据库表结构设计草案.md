# 电力行业解决方案生成Agent 数据库表结构设计草案

## 1. 目标

本文档用于给 Django 平台层提供 MVP 阶段的数据库设计草案，优先覆盖：

- 用户预留
- 会话
- 消息
- 任务
- 审计
- 配置

数据库建议：

- `PostgreSQL`

## 2. 表清单

MVP 建议至少包含：

1. `users`
2. `roles`
3. `user_roles`
4. `conversations`
5. `messages`
6. `tasks`
7. `task_events`
8. `audit_logs`
9. `system_configs`

## 3. users

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | bigint pk | 主键 |
| `username` | varchar(64) | 登录名 |
| `display_name` | varchar(128) | 展示名 |
| `email` | varchar(128) | 邮箱 |
| `is_active` | bool | 是否有效 |
| `created_at` | timestamp | 创建时间 |
| `updated_at` | timestamp | 更新时间 |

说明：

- MVP 可暂不开放登录，但表先建好

## 4. roles

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | bigint pk | 主键 |
| `code` | varchar(64) | 角色编码 |
| `name` | varchar(128) | 角色名称 |
| `created_at` | timestamp | 创建时间 |

## 5. user_roles

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | bigint pk | 主键 |
| `user_id` | bigint | 用户 ID |
| `role_id` | bigint | 角色 ID |

## 6. conversations

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | uuid pk | 会话 ID |
| `user_id` | bigint nullable | 用户 ID |
| `title` | varchar(255) | 会话标题 |
| `status` | varchar(32) | idle/running/failed |
| `last_user_message` | text | 最近用户消息摘要 |
| `last_message_at` | timestamp | 最近消息时间 |
| `created_at` | timestamp | 创建时间 |
| `updated_at` | timestamp | 更新时间 |

索引建议：

- `user_id, updated_at desc`

## 7. messages

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | uuid pk | 消息 ID |
| `conversation_id` | uuid | 会话 ID |
| `role` | varchar(16) | user/assistant/system |
| `status` | varchar(32) | pending/running/completed/failed |
| `query_text` | text | 用户原始提问 |
| `summary_text` | text | 摘要 |
| `content_markdown` | text | 正文 |
| `assumptions_json` | jsonb | 假设条件 |
| `evidence_cards_json` | jsonb | 证据卡 |
| `metadata_json` | jsonb | 扩展字段 |
| `created_at` | timestamp | 创建时间 |
| `updated_at` | timestamp | 更新时间 |

索引建议：

- `conversation_id, created_at asc`

## 8. tasks

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | uuid pk | 任务 ID |
| `conversation_id` | uuid | 会话 ID |
| `assistant_message_id` | uuid | 对应 assistant 消息 |
| `status` | varchar(32) | pending/running/completed/failed/cancelled |
| `current_step` | varchar(64) | 当前节点 |
| `run_id` | varchar(128) | Agent Service 运行 ID |
| `error_code` | varchar(32) | 错误码 |
| `error_message` | text | 错误信息 |
| `started_at` | timestamp | 开始时间 |
| `finished_at` | timestamp | 结束时间 |
| `created_at` | timestamp | 创建时间 |
| `updated_at` | timestamp | 更新时间 |

索引建议：

- `conversation_id, created_at desc`
- `status`

## 9. task_events

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | bigint pk | 主键 |
| `task_id` | uuid | 任务 ID |
| `event_type` | varchar(64) | status/content/error 等 |
| `payload_json` | jsonb | 事件内容 |
| `created_at` | timestamp | 创建时间 |

用途：

- 问题排查
- 回放关键节点
- 审计和追踪

## 10. audit_logs

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | bigint pk | 主键 |
| `user_id` | bigint nullable | 操作人 |
| `action` | varchar(128) | 操作类型 |
| `resource_type` | varchar(64) | 资源类型 |
| `resource_id` | varchar(128) | 资源 ID |
| `detail_json` | jsonb | 明细 |
| `created_at` | timestamp | 创建时间 |

## 11. system_configs

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | bigint pk | 主键 |
| `config_key` | varchar(128) | 配置键 |
| `config_value` | jsonb | 配置值 |
| `description` | text | 说明 |
| `updated_at` | timestamp | 更新时间 |

适合保存：

- 默认参数
- 模型策略
- 场景配置

## 12. Django App 对应建议

- `accounts`
  - users
  - roles
  - user_roles

- `conversations`
  - conversations
  - messages

- `tasks`
  - tasks
  - task_events

- `audit`
  - audit_logs

- `configurations`
  - system_configs

## 13. 最终建议

MVP 阶段数据库不要贪大而全，先把：

- 会话
- 消息
- 任务
- 事件

这四类表建稳。  
而用户、角色、审计和配置要先预留，不要等到后期再硬改主数据结构。
