# 飞书 CRM 接口设计文档

## 1. 文档目的

本文档用于明确 `PowerAgent 平台` 与 `飞书多维表格 CRM` 之间的一期接口设计，覆盖：

- 客户主档查询与绑定
- 商机记录查询与绑定
- 跟进记录写入
- 附件索引写入
- 平台对象到飞书 CRM 的映射字段口径
- 一期最小可用接口边界

本文档默认前提为：

- 飞书多维表格作为当前阶段的 `CRM 主数据层`
- PowerAgent 平台作为 `智能体处理层 + 流程流转层 + 协同执行层`
- 客户、商机、联系人等主数据优先维护在飞书侧
- 平台保存必要的 `crm_*` 外键与业务快照，不自建完整 CRM 界面

---

## 2. 一期接口设计原则

### 2.1 平台不直接暴露飞书原始对象给前端

前端不直接操作：

- `app_token`
- `table_id`
- 飞书原始字段 ID
- 飞书原始 API 结构

前端只面向平台内部语义化接口：

- 客户搜索
- 商机搜索
- 绑定 CRM 记录
- 写入 CRM 跟进记录
- 写入 CRM 附件索引

### 2.2 平台后端负责字段映射

平台后端负责完成：

- 平台字段 -> 飞书多维表格字段 的转换
- 关联记录 ID 的保存
- 写入失败重试与审计留痕

### 2.3 一期先做“平台驱动写回”

一期不建议先做：

- 飞书多维表格主动推送回平台
- 飞书表格 Webhook 反向驱动平台

一期推荐先做：

- 平台查询飞书 CRM 数据
- 平台在关键节点回写飞书 CRM

---

## 3. 基础配置项

后端建议增加以下配置：

- `FEISHU_CRM_ENABLED`
- `FEISHU_BITABLE_APP_TOKEN`
- `FEISHU_CRM_CUSTOMER_TABLE_ID`
- `FEISHU_CRM_CONTACT_TABLE_ID`
- `FEISHU_CRM_OPPORTUNITY_TABLE_ID`
- `FEISHU_CRM_FOLLOWUP_TABLE_ID`
- `FEISHU_CRM_ATTACHMENT_TABLE_ID`
- `FEISHU_CRM_SYNC_ENABLED`
- `FEISHU_CRM_WRITEBACK_ENABLED`

说明：

- `FEISHU_BITABLE_APP_TOKEN` 对应一套 CRM 多维表格应用
- 各 `TABLE_ID` 对应客户、联系人、商机、跟进、附件等表
- `SYNC_ENABLED` 控制查询与绑定能力
- `WRITEBACK_ENABLED` 控制需求分析/方案结果/售前任务等业务写回能力

---

## 4. 建议新增的数据对象

平台后端建议增加一类轻量写回记录表，例如：

- `crm_writeback_record`

建议字段：

- `id`
- `provider`：固定为 `feishu_bitable`
- `object_type`
  - `customer_demand_session`
  - `customer_demand_report`
  - `solution_session`
  - `solution_result`
  - `presales_task`
  - `archive_record`
- `object_id`
- `target_table`
  - `customer`
  - `opportunity`
  - `followup`
  - `attachment`
- `target_record_id`
- `action`
  - `bind`
  - `create_record`
  - `update_record`
- `status`
  - `pending`
  - `success`
  - `failed`
- `request_payload`
- `response_payload`
- `error_message`
- `created_by`
- `created_at`

用途：

- 审计写回行为
- 排查映射错误
- 后续补偿重试

---

## 5. 平台统一返回结构建议

### 5.1 CRM 客户记录

```json
{
  "provider": "feishu_bitable",
  "base_id": "app_xxx",
  "table": "customer",
  "record_id": "rec_xxx",
  "name": "常州大通工业园",
  "industry": "工业园区",
  "region": "江苏常州",
  "level": "重点客户",
  "owner_name": "霸天",
  "last_followup_at": "2026-03-26T10:30:00+08:00"
}
```

### 5.2 CRM 商机记录

```json
{
  "provider": "feishu_bitable",
  "base_id": "app_xxx",
  "table": "opportunity",
  "record_id": "rec_yyy",
  "customer_record_id": "rec_xxx",
  "name": "常州大通工业园储能优化项目",
  "stage": "方案推进",
  "amount": "待评估",
  "owner_name": "霸天",
  "next_followup_at": "2026-03-30T14:00:00+08:00"
}
```

---

## 6. 客户与商机查询接口

### 6.1 搜索客户

`GET /api/v1/crm/customers`

查询参数：

- `keyword`：可选，支持客户名称、客户简称、区域关键词
- `owner_id`：可选，按平台账号负责人过滤
- `page`
- `page_size`

返回：

```json
{
  "items": [
    {
      "provider": "feishu_bitable",
      "base_id": "app_xxx",
      "record_id": "rec_c001",
      "name": "常州大通工业园",
      "industry": "工业园区",
      "region": "江苏常州",
      "owner_name": "霸天"
    }
  ],
  "total": 1
}
```

用途：

- 需求分析会话绑定客户
- 方案会话绑定客户
- 售前任务绑定客户

### 6.2 搜索商机

`GET /api/v1/crm/opportunities`

查询参数：

- `customer_record_id`：可选
- `keyword`：可选
- `stage`：可选
- `owner_id`：可选
- `page`
- `page_size`

返回：

```json
{
  "items": [
    {
      "provider": "feishu_bitable",
      "base_id": "app_xxx",
      "record_id": "rec_o001",
      "customer_record_id": "rec_c001",
      "name": "常州大通工业园储能优化项目",
      "stage": "方案推进",
      "owner_name": "霸天"
    }
  ],
  "total": 1
}
```

---

## 7. 平台对象绑定 CRM 记录接口

### 7.1 需求分析会话绑定客户/商机

`POST /api/v1/customer-demand/sessions/{session_id}/crm-bind`

请求体：

```json
{
  "provider": "feishu_bitable",
  "crm_customer_record_id": "rec_c001",
  "crm_opportunity_record_id": "rec_o001"
}
```

效果：

- 回写当前会话的 `crm_customer_record_id`
- 回写当前会话的 `crm_opportunity_record_id`
- 保存客户名称/商机名称快照，方便页面直接展示

### 7.2 解决方案会话绑定客户/商机

`POST /api/v1/solution/conversations/{conversation_id}/crm-bind`

请求体：

```json
{
  "provider": "feishu_bitable",
  "crm_customer_record_id": "rec_c001",
  "crm_opportunity_record_id": "rec_o001"
}
```

### 7.3 售前任务绑定客户/商机

`POST /api/v1/presales/tasks/{task_id}/crm-bind`

请求体：

```json
{
  "provider": "feishu_bitable",
  "crm_customer_record_id": "rec_c001",
  "crm_opportunity_record_id": "rec_o001"
}
```

---

## 8. 写回飞书 CRM 的关键接口

### 8.1 需求分析报告写回跟进记录

`POST /api/v1/customer-demand/reports/{report_id}/crm-writeback`

用途：

- 在飞书 CRM 跟进记录表新增一条记录
- 写入本次需求分析结论摘要、建议追问、报告链接

请求体：

```json
{
  "write_target": "followup",
  "mode": "append",
  "confirmed": true
}
```

建议写入字段：

- 关联客户
- 关联商机
- 跟进类型：`需求分析`
- 跟进摘要
- 核心需求
- 待确认问题
- 报告链接
- 创建人
- 创建时间

### 8.2 解决方案结果写回跟进记录

`POST /api/v1/solution/results/{result_id}/crm-writeback`

用途：

- 在飞书 CRM 跟进记录表新增“方案已生成”记录
- 可附带方案链接与方案摘要

### 8.3 售前任务写回商机/跟进记录

`POST /api/v1/presales/tasks/{task_id}/crm-writeback`

用途：

- 将售前任务摘要写入 CRM 跟进记录
- 可选回写商机的：
  - 下次回访时间
  - 当前负责人
  - 最新进展

请求体：

```json
{
  "write_target": "followup",
  "confirmed": true,
  "sync_next_followup": true
}
```

### 8.4 资料归档写回附件索引表

`POST /api/v1/presales/archives/{archive_id}/crm-writeback`

用途：

- 在附件索引表写入文档名称、来源、链接、关联客户/商机

---

## 9. 飞书多维表格实际调用建议

### 9.1 查询记录

平台内部服务建议封装为：

- `search_customer_records(...)`
- `search_opportunity_records(...)`
- `list_contact_records(...)`

由服务层负责调用飞书多维表格接口并做字段转换。

### 9.2 创建记录

平台内部服务建议封装为：

- `create_followup_record(...)`
- `create_attachment_record(...)`

### 9.3 更新记录

平台内部服务建议封装为：

- `update_customer_record(...)`
- `update_opportunity_record(...)`

一期建议慎用直接更新主表，优先：

- 创建跟进记录
- 创建附件索引记录

避免智能体过程频繁直接覆盖 CRM 主档。

---

## 10. 前端建议使用方式

前端不直接展示飞书字段 ID。建议只提供：

- 搜索客户
- 搜索商机
- 绑定当前对象
- 查看当前绑定结果
- 人工确认后写回 CRM

例如：

- 需求分析报告页
  - `绑定客户`
  - `绑定商机`
  - `写入 CRM 跟进`
- 解决方案结果页
  - `写入 CRM 跟进`
- 售前闭环中心
  - `绑定客户`
  - `绑定商机`
  - `同步到 CRM`

---

## 11. 权限建议

建议新增平台权限：

- `crm.access`：查看 CRM 绑定信息
- `crm.bind`：绑定客户/商机
- `crm.writeback`：将报告、方案、任务写回 CRM
- `crm.manage`：管理 CRM 配置与表映射

控制原则：

- 普通售前/销售可查看与绑定自己负责对象
- 写回动作建议保留人工确认
- CRM 配置仅平台管理员或指定业务管理员可修改

---

## 12. 审计与留痕建议

以下动作建议写入审计日志：

- 搜索客户/商机
- 绑定客户/商机
- 需求分析报告写回 CRM
- 解决方案结果写回 CRM
- 售前任务写回 CRM
- 附件索引写回 CRM

同时 `crm_writeback_record` 要保留：

- 请求载荷
- 响应内容
- 错误信息
- 操作人
- 时间

---

## 13. 一期最小落地建议

推荐按以下顺序落地：

1. 查询客户
2. 查询商机
3. 绑定需求分析会话 / 方案会话 / 售前任务到 CRM
4. 需求分析报告写回飞书 CRM 跟进记录
5. 解决方案结果写回飞书 CRM 跟进记录
6. 售前任务写回飞书 CRM 跟进记录
7. 资料归档写回飞书 CRM 附件索引表

一期先不做：

- 飞书 CRM 主表自动回推平台
- 自动双向同步冲突解决
- 客户画像自动评分模型
- 飞书侧修改实时回流平台

---

## 14. 一句话总结

一期飞书 CRM 接口设计建议采用：

- `平台语义化接口 + 后端字段映射 + 人工确认写回`

从而实现：

- 平台对象与飞书 CRM 记录可绑定
- 需求分析、方案结果、售前任务能够稳定写回飞书 CRM
- 飞书 CRM 承担客户与商机主数据层职责
- PowerAgent 平台承担智能体处理与流程流转职责
