from __future__ import annotations

from functools import lru_cache
from typing import Any

from app.config import settings


DEFAULT_SPECIALIZED_SECTIONS = [
    "成功案例介绍",
    "技术实施方案",
    "效益评估指标",
    "总结",
]


SCENARIO_REGISTRY: dict[str, dict[str, Any]] = {
    "fault_diagnosis_solution": {
        "document_title": "智能配电网故障诊断解决方案",
        "template_path": settings.solution_template_path,
        "source_path": settings.solution_template_source_path,
        "keywords": [
            "故障",
            "诊断",
            "定位",
            "研判",
            "停电",
            "自愈",
            "保护",
            "波形",
            "告警",
        ],
        "retrieval_priority": ["solution", "case", "paper", "standard"],
        "default_context": {
            "grid_environment": "distribution_network",
            "equipment_type": "comprehensive",
            "data_basis": ["scada", "online_monitoring", "historical_workorder"],
            "target_capability": ["fault_diagnosis", "root_cause_analysis"],
        },
        "section_guidance": {},
        "specialized_sections": DEFAULT_SPECIALIZED_SECTIONS,
        "tags": ["故障诊断", "配电网", "运检", "自愈"],
    },
    "storage_aggregation_solution": {
        "document_title": "分布式储能聚合运营智能体解决方案",
        "template_path": settings.storage_solution_template_path,
        "source_path": settings.storage_solution_template_source_path,
        "keywords": [
            "储能",
            "聚合",
            "虚拟电厂",
            "电价",
            "现货",
            "需求响应",
            "套利",
            "生命周期",
            "aggregator",
            "storage",
        ],
        "retrieval_priority": ["solution", "case", "paper", "standard"],
        "default_context": {
            "grid_environment": "urban_distribution_network",
            "asset_scope": [
                "user_side_storage",
                "park_storage",
                "distributed_pv",
                "flexible_load",
            ],
            "market_scope": [
                "time_of_use_tariff",
                "spot_market",
                "demand_response",
                "green_power_trade",
            ],
            "core_constraints": [
                "grid_constraints",
                "price_policy",
                "lifecycle_benefit_maximization",
            ],
            "region": "zhejiang_ningbo",
        },
        "section_guidance": {
            "背景介绍": "必须同时交代区域负荷特征、新能源渗透、市场化交易背景，以及为什么储能聚合运营需要智能体。",
            "核心挑战识别": "重点写清电网约束、市场价格波动、储能寿命退化、资源分散接入和收益分配五类挑战。",
            "建设目标": "必须覆盖电网侧目标、市场侧目标、资产侧目标、平台侧目标，并给出分阶段目标。",
            "总体技术架构": "建议写成数据底座、规则约束层、多智能体决策层、调度执行层、复盘优化层五层结构，并明确外部数据、现场数据和知识库的角色。",
            "技术创新方向": "至少写4项，优先围绕市场研判、电网约束分析、寿命机会成本建模、聚合调度优化、收益分摊和Agent协同。",
            "成功案例介绍": "若缺少完全匹配本地案例，可写同类参考案例，但要明确说明“参考案例”或“可参考场景”，并写出映射意义。",
            "技术实施方案": "优先展开资源接入治理、规则建模、预测模型、优化引擎、执行联动、收益复盘中的5步关键路径。",
            "效益分析": "必须从聚合收益提升、电网调峰支撑、储能寿命友好运行、运维效率提升四个角度量化。",
            "效益评估指标": "KPI应覆盖收益、执行、设备寿命、电网约束、安全合规和客户侧解释性。",
            "总结": "必须回扣区域性、电网约束、市场化运营和产品复制前景。",
        },
        "specialized_sections": DEFAULT_SPECIALIZED_SECTIONS,
        "tags": ["储能聚合", "虚拟电厂", "市场交易", "源网荷储"],
    },
}


SCENARIO_ALIASES = {
    "vpp_operation_solution": "storage_aggregation_solution",
    "virtual_power_plant_solution": "storage_aggregation_solution",
    "distributed_storage_solution": "storage_aggregation_solution",
    "distribution_fault_solution": "fault_diagnosis_solution",
}


@lru_cache(maxsize=1)
def supported_intent_labels() -> list[str]:
    return sorted(SCENARIO_REGISTRY.keys())


def list_scenarios() -> list[dict[str, Any]]:
    return [
        {"scenario_id": scenario_id, **config}
        for scenario_id, config in SCENARIO_REGISTRY.items()
    ]


def get_scenario_config(scenario_id: str | None = None) -> dict[str, Any]:
    resolved_id = SCENARIO_ALIASES.get(scenario_id or "", scenario_id or "")
    return {
        "scenario_id": resolved_id or "fault_diagnosis_solution",
        **SCENARIO_REGISTRY.get(resolved_id or "", SCENARIO_REGISTRY["fault_diagnosis_solution"]),
    }


def resolve_scenario_id(
    *,
    query: str = "",
    intent: str = "",
    explicit: str = "",
) -> str:
    for candidate in [explicit, intent]:
        if candidate in SCENARIO_REGISTRY:
            return candidate
        if candidate in SCENARIO_ALIASES:
            return SCENARIO_ALIASES[candidate]

    normalized = f"{explicit} {intent} {query}".lower()
    if not normalized.strip():
        return "fault_diagnosis_solution"

    best_id = "fault_diagnosis_solution"
    best_score = 0
    for scenario_id, config in SCENARIO_REGISTRY.items():
        score = sum(1 for keyword in config.get("keywords", []) if keyword.lower() in normalized)
        if score > best_score:
            best_id = scenario_id
            best_score = score
    return best_id

