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
    "other_solution": {
        "document_title": "电力行业智能体解决方案",
        "template_path": settings.generic_solution_template_path,
        "source_path": settings.generic_solution_template_source_path,
        "keywords": [
            "智能体",
            "解决方案",
            "能源",
            "电力",
            "电网",
        ],
        "retrieval_priority": ["solution", "paper", "case", "standard"],
        "default_context": {},
        "section_guidance": {
            "背景介绍": "结合用户输入动态抽取行业背景，不要强行套用故障诊断、储能、预测等已有场景语言。",
            "核心挑战识别": "根据用户问题归纳 3 到 5 项挑战，必须和后文技术路线对应。",
            "建设目标": "围绕用户提出的业务目标和平台目标，给出可交付、可实施的目标设计。",
            "总体技术架构": "采用通用电力智能体方案结构，讲清数据、知识、模型、Agent 编排和业务应用。",
            "技术创新方向": "允许按用户场景自定义创新点，但必须解释其业务价值与工程意义。",
            "成功案例介绍": "如缺少同类案例，可使用参考案例，但必须说明映射价值与边界。",
            "技术实施方案": "默认按五步法展开，不得遗漏实施动作、输入输出和系统对接方式。",
            "效益分析": "从效率、质量、收益、风险控制等角度量化分析。",
            "效益评估指标": "KPI 必须根据用户场景动态生成，不得套用固定场景指标。",
            "总结": "回扣用户场景、方案价值和后续推广方向。",
        },
        "specialized_sections": DEFAULT_SPECIALIZED_SECTIONS,
        "tags": ["通用场景", "其他场景", "临时模板"],
    },
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
            "grid_environment": "distribution_network",
            "resource_type": "distributed_storage",
            "data_basis": ["market_price_data", "load_curve", "bms_pcs_data"],
            "target_capability": ["storage_aggregation_operation", "market_bidding_optimization"],
            "market_policy_focus": ["spot_market", "peak_valley_arbitrage"],
            "lifecycle_goal": "lifecycle_revenue_balance",
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
    "distribution_planning_solution": {
        "document_title": "配网规划智能体解决方案",
        "template_path": settings.planning_solution_template_path,
        "source_path": settings.planning_solution_template_source_path,
        "keywords": [
            "配网规划",
            "网架优化",
            "重过载",
            "台区",
            "馈线",
            "n-1",
            "规划",
            "投资",
            "可靠性",
        ],
        "retrieval_priority": ["solution", "standard", "case", "paper"],
        "default_context": {
            "grid_environment": "distribution_network",
            "equipment_type": "feeder_transformer_area",
            "data_basis": ["scada", "load_curve", "renewable_curve"],
            "target_capability": ["distribution_planning_optimization"],
            "planning_objective": ["overload_mitigation", "investment_benefit_optimization"],
        },
        "section_guidance": {
            "背景介绍": "必须说明区域负荷增长、新能源接入、网架承压和传统规划方式的局限。",
            "核心挑战识别": "重点写清网架瓶颈识别、负荷与新能源不确定性、规划约束多目标平衡、投资收益测算四类问题。",
            "建设目标": "至少覆盖供电可靠性、重过载治理、新能源消纳、投资收益和规划效率提升五个目标。",
            "总体技术架构": "建议写成数据底座、规划分析引擎、约束校核引擎、方案比选引擎、成果发布层。",
            "技术创新方向": "优先围绕负荷预测与源荷协同、规划约束建模、方案自动比选、投资效益评估、规划知识复用。",
            "成功案例介绍": "优先给出台区重过载治理、新能源并网配网规划、城郊配网结构优化两类案例。",
            "技术实施方案": "要展开现状诊断、场景建模、方案生成、校核比选、规划发布五步。",
            "效益分析": "突出投资精准化、网架弹性、新能源承载能力、规划周期压缩和专家经验沉淀。",
            "效益评估指标": "KPI要覆盖N-1通过率、重过载消减率、投资收益率、规划周期、方案复用率。",
            "总结": "必须回到规划智能化、规模复制和规划-建设-运维联动价值。",
        },
        "specialized_sections": DEFAULT_SPECIALIZED_SECTIONS,
        "tags": ["配网规划", "网架优化", "规划校核", "投资效益"],
    },
    "power_forecast_solution": {
        "document_title": "新能源功率预测智能体解决方案",
        "template_path": settings.forecast_solution_template_path,
        "source_path": settings.forecast_solution_template_source_path,
        "keywords": [
            "功率预测",
            "风电预测",
            "光伏预测",
            "出力预测",
            "预测偏差",
            "日前预测",
            "日内预测",
            "短时预测",
            "气象",
        ],
        "retrieval_priority": ["paper", "solution", "case", "standard"],
        "default_context": {
            "grid_environment": "integrated_energy",
            "data_basis": ["weather_data", "renewable_curve", "load_curve"],
            "target_capability": ["renewable_power_forecast"],
            "forecast_target": ["day_ahead_forecast", "deviation_assessment_optimization"],
        },
        "section_guidance": {
            "背景介绍": "必须交代风电/光伏出力波动、偏差考核压力、区域调度协同需求和气象数据的重要性。",
            "核心挑战识别": "重点写清气象不确定性、地形与场站差异、设备状态影响、考核偏差约束、多时间尺度预测联动。",
            "建设目标": "覆盖短时、日内、日前预测能力，以及偏差率控制、调度协同和业务闭环目标。",
            "总体技术架构": "建议分为数据采集层、特征与样本治理层、预测模型层、偏差分析层、业务应用层。",
            "技术创新方向": "围绕多时间尺度联合建模、气象-功率融合、场站群协同预测、偏差自学习、Agent自动策略切换展开。",
            "成功案例介绍": "至少写风电场群预测和分布式光伏区域预测两类案例，强调偏差改进效果。",
            "技术实施方案": "必须按数据接入、样本治理、模型训练、在线推理、偏差复盘五步展开。",
            "效益分析": "强调偏差考核成本下降、调度计划准确率提升、弃风弃光降低、运行效率提升。",
            "效益评估指标": "KPI要覆盖MAE、RMSE、MAPE、合格率、偏差考核改善率、模型更新时效。",
            "总结": "回扣区域新能源消纳、预测闭环和规模复制能力。",
        },
        "specialized_sections": DEFAULT_SPECIALIZED_SECTIONS,
        "tags": ["新能源预测", "风电", "光伏", "偏差考核"],
    },
    "vpp_coordination_solution": {
        "document_title": "虚拟电厂/源网荷储协同智能体解决方案",
        "template_path": settings.vpp_solution_template_path,
        "source_path": settings.vpp_solution_template_source_path,
        "keywords": [
            "虚拟电厂",
            "源网荷储",
            "协同调度",
            "聚合调度",
            "可调负荷",
            "需求响应",
            "多资源协同",
            "vpp",
        ],
        "retrieval_priority": ["solution", "case", "paper", "standard"],
        "default_context": {
            "grid_environment": "integrated_energy",
            "resource_type": "hybrid_flexible_resources",
            "data_basis": ["market_price_data", "load_curve", "renewable_curve", "bms_pcs_data"],
            "target_capability": ["vpp_dispatch_coordination", "market_bidding_optimization"],
            "market_policy_focus": ["spot_market", "demand_response"],
            "coordination_scope": "virtual_power_plant",
            "lifecycle_goal": "comprehensive_benefit_optimization",
        },
        "section_guidance": {
            "背景介绍": "必须说明分散资源接入、电网约束、市场交易和聚合调度需求，体现源网荷储一体化背景。",
            "核心挑战识别": "至少覆盖资源异构、实时调度、电网安全、市场收益和执行一致性五类挑战。",
            "建设目标": "要同时写电网侧、市场侧、资源侧和平台侧目标。",
            "总体技术架构": "建议按资源接入层、约束建模层、多Agent协同决策层、执行控制层、运营复盘层展开。",
            "技术创新方向": "围绕资源画像、协同约束求解、实时调度、收益分配、指令闭环、策略自优化展开。",
            "成功案例介绍": "优先写虚拟电厂聚合调度和源网荷储示范园区两类案例。",
            "技术实施方案": "必须展开资源接入、规则建模、策略优化、执行联动、运营复盘五步。",
            "效益分析": "要体现调峰调频支撑、资源利用率提升、市场收益提升、调度执行效率提升。",
            "效益评估指标": "KPI应覆盖可调容量、响应成功率、市场收益、执行偏差、电网约束满足率、资源参与率。",
            "总结": "回扣多资源协同、平台复制和市场化价值。",
        },
        "specialized_sections": DEFAULT_SPECIALIZED_SECTIONS,
        "tags": ["虚拟电厂", "源网荷储", "协同调度", "需求响应"],
    },
}


SCENARIO_ALIASES = {
    "vpp_operation_solution": "storage_aggregation_solution",
    "virtual_power_plant_solution": "storage_aggregation_solution",
    "distributed_storage_solution": "storage_aggregation_solution",
    "distribution_fault_solution": "fault_diagnosis_solution",
    "distribution_planning_agent": "distribution_planning_solution",
    "power_forecast_agent": "power_forecast_solution",
    "renewable_power_forecast_solution": "power_forecast_solution",
    "source_grid_load_storage_solution": "vpp_coordination_solution",
    "virtual_power_plant_coordination_solution": "vpp_coordination_solution",
    "other_scene_solution": "other_solution",
    "general_solution": "other_solution",
    "generic_solution": "other_solution",
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

    best_id = "other_solution"
    best_score = 0
    for scenario_id, config in SCENARIO_REGISTRY.items():
        score = sum(1 for keyword in config.get("keywords", []) if keyword.lower() in normalized)
        if score > best_score:
            best_id = scenario_id
            best_score = score
    return best_id
