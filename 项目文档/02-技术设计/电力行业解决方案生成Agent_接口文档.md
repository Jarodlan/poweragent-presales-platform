# 电力行业解决方案生成Agent 接口文档

## 1. 文档信息

- `文档名称`：电力行业解决方案生成Agent 接口文档
- `适用系统`：Vue 前端 / Django Platform API / Agent Service / RAGFlow / LLM Gateway
- `文档版本`：v1.0
- `日期`：2026-03-20

## 2. 说明

本文档定义：

1. 前端对 Django 平台层的业务接口
2. Django 平台层对 Agent Service 的内部接口
3. Agent Service 对 Retrieval Service 的检索接口
4. LLM Gateway 的统一模型调用接口

目标是让前后端工程师、Agent 工程师能按统一协议联调。

## 3. 约定

## 3.1 通用响应格式

非流式接口统一返回：

```json
{
  "code": 0,
  "message": "ok",
  "data": {}
}
```

错误时：

```json
{
  "code": 10001,
  "message": "invalid request",
  "data": null
}
```

## 3.2 通用 Header

请求头：

- `Content-Type: application/json`
- `X-Request-Id: <uuid>` 可选

响应头：

- `X-Request-Id: <uuid>`

## 3.3 状态码约定

- `200`：成功
- `400`：请求参数错误
- `401`：未授权
- `404`：资源不存在
- `409`：任务状态冲突
- `500`：服务异常

## 4. 前端 -> Django 平台层接口

## 4.1 获取页面初始化配置

### 请求

`GET /api/v1/meta/options`

### 说明

获取前端下拉框配置、默认参数和可选场景。

### 响应示例

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "grid_environment_options": [
      { "label": "配电网", "value": "distribution_network" },
      { "label": "输电网", "value": "transmission_network" },
      { "label": "园区微网", "value": "microgrid" },
      { "label": "综合能源场景", "value": "integrated_energy" }
    ],
    "equipment_type_options": [
      { "label": "线路", "value": "line" },
      { "label": "变压器", "value": "transformer" },
      { "label": "开关柜", "value": "switchgear" },
      { "label": "综合故障", "value": "comprehensive" }
    ],
    "data_basis_options": [
      { "label": "SCADA", "value": "scada" },
      { "label": "在线监测", "value": "online_monitoring" },
      { "label": "历史工单", "value": "historical_workorder" },
      { "label": "图像巡检", "value": "inspection_image" }
    ],
    "target_capability_options": [
      { "label": "故障预警", "value": "fault_warning" },
      { "label": "故障诊断", "value": "fault_diagnosis" },
      { "label": "根因分析", "value": "root_cause_analysis" },
      { "label": "辅助处置", "value": "assisted_dispatch" }
    ],
    "default_params": {
      "grid_environment": "distribution_network",
      "equipment_type": "comprehensive",
      "data_basis": ["scada", "online_monitoring", "historical_workorder"],
      "target_capability": ["fault_diagnosis", "root_cause_analysis"]
    }
  }
}
```

## 4.2 获取会话列表

### 请求

`GET /api/v1/conversations?page=1&page_size=20`

### 说明

返回侧边栏会话列表，按最近更新时间倒序。

### 响应示例

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "items": [
      {
        "conversation_id": "conv_001",
        "title": "智能电网故障诊断解决方案",
        "last_user_message": "给我提供一个智能电网故障诊断的解决方案",
        "last_message_at": "2026-03-20T10:12:30+08:00",
        "status": "idle"
      }
    ],
    "page": 1,
    "page_size": 20,
    "has_more": false
  }
}
```

## 4.3 创建会话

### 请求

`POST /api/v1/conversations`

### 请求体

```json
{
  "title": ""
}
```

### 说明

- `title` 可空
- 若为空，系统根据首轮用户消息自动生成标题

### 响应示例

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "conversation_id": "conv_001",
    "title": "",
    "status": "idle"
  }
}
```

## 4.4 获取会话详情

### 请求

`GET /api/v1/conversations/{conversation_id}`

### 响应示例

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "conversation_id": "conv_001",
    "title": "智能电网故障诊断解决方案",
    "created_at": "2026-03-20T10:12:00+08:00",
    "updated_at": "2026-03-20T10:12:30+08:00",
    "status": "idle"
  }
}
```

## 4.5 获取会话消息

### 请求

`GET /api/v1/conversations/{conversation_id}/messages?page=1&page_size=50`

### 响应示例

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "conversation_id": "conv_001",
    "items": [
      {
        "message_id": "msg_user_001",
        "role": "user",
        "content": "给我提供一个智能电网故障诊断的解决方案",
        "created_at": "2026-03-20T10:12:00+08:00"
      },
      {
        "message_id": "msg_assistant_001",
        "role": "assistant",
        "status": "completed",
        "summary": "本方案面向配电网故障诊断场景...",
        "content": "# 智能电网故障诊断解决方案\n...",
        "assumptions": [
          "默认按配电网场景生成"
        ],
        "evidence_cards": [],
        "created_at": "2026-03-20T10:12:30+08:00"
      }
    ],
    "page": 1,
    "page_size": 50,
    "has_more": false
  }
}
```

## 4.6 在会话中发送消息并创建任务

### 请求

`POST /api/v1/conversations/{conversation_id}/messages`

### 请求体

```json
{
  "query": "给我提供一个智能电网故障诊断的解决方案",
  "params": {
    "grid_environment": "distribution_network",
    "equipment_type": "comprehensive",
    "data_basis": ["scada", "online_monitoring", "historical_workorder"],
    "target_capability": ["fault_diagnosis", "root_cause_analysis"]
  },
  "client_meta": {
    "source": "web",
    "trace_id": "b75d4a9c-1111-4444-8888-8eae8ff1d4aa"
  }
}
```

### 字段说明

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `query` | string | 是 | 用户原始需求 |
| `params.grid_environment` | string | 否 | 电网场景 |
| `params.equipment_type` | string | 否 | 诊断对象 |
| `params.data_basis` | string[] | 否 | 数据基础 |
| `params.target_capability` | string[] | 否 | 目标能力 |
| `client_meta.source` | string | 否 | 来源标识 |
| `client_meta.trace_id` | string | 否 | 前端追踪 ID |

### 响应示例

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "conversation_id": "conv_001",
    "user_message_id": "msg_user_002",
    "assistant_message_id": "msg_assistant_002",
    "task_id": "task_20260320_0001",
    "status": "running",
    "stream_url": "/api/v1/solution/tasks/task_20260320_0001/stream",
    "result_url": "/api/v1/solution/tasks/task_20260320_0001"
  }
}
```

## 4.7 订阅任务流

### 请求

`GET /api/v1/solution/tasks/{task_id}/stream`

### 说明

使用 `SSE` 返回状态、正文增量和结果。

### 事件类型

#### 1. `status`

```json
{
  "event": "status",
  "data": {
    "conversation_id": "conv_001",
    "assistant_message_id": "msg_assistant_002",
    "task_id": "task_20260320_0001",
    "step": "retrieving_documents",
    "message": "正在检索行业知识",
    "progress": 35
  }
}
```

#### 2. `conversation_meta`

```json
{
  "event": "conversation_meta",
  "data": {
    "conversation_id": "conv_001",
    "title": "智能电网故障诊断解决方案"
  }
}
```

#### 3. `message_created`

```json
{
  "event": "message_created",
  "data": {
    "conversation_id": "conv_001",
    "user_message_id": "msg_user_002",
    "assistant_message_id": "msg_assistant_002"
  }
}
```

#### 4. `summary_chunk`

```json
{
  "event": "summary_chunk",
  "data": {
    "conversation_id": "conv_001",
    "assistant_message_id": "msg_assistant_002",
    "task_id": "task_20260320_0001",
    "content": "本方案面向配电网故障诊断场景，采用..."
  }
}
```

#### 5. `content_chunk`

```json
{
  "event": "content_chunk",
  "data": {
    "conversation_id": "conv_001",
    "assistant_message_id": "msg_assistant_002",
    "task_id": "task_20260320_0001",
    "content": "## 一、项目背景\n..."
  }
}
```

#### 6. `evidence_cards`

```json
{
  "event": "evidence_cards",
  "data": {
    "conversation_id": "conv_001",
    "assistant_message_id": "msg_assistant_002",
    "task_id": "task_20260320_0001",
    "items": [
      {
        "id": "ev_001",
        "source_type": "paper",
        "title": "基于数字孪生的配电网智能化故障诊断方法",
        "summary": "用于支撑故障诊断算法设计章节",
        "used_in_section": "故障诊断算法设计",
        "metadata": {}
      }
    ]
  }
}
```

#### 7. `completed`

```json
{
  "event": "completed",
  "data": {
    "conversation_id": "conv_001",
    "assistant_message_id": "msg_assistant_002",
    "task_id": "task_20260320_0001",
    "status": "completed"
  }
}
```

#### 8. `error`

```json
{
  "event": "error",
  "data": {
    "conversation_id": "conv_001",
    "assistant_message_id": "msg_assistant_002",
    "task_id": "task_20260320_0001",
    "code": 50001,
    "message": "方案生成失败，请稍后重试"
  }
}
```

## 4.8 获取任务结果

### 请求

`GET /api/v1/solution/tasks/{task_id}`

### 响应示例

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "conversation_id": "conv_001",
    "assistant_message_id": "msg_assistant_002",
    "task_id": "task_20260320_0001",
    "status": "completed",
    "summary": "本方案面向配电网故障诊断场景...",
    "final_markdown": "# 智能电网故障诊断解决方案\n...",
    "assumptions": [
      "默认按配电网场景生成",
      "默认输入数据包括 SCADA 与在线监测数据"
    ],
    "evidence_cards": [
      {
        "id": "ev_001",
        "source_type": "paper",
        "title": "基于数字孪生的配电网智能化故障诊断方法",
        "summary": "用于支撑故障诊断算法设计章节",
        "used_in_section": "故障诊断算法设计",
        "metadata": {}
      }
    ],
    "metrics": {
      "total_latency_ms": 28430,
      "retrieval_latency_ms": 3210,
      "generation_latency_ms": 20221
    }
  }
}
```

## 4.9 取消任务

### 请求

`POST /api/v1/solution/tasks/{task_id}/cancel`

### 响应示例

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "task_id": "task_20260320_0001",
    "status": "cancelled"
  }
}
```

## 5. Django 平台层 -> Agent Service 接口

说明：

- Django 平台层对前端暴露业务接口
- 平台层对 Agent Service 暴露内部接口或通过内部 HTTP 调用

## 5.1 创建运行任务

`POST /internal/agent/runs`

### 请求体

```json
{
  "task_id": "task_20260320_0001",
  "conversation_id": "conv_001",
  "assistant_message_id": "msg_assistant_002",
  "query": "给我提供一个智能电网故障诊断的解决方案",
  "params": {
    "grid_environment": "distribution_network",
    "equipment_type": "comprehensive",
    "data_basis": ["scada", "online_monitoring", "historical_workorder"],
    "target_capability": ["fault_diagnosis", "root_cause_analysis"]
  }
}
```

### 响应

```json
{
  "run_id": "run_001",
  "status": "started"
}
```

## 5.2 获取运行状态

`GET /internal/agent/runs/{run_id}`

### 响应

```json
{
  "run_id": "run_001",
  "status": "expanding_sections",
  "step": "expand_sections",
  "progress": 75
}
```

## 6. Agent Service -> Retrieval Service 接口

## 6.1 检索请求

`POST /internal/retrieval/search`

### 请求体

```json
{
  "intent": "fault_diagnosis_solution",
  "query": "智能电网故障诊断",
  "filters": {
    "grid_environment": "distribution_network",
    "equipment_type": "comprehensive"
  },
  "top_k": 8,
  "datasets": ["power_cases", "power_solutions", "power_papers", "power_standards"]
}
```

### 响应

```json
{
  "documents": [
    {
      "source_type": "case",
      "title": "某配电网故障诊断案例",
      "snippet": "通过在线监测和工单复盘实现故障定位...",
      "score": 0.93,
      "metadata": {
        "scenario": "fault_diagnosis",
        "grid_environment": "distribution_network"
      },
      "reference": {
        "dataset": "power_cases",
        "doc_id": "doc_001",
        "chunk_id": "chunk_001"
      }
    }
  ]
}
```

## 7. Retrieval Service -> RAGFlow 接口适配约定

说明：

- 对 RAGFlow 的具体 API 细节，在服务代码中封装
- 对 LangGraph 层统一输出标准结果

内部适配流程：

1. 根据 dataset 列表组装 RAGFlow 查询
2. 对每个 dataset 请求检索
3. 汇总结果
4. 做去重与排序
5. 返回统一结构

## 8. Agent Service -> LLM Gateway 接口

## 8.1 统一文本生成接口

`POST /internal/llm/chat`

### 请求体

```json
{
  "provider": "qwen",
  "model": "qwen3.5-plus",
  "messages": [
    {
      "role": "system",
      "content": "你是电力行业解决方案助手。"
    },
    {
      "role": "user",
      "content": "请将用户需求标准化。"
    }
  ],
  "temperature": 0.2,
  "max_tokens": 2048,
  "stream": false,
  "metadata": {
    "task_id": "task_20260320_0001",
    "node": "intent_identify"
  }
}
```

### 响应体

```json
{
  "provider": "qwen",
  "model": "qwen3.5-plus",
  "content": "智能电网故障诊断",
  "reasoning": "",
  "usage": {
    "input_tokens": 120,
    "output_tokens": 18,
    "total_tokens": 138
  },
  "raw": {}
}
```

## 8.2 统一流式文本生成接口

`POST /internal/llm/chat/stream`

### 响应方式

SSE 或服务内部异步生成器。

### 流式事件建议

- `delta`
- `completed`
- `error`

## 9. 外部模型适配约定

## 9.1 Qwen 适配

### 接入方式

- OpenAI 兼容 `Chat Completions API`

### 配置建议

```bash
DASHSCOPE_API_KEY=***
DASHSCOPE_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
```

### 推荐模型

- `qwen3.5-plus`
- `qwen-max-latest`

### 工程建议

- 意图识别、上下文标准化优先 `qwen3.5-plus`
- 最终质量校核优先 `qwen-max-latest`

## 9.2 MiniMax 适配

### 接入方式

- OpenAI 兼容 `Chat Completions API`

### 配置建议

```bash
MINIMAX_API_KEY=***
MINIMAX_BASE_URL=https://api.minimaxi.com/v1
```

### 推荐模型

- `MiniMax-M2.7`
- `MiniMax-M2.7-highspeed`

### 工程建议

- 可作为复杂方案生成或回退模型
- 高速节点可优先使用 `MiniMax-M2.7-highspeed`

## 10. 任务结果对象定义

统一结果对象：

```json
{
  "conversation_id": "string",
  "assistant_message_id": "string",
  "task_id": "string",
  "status": "running|completed|failed|cancelled",
  "query": "string",
  "normalized_intent": "string",
  "summary": "string",
  "final_markdown": "string",
  "assumptions": ["string"],
  "evidence_cards": [
    {
      "id": "string",
      "source_type": "paper|standard|case|solution",
      "title": "string",
      "summary": "string",
      "used_in_section": "string",
      "metadata": {}
    }
  ],
  "metrics": {
    "total_latency_ms": 0,
    "retrieval_latency_ms": 0,
    "generation_latency_ms": 0
  },
  "error": null
}
```

## 11. 错误码定义

| code | 含义 | 说明 |
|---|---|---|
| `10001` | 参数错误 | query 为空或格式错误 |
| `10002` | 任务不存在 | task_id 无效 |
| `10003` | 任务状态冲突 | 已完成任务不可重复取消 |
| `20001` | 检索失败 | RAGFlow 调用失败 |
| `30001` | 模型调用失败 | Qwen / MiniMax 调用失败 |
| `30002` | 模型超时 | 模型响应超时 |
| `40001` | 工作流失败 | LangGraph 节点执行异常 |
| `50001` | 系统内部错误 | 未分类异常 |

## 12. 超时与重试策略

## 12.1 接口超时

- 创建任务接口：10 秒
- 检索接口：20 秒
- 单次模型调用：40 秒
- 全任务：60 秒

## 12.2 重试规则

- 检索失败：重试 1 次
- 模型调用失败：同模型重试 1 次，失败后切换到备用模型
- SSE 中断：前端允许重新获取结果接口

## 13. 示例交互链路

### 第一步：前端创建任务

`POST /api/v1/conversations/{conversation_id}/messages`

返回 `task_id`

### 第二步：前端订阅任务流

`GET /api/v1/solution/tasks/{task_id}/stream`

接收状态：

- 正在识别业务场景
- 正在检索行业知识
- 正在生成方案结构
- 正在扩写完整方案
- 正在校核输出质量

### 第三步：完成后获取结果

`GET /api/v1/solution/tasks/{task_id}`

返回：

- 摘要
- 正文
- 证据卡
- 耗时指标

## 14. 接口验收标准

满足以下条件视为接口层通过验收：

1. 前端可成功创建任务
2. 前端可稳定接收 SSE 状态流
3. LangGraph 可调用检索与模型服务
4. 最终结果对象结构稳定
5. Qwen 与 MiniMax 可按配置切换
6. 出错时能返回可识别错误码

## 15. 最终建议

接口层的关键不是“先接多少功能”，而是先把下面三件事做对：

1. `统一任务对象`
2. `统一流式协议`
3. `统一模型适配接口`

只要这三个基础协议稳定，后面扩场景、扩知识库、换模型提供方，工程成本都会低很多。
