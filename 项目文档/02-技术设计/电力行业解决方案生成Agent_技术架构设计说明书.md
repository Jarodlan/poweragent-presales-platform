# 电力行业解决方案生成Agent 技术架构设计说明书

## 1. 文档信息

- `文档名称`：电力行业解决方案生成Agent 技术架构设计说明书
- `技术栈`：`Vue 3 + LangGraph + RAGFlow`
- `模型提供方`：`Qwen + MiniMax`
- `文档版本`：v1.0
- `日期`：2026-03-20
- `适用阶段`：MVP / Demo
- `当前智能体版本`：`0.1.0-mvp`

## 2. 设计目标

本系统目标是构建一个面向电力行业方案生成的智能体 Demo，支持用户输入如：

`给我提供一个智能电网故障诊断的解决方案`

系统自动完成：

1. 意图识别与场景标准化
2. 多知识库检索
3. 方案大纲生成
4. 分章节扩写
5. 方案质量校核
6. 证据卡生成
7. 流式输出到前端
8. 承接客户需求分析报告并生成方案草稿

核心要求：

- 输出必须更像“项目方案”，而不是普通问答
- 系统必须可扩展到更多电力场景
- 模型提供方可灵活切换
- 检索与编排解耦
- 前端不暴露任何模型或知识库密钥

## 3. 总体架构

```mermaid
flowchart LR
    U["用户"] --> V["Vue 前端"]
    CD["客户需求分析报告页"] --> V
    V --> DJ["Django Platform API"]
    DJ --> AG["Agent Service"]
    AG --> LG["LangGraph Orchestrator"]
    LG --> RET["Retrieval Service"]
    RET --> R1["RAGFlow 文献库"]
    RET --> R2["RAGFlow 标准库"]
    RET --> R3["RAGFlow 案例库"]
    RET --> R4["RAGFlow 方案库"]
    LG --> LLM["LLM Gateway"]
    LLM --> QW["Qwen Adapter"]
    LLM --> MM["MiniMax Adapter"]
    DJ --> DB["PostgreSQL / Redis"]
    DJ --> AUTH["Auth / Permission / Audit"]
    AG --> OBS["日志 / Trace / Metrics"]
    DJ --> SSE["SSE 流式事件输出"]
    SSE --> V
```

## 4. 分层设计

## 4.1 前端层

技术建议：

- `Vue 3`
- `Vite`
- `Element Plus`
- `Pinia`
- `markdown-it`

职责：

- 接收用户需求输入
- 展示会话侧边栏和历史会话
- 提供参数选择
- 发起方案生成请求
- 订阅 SSE 状态流
- 加载历史消息
- 渲染方案正文与证据卡片
- 支持复制摘要和全文
- 支持从客户需求分析报告页导入方案草稿
- 支持导入前人工确认与参数调整

不负责：

- 直接调用模型 API
- 直接调用 RAGFlow
- 管理任务编排逻辑

## 4.2 Django 平台层

建议使用：

- `Django`
- `Django REST Framework`
- `Django ORM`

职责：

- 接收前端请求
- 提供会话列表与消息查询接口
- 创建任务 ID
- 调用 Agent Service
- 负责 SSE 状态透出
- 统一返回前端结果结构
- 屏蔽内部模型、RAGFlow 和 LangGraph 细节
- 负责承接客户需求分析结果与方案工作台会话生命周期

## 4.3 Agent Service

建议使用：

- `Python`
- `LangGraph`
- 可选 `FastAPI` 作为内部 HTTP 承载层

职责：

- 维护工作流状态
- 驱动节点有序执行
- 根据场景决定检索和模型调用路径
- 汇总结构化输出对象
- 根据导入草稿中的场景与参数执行对应工作流

优势：

- 支持显式状态机
- 适合多步骤行业 Agent
- 便于观察每个节点耗时与质量

## 4.4 检索层

技术：

- `RAGFlow`

职责：

- 文档解析
- 切片与召回
- 引用追溯
- 按知识库分类返回结果

本项目中 RAGFlow 定位为：

`知识库平台与检索执行层`

不建议在首期将 RAGFlow 直接作为完整 Agent 编排中心使用。

## 4.5 模型网关层

技术建议：

- 自建 `LLM Gateway`
- 在服务内部实现统一 Provider Adapter

职责：

- 屏蔽 Qwen / MiniMax 差异
- 统一流式与非流式响应结构
- 处理超时、重试、回退
- 管理模型选择策略

## 5. 与客户需求分析智能体的交接

当前架构已支持：

1. 从客户需求分析正式报告中抽取结构化字段
2. 自动推断最可能的方案场景
3. 自动加载对应参数预设
4. 在前端确认弹窗中允许用户修改文本与参数
5. 将确认后的草稿带入方案工作台

该交接动作当前采用前端受控导入方式，不直接触发后端生成任务，目的是保留人工确认环节并降低误生成风险。

## 6. 模型接入设计

## 6.1 设计原则

由于本项目使用 `Qwen + MiniMax` 两家模型，架构上不允许业务节点直接绑定某一家 SDK。所有模型调用必须走统一的 `LLM Gateway`。

统一目标：

- 统一输入格式
- 统一输出格式
- 统一异常处理
- 统一流式事件结构

## 6.2 模型选型建议

基于 2026 年 3 月 20 日可查的官方文档，我建议采用如下模型策略：

### Qwen 侧

- `qwen3.5-plus`
  - 作为主力通用模型
  - 适合意图识别、归并整理、章节扩写

- `qwen-max-latest`
  - 作为复杂方案生成 / 质量校核的高质量模型
  - 用于复杂推理和最终润色

说明：

- 这是基于官方文档中“Plus 为多数场景推荐选择、Max 适合复杂多步骤任务”的能力描述作出的工程推断

### MiniMax 侧

- `MiniMax-M2.7`
  - 当前最新文本主力模型
  - 用于方案生成与复杂任务备选

- `MiniMax-M2.7-highspeed`
  - 当前最新高速版
  - 用于低延迟节点

## 6.3 模型职责分配建议

### 方案A：Qwen 主、MiniMax 备

- `intent_identify` -> `qwen3.5-plus`
- `normalize_context` -> `qwen3.5-plus`
- `generate_outline` -> `qwen-max-latest`
- `expand_sections` -> `qwen3.5-plus`
- `review_solution` -> `qwen-max-latest`
- 异常回退 -> `MiniMax-M2.7`

适合：

- 更强调行业内容稳定性
- 更依赖 Qwen 的中文与推理表现

### 方案B：双模型分工

- `intent_identify` -> `qwen3.5-plus`
- `generate_outline` -> `MiniMax-M2.7`
- `expand_sections` -> `MiniMax-M2.7-highspeed`
- `review_solution` -> `qwen-max-latest`

适合：

- 希望兼顾速度与不同模型风格
- 需要 Demo 上体现“双模型融合能力”

### MVP 推荐

建议先采用：

`方案A`

原因：

- 逻辑更稳定
- 调试更简单
- 出问题时更容易定位

## 5.4 统一模型适配接口

服务内部定义统一接口：

```ts
interface LLMRequest {
  provider: "qwen" | "minimax";
  model: string;
  messages: Array<{ role: "system" | "user" | "assistant"; content: string }>;
  temperature?: number;
  maxTokens?: number;
  stream?: boolean;
  metadata?: Record<string, any>;
}

interface LLMResponse {
  provider: "qwen" | "minimax";
  model: string;
  content: string;
  reasoning?: string;
  usage?: Record<string, any>;
  raw?: any;
}
```

## 5.5 外部模型接口兼容策略

为了降低工程复杂度，建议：

- `Qwen`：统一走 OpenAI 兼容接口
- `MiniMax`：统一走 OpenAI 兼容接口

这样 LangGraph 侧可统一使用 OpenAI 兼容客户端封装。

### Qwen 接口配置建议

- `base_url`: `https://dashscope.aliyuncs.com/compatible-mode/v1`
- 兼容方式：`Chat Completions`

### MiniMax 接口配置建议

- `base_url`: `https://api.minimaxi.com/v1`
- 兼容方式：`Chat Completions`

说明：

- Qwen 官方同时支持 `Responses API` 和 `Chat Completions API`
- MiniMax 官方文本模型支持 `HTTP / Anthropic SDK / OpenAI SDK`
- 为统一工程实现，MVP 优先统一为 OpenAI 兼容的 Chat API

## 6. LangGraph 工作流设计

## 6.1 核心状态对象

```json
{
  "task_id": "",
  "query": "",
  "params": {
    "grid_environment": "",
    "equipment_type": "",
    "data_basis": [],
    "target_capability": []
  },
  "normalized_intent": "",
  "normalized_context": {},
  "documents": [],
  "evidence": {
    "papers": [],
    "standards": [],
    "cases": [],
    "solutions": []
  },
  "outline": "",
  "sections": [],
  "summary": "",
  "final_markdown": "",
  "evidence_cards": [],
  "assumptions": [],
  "status": "",
  "errors": []
}
```

## 6.2 节点拆分

### `intent_identify`

职责：

- 判断用户是否属于电力方案生成场景
- 输出标准化意图

输入：

- `query`

输出：

- `normalized_intent`

### `normalize_context`

职责：

- 合并默认参数与用户选择参数
- 形成标准上下文

### `retrieve_documents`

职责：

- 调用 Retrieval Service
- 并发请求 RAGFlow 多知识库

### `merge_evidence`

职责：

- 去重
- 按来源分组
- 选择 TopN

### `generate_outline`

职责：

- 先输出方案骨架

### `expand_sections`

职责：

- 按章节扩写正文

### `review_solution`

职责：

- 检查方案完整性
- 对缺失项做补写

### `build_evidence_cards`

职责：

- 为前端生成证据卡对象

### `finalize_output`

职责：

- 生成最终返回 JSON

## 6.3 推荐状态流

前端可接收以下状态：

- `intent_identifying`
- `context_normalizing`
- `retrieving_documents`
- `merging_evidence`
- `generating_outline`
- `expanding_sections`
- `reviewing_solution`
- `building_evidence_cards`
- `completed`
- `failed`

## 7. Retrieval Service 设计

## 7.1 设计原因

不建议 LangGraph 直接散落调用多个 RAGFlow API。应增加一层 `Retrieval Service`，作为检索中间层。

职责：

- 接收标准化检索请求
- 路由到不同 RAGFlow dataset
- 整理统一返回格式
- 后续可接入重排、过滤、缓存

## 7.2 统一检索请求结构

```json
{
  "intent": "fault_diagnosis_solution",
  "query": "智能电网故障诊断",
  "filters": {
    "grid_environment": "distribution_network",
    "equipment_type": "comprehensive"
  },
  "top_k": 8
}
```

## 7.3 统一检索返回结构

```json
{
  "documents": [
    {
      "source_type": "case",
      "title": "string",
      "snippet": "string",
      "score": 0.92,
      "metadata": {},
      "reference": {}
    }
  ]
}
```

## 8. 数据存储设计

## 8.1 任务存储

建议使用：

- `PostgreSQL`
- `Redis`

存储内容：

- 会话基础信息
- 消息列表
- 任务状态
- 流式输出片段
- 最终结果
- 错误信息

## 8.2 日志与观测

至少记录：

- task_id
- 节点名称
- 模型名
- 提示词版本
- 检索耗时
- 模型耗时
- 总耗时
- 错误码

建议接入：

- 结构化日志
- Trace ID
- Prometheus / Grafana 或等价方案

## 9. 前端架构设计

## 9.1 页面结构

采用 ChatGPT 风格单页工作台：

- `WorkspaceView`

子组件建议：

- `ConversationSidebar`
- `ConversationList`
- `ChatMessageList`
- `MessageComposer`
- `ScenarioParamDrawer`
- `RunStatusTimeline`
- `SolutionSummaryCard`
- `SolutionMarkdownView`
- `EvidenceCardList`

## 9.2 状态管理

建议使用 `Pinia` 管理：

- 会话列表
- 当前会话
- 消息列表
- 输入参数
- 任务状态
- SSE 事件流
- 最终结果对象

## 9.3 渲染策略

- 左侧会话列表分页或分组加载
- 切换会话时先显示历史消息，再按需请求增量结果
- 状态区实时刷新
- 正文区流式追加
- 证据卡在最终结果或阶段性结果后刷新

## 10. 配置设计

## 10.1 环境变量

```bash
# Frontend
VITE_API_BASE_URL=http://localhost:8000

# Django Platform
DJANGO_ENV=dev
DJANGO_PORT=8000
DJANGO_SECRET_KEY=***
POSTGRES_URL=postgresql://user:pass@localhost:5432/power_agent
REDIS_URL=redis://localhost:6379/0

# Agent Service
AGENT_SERVICE_BASE_URL=http://localhost:9000
AGENT_SERVICE_TIMEOUT=120

# Qwen
DASHSCOPE_API_KEY=***
DASHSCOPE_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
QWEN_DEFAULT_MODEL=qwen3.5-plus
QWEN_REVIEW_MODEL=qwen-max-latest

# MiniMax
MINIMAX_API_KEY=***
MINIMAX_BASE_URL=https://api.minimaxi.com/v1
MINIMAX_DEFAULT_MODEL=MiniMax-M2.7
MINIMAX_FAST_MODEL=MiniMax-M2.7-highspeed

# RAGFlow
RAGFLOW_BASE_URL=http://ragflow.internal
RAGFLOW_API_KEY=***
RAGFLOW_DATASET_PAPERS=power_papers
RAGFLOW_DATASET_STANDARDS=power_standards
RAGFLOW_DATASET_CASES=power_cases
RAGFLOW_DATASET_SOLUTIONS=power_solutions
```

## 10.2 模型策略配置

建议把模型策略抽成配置项，而不是写死在代码里。

例如：

```json
{
  "intent_identify": {
    "primary": { "provider": "qwen", "model": "qwen3.5-plus" },
    "fallback": { "provider": "minimax", "model": "MiniMax-M2.7-highspeed" }
  },
  "generate_outline": {
    "primary": { "provider": "qwen", "model": "qwen-max-latest" },
    "fallback": { "provider": "minimax", "model": "MiniMax-M2.7" }
  },
  "expand_sections": {
    "primary": { "provider": "qwen", "model": "qwen3.5-plus" },
    "fallback": { "provider": "minimax", "model": "MiniMax-M2.7" }
  }
}
```

## 11. 流式输出设计

## 11.1 协议

前端与 Django 平台层之间使用：

- `SSE`

原因：

- 浏览器原生支持较好
- 适合单向流式状态输出
- 实现比 WebSocket 更轻

## 11.2 事件类型

- `status`
- `conversation_meta`
- `message_created`
- `summary_chunk`
- `content_chunk`
- `evidence_cards`
- `completed`
- `error`

## 12. 容错与回退设计

## 12.1 模型失败回退

规则：

- Qwen 主调用失败 -> 回退到 MiniMax
- MiniMax 主调用失败 -> 回退到 Qwen

## 12.2 检索失败回退

规则：

- 某一类知识库失败时，允许其他库先继续
- 若全部失败，则进入“无知识增强”兜底生成，但结果中标记：
  - `evidence_insufficient = true`

## 12.3 超时控制

建议超时：

- 意图识别：15 秒
- 检索：20 秒
- 大纲生成：20 秒
- 章节扩写：40 秒
- 全任务：60 秒

## 13. 安全设计

MVP 阶段至少保证：

- API Key 仅存在服务端
- 前端不暴露模型调用地址
- RAGFlow 不对前端直连开放
- 记录基本访问日志
- 错误信息不泄露敏感配置

## 14. 研发落地建议

## 14.1 推荐目录结构

```text
project/
  frontend/
    src/
      views/
      components/
      stores/
      services/
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
        llm/
        retrieval/
        schemas/
        services/
        config/
        utils/
```

## 14.2 开发顺序

1. 先打通前端 -> Django 平台层 -> Agent Service 空链路
2. 再接通会话、消息和任务状态
3. 再接通 RAGFlow 检索
4. 再接通 Qwen / MiniMax 统一适配
5. 再实现完整工作流
6. 最后优化内容质量和页面表现

## 15. 最终判断

本项目最核心的技术原则是：

`Django 负责平台层`
`RAGFlow 负责知识库`
`LangGraph 负责编排`
`Vue 负责产品体验`
`Qwen + MiniMax 通过统一网关接入`

只要把这四层边界守住，后续无论你要替换模型、扩展场景、增加知识库还是做正式产品化，都会更顺畅。
