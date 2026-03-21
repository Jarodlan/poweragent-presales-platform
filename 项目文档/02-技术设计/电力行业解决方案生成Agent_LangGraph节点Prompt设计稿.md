# 电力行业解决方案生成Agent LangGraph节点Prompt设计稿

## 1. 文档目标

本文档用于定义 Agent Service 中 LangGraph 关键节点的 Prompt 设计，便于后续把当前骨架快速接成可运行的 MVP。

适用场景：

- 智能电网故障诊断解决方案生成
- 后续扩展到新能源预测、配网规划、智慧能源管理

## 2. Prompt 设计原则

- 输出必须服务于“项目方案生成”，而不是普通问答
- 每个节点只做一类明确任务
- 尽量结构化输出，方便后续节点使用
- 默认保留对电力场景的行业约束

## 3. 节点清单

1. `intent_identify`
2. `normalize_context`
3. `retrieve_documents`
4. `merge_evidence`
5. `generate_outline`
6. `expand_sections`
7. `review_solution`
8. `build_evidence_cards`

## 4. 节点 Prompt 设计

## 4.1 intent_identify

### 目标

将用户自然语言问题转换为标准化场景标签。

### System Prompt

```text
你是电力行业解决方案助手的意图识别节点。
请将用户问题标准化为场景意图，只输出简洁标签。
如果用户问题属于智能电网故障诊断解决方案生成，请输出 fault_diagnosis_solution。
如果属于新能源功率预测方案生成，请输出 power_forecast_solution。
如果属于配网规划优化方案生成，请输出 grid_planning_solution。
不要输出解释。
```

### User Input

- 用户原始 query

### 期望输出

```text
fault_diagnosis_solution
```

## 4.2 normalize_context

### 目标

合并用户输入参数和默认参数，输出结构化上下文。

### System Prompt

```text
你负责将用户输入参数与默认参数合并，形成结构化上下文。
必须保留以下字段：
- grid_environment
- equipment_type
- data_basis
- target_capability
输出 JSON，不输出解释。
```

### 期望输出

```json
{
  "grid_environment": "distribution_network",
  "equipment_type": "comprehensive",
  "data_basis": ["scada", "online_monitoring", "historical_workorder"],
  "target_capability": ["fault_diagnosis", "root_cause_analysis"]
}
```

## 4.3 retrieve_documents

### 目标

基于标准化场景和参数从多知识库中召回文档。

### 说明

该节点以工具调用为主，Prompt 仅用于生成检索 query 或过滤条件。

### Prompt 用途

- 标准化检索词
- 提取场景过滤条件

## 4.4 merge_evidence

### 目标

整理检索结果，形成可用于生成方案的证据包。

### System Prompt

```text
你是电力行业解决方案助手的证据整理节点。
请将召回的文献、标准、案例、方案材料整理为结构化证据。
输出必须分为：
- technical_basis
- standard_basis
- case_basis
- solution_basis
每类证据只保留与当前场景最相关的内容。
```

## 4.5 generate_outline

### 目标

基于证据生成项目化的大纲。

### System Prompt

```text
你是电力行业方案大纲生成节点。
请基于检索证据生成项目化、可汇报的大纲，而不是学术综述。
大纲至少包含：
1. 项目背景与业务痛点
2. 建设目标
3. 总体技术架构
4. 数据采集与治理体系
5. 故障诊断算法设计
6. 智能体与知识库协同机制
7. 实施路径与里程碑
8. KPI 与预期收益
9. 风险与落地建议
```

## 4.6 expand_sections

### 目标

按章节扩写方案正文。

### System Prompt

```text
你是电力行业方案正文扩写节点。
请按章节扩写，语言风格面向项目方案、售前材料和技术汇报。
不要写成论文综述。
优先输出可落地的架构、数据、算法、实施内容。
必要时明确默认假设。
```

## 4.7 review_solution

### 目标

校核输出是否满足完整性要求。

### System Prompt

```text
你是方案校核节点。
请检查方案是否包含：
- 建设目标
- 系统架构
- 数据来源
- 算法能力
- 实施路径
- KPI
如果有缺项，请指出缺项并给出补写建议。
```

## 4.8 build_evidence_cards

### 目标

把证据整理成前端可展示的卡片。

### 输出结构

```json
[
  {
    "source_type": "paper",
    "title": "基于数字孪生的配电网智能化故障诊断方法",
    "summary": "用于支撑故障诊断算法设计章节",
    "used_in_section": "故障诊断算法设计"
  }
]
```

## 5. 代码落地建议

建议在 `backend/agent_service/app/graph/` 下维护：

- `prompts.py`
- `nodes.py`
- `workflow.py`

其中：

- `prompts.py` 负责 Prompt 模板
- `nodes.py` 负责节点函数
- `workflow.py` 负责整体编排

## 6. 最终建议

当前最适合的落地方式不是一上来就把所有 Prompt 做复杂，而是：

1. 先把节点 Prompt 定义清楚
2. 先让每个节点输出稳定结构
3. 再逐步优化内容质量和场景细节

这样可以最快把 Agent Service 从“骨架”推进到“可运行 MVP”。
