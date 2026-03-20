# 电力行业解决方案生成Agent 后端开发任务拆解清单

## 1. 文档目标

本文档面向后端工程师、Agent 工程师和全栈工程师，用于把当前系统拆解成可执行的后端开发任务。

技术边界：

- `Django 平台层`
- `Agent Service`
- `LangGraph 编排层`
- `Retrieval Service`
- `LLM Gateway`
- `RAGFlow 对接`

## 2. 后端目标

后端需支撑以下前端能力：

1. 会话创建与历史会话列表
2. 历史消息加载
3. 在会话中发送消息
4. 任务流式输出
5. 方案结果保存
6. 任务取消
7. 模型主备切换
8. RAGFlow 多库检索
9. 后续账户、认证、权限扩展

## 3. 推荐后端分层

```text
backend/
  platform/
    manage.py
    config/
    apps/
      accounts/
      conversations/
      tasks/
      audit/
      configurations/
    api/
  agent_service/
    app/
      api/
      graph/
      retrieval/
      llm/
      repositories/
      schemas/
      services/
      config/
      utils/
```

## 4. 任务拆解总览

| 模块 | 任务 | 优先级 |
|---|---|---|
| Django 平台 | 服务初始化、配置、日志、API | P0 |
| 会话服务 | 会话与消息 API | P0 |
| 任务服务 | 创建任务、状态管理、取消 | P0 |
| Agent Service | 工作流承载与内部接口 | P0 |
| LangGraph | 工作流节点与状态对象 | P0 |
| Retrieval | RAGFlow 对接与统一检索结构 | P0 |
| LLM Gateway | Qwen / MiniMax 统一适配 | P0 |
| SSE | 状态和内容流式返回 | P0 |
| 持久化 | 会话、消息、任务、结果存储 | P0 |
| 认证权限预留 | 用户、角色、审计扩展点 | P1 |
| 观测 | 日志、Trace、耗时指标 | P1 |
| 容错 | 重试、回退、错误码 | P1 |

## 5. 阶段一：Django 平台层基础框架

### 任务 1：初始化 Django 服务

建议：

- `Python 3.11+`
- `Django`
- `Django REST Framework`

交付标准：

- 服务可启动
- 有健康检查接口
- 有基础配置文件

### 任务 2：建立 Django App 结构

建议至少拆分：

- `accounts`
- `conversations`
- `tasks`
- `audit`
- `configurations`

交付标准：

- App 结构清晰
- 路由可按 app 管理

### 任务 3：基础配置

内容：

- 读取环境变量
- 区分 dev/test/prod
- 加载数据库、Redis、Agent Service、模型和 RAGFlow 配置

交付标准：

- 配置项可通过 env 管理

### 任务 4：统一日志

内容：

- 请求日志
- 业务日志
- 错误日志

交付标准：

- 每次请求有 request_id
- 每个任务有 task_id

## 6. 阶段二：数据库与模型建模

### 任务 5：设计基础表结构

优先实现：

- `conversations`
- `messages`
- `tasks`
- `task_events`

预留实现：

- `users`
- `roles`
- `user_roles`
- `audit_logs`
- `system_configs`

### 任务 6：实现 Django ORM Model

要求：

- 模型字段与数据库表结构草案一致
- 预留后续用户与权限扩展字段

### 任务 7：初始化迁移文件

交付标准：

- 可一键迁移数据库
- 本地和测试环境可复用

## 7. 阶段三：会话与消息服务

### 任务 8：实现会话接口

接口：

- `GET /api/v1/conversations`
- `POST /api/v1/conversations`
- `GET /api/v1/conversations/{conversation_id}`

### 任务 9：实现消息接口

接口：

- `GET /api/v1/conversations/{conversation_id}/messages`

交付标准：

- 前端可加载历史会话和历史消息
- 会话按更新时间排序

### 任务 10：会话标题生成与更新

内容：

- 首轮消息发送后自动生成会话标题
- 刷新最后消息时间与摘要

交付标准：

- 侧边栏会话标题可读

## 8. 阶段四：任务服务

### 任务 11：任务模型设计与实现

字段建议：

- `task_id`
- `conversation_id`
- `assistant_message_id`
- `status`
- `current_step`
- `run_id`
- `error_code`
- `started_at`
- `finished_at`

### 任务 12：创建任务接口

接口：

- `POST /api/v1/conversations/{conversation_id}/messages`

动作：

- 创建用户消息
- 创建 assistant 占位消息
- 创建任务
- 调用 Agent Service
- 返回 task_id

### 任务 13：获取任务结果接口

接口：

- `GET /api/v1/solution/tasks/{task_id}`

### 任务 14：取消任务接口

接口：

- `POST /api/v1/solution/tasks/{task_id}/cancel`

交付标准：

- 前端可停止生成
- 任务状态可正确切换

## 9. 阶段五：Agent Service 基础框架

### 任务 15：初始化 Agent Service

建议：

- `Python 3.11+`
- `LangGraph`
- 可选 `FastAPI` 作为内部 HTTP 承载

职责：

- 承接 Django 平台层下发的运行任务
- 调用 LangGraph、Retrieval、LLM Gateway

### 任务 16：实现内部运行接口

接口：

- `POST /internal/agent/runs`
- `GET /internal/agent/runs/{run_id}`

交付标准：

- Django 平台层可创建内部运行任务
- 可查询运行状态

## 10. 阶段六：SSE 流式服务

### 任务 17：SSE 基础实现

接口：

- `GET /api/v1/solution/tasks/{task_id}/stream`

事件：

- `status`
- `conversation_meta`
- `message_created`
- `summary_chunk`
- `content_chunk`
- `evidence_cards`
- `completed`
- `error`

### 任务 18：事件序列管理

要求：

- 状态事件先于正文
- 正文 chunk 顺序稳定
- 完成事件仅发送一次

### 任务 19：断连容错

要求：

- 断开后前端仍可通过结果接口恢复最终内容

## 11. 阶段七：LangGraph 工作流

### 任务 20：状态对象定义

字段：

- query
- params
- normalized_intent
- normalized_context
- evidence
- outline
- final_markdown
- summary
- evidence_cards
- status
- errors

### 任务 21：实现工作流节点

节点：

1. `intent_identify`
2. `normalize_context`
3. `retrieve_documents`
4. `merge_evidence`
5. `generate_outline`
6. `expand_sections`
7. `review_solution`
8. `build_evidence_cards`
9. `finalize_output`

### 任务 22：节点状态透出

要求：

- 节点执行前更新 task 状态
- 节点执行时可推送前端友好文案

## 12. 阶段八：Retrieval Service

### 任务 23：统一检索请求结构

目标：

- LangGraph 不直接散落调用 RAGFlow

### 任务 24：RAGFlow 适配器

内容：

- 封装多 dataset 查询
- 统一返回文档结构

### 任务 25：结果清洗

内容：

- 去重
- 排序
- 分来源类型
- 取 TopN

交付标准：

- LangGraph 只接收标准化 document 列表

## 13. 阶段九：LLM Gateway

### 任务 26：统一 Provider Adapter

提供：

- `QwenAdapter`
- `MiniMaxAdapter`

### 任务 27：统一接口

实现：

- `/internal/llm/chat`
- `/internal/llm/chat/stream`

### 任务 28：模型策略配置

支持：

- 主模型
- 备用模型
- 按节点配置模型

### 任务 29：失败回退

规则：

- 主模型失败后切到备用模型

## 14. 阶段十：持久化

### 任务 30：数据库与缓存选型落地

MVP 建议：

- `PostgreSQL`
- `Redis`

### 任务 31：会话和消息存储

要求：

- 支持查询会话列表
- 支持查询历史消息

### 任务 32：任务和结果存储

要求：

- 支持任务状态查询
- 支持最终结果恢复

### 任务 33：任务事件存储

要求：

- 记录关键状态事件
- 支持问题排查

## 15. 阶段十一：认证、权限与审计预留

### 任务 34：用户与认证框架预留

要求：

- Django 用户模型可扩展
- 预留 Token / Session 认证接入点
- 前端接口预留登录态扩展能力

### 任务 35：角色与权限预留

要求：

- 预留角色字段
- 预留会话与知识访问权限控制点

### 任务 36：审计日志预留

要求：

- 记录关键操作
- 记录模型和检索调用摘要

## 16. 阶段十二：观测与稳定性

### 任务 37：耗时指标

记录：

- 检索耗时
- 模型耗时
- 总耗时

### 任务 38：错误码

实现：

- 参数错误
- 检索失败
- 模型失败
- 工作流失败

### 任务 39：链路追踪

要求：

- request_id
- task_id
- conversation_id
- run_id

## 17. 联调顺序建议

1. 健康检查
2. `meta/options`
3. 会话接口
4. 消息接口
5. 创建任务
6. Django -> Agent Service 空链路
7. SSE
8. LangGraph 空链路
9. RAGFlow 接入
10. Qwen 接入
11. MiniMax 备用接入

## 18. 验收标准

后端完成后需满足：

- 会话列表可查询
- 历史消息可查询
- 可发送消息并创建任务
- Django 平台层与 Agent Service 可联通
- SSE 可稳定推送
- LangGraph 可输出完整结构化结果
- RAGFlow 检索可用
- Qwen / MiniMax 可配置切换
- 最终结果可恢复

## 19. 推荐开发排期

### 第 1 天

- Django 平台层初始化
- 配置
- 日志

### 第 2 天

- 数据模型
- 会话/消息接口

### 第 3 天

- 任务模型
- 创建任务
- 结果接口
- 取消接口

### 第 4 天

- Agent Service 初始化
- Django 到 Agent Service 空链路
- SSE

### 第 5 天

- LangGraph 空工作流
- Retrieval Service
- RAGFlow 接入

### 第 6 天

- Qwen Adapter
- MiniMax Adapter
- 模型策略

### 第 7 天

- 联调
- 容错
- 观测

## 20. 最终建议

后端开发不要一开始就陷入“模型 prompt 微调”，优先级应该始终是：

1. 先把 Django 平台层跑通
2. 再把 Django -> Agent Service 链路跑通
3. 再把会话制链路跑通
4. 再把 SSE 跑通
5. 再把检索接通
6. 再把模型主备跑通
7. 最后再优化内容质量

这样前后端就能尽快形成一个可演示、可继续迭代的完整系统。
