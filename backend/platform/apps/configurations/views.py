from rest_framework.response import Response
from rest_framework.views import APIView


class MetaOptionsView(APIView):
    def get(self, request):
        return Response(
            {
                "code": 0,
                "message": "ok",
                "data": {
                    "scenario_options": [
                        {"label": "智能电网故障诊断", "value": "fault_diagnosis_solution"},
                        {"label": "分布式储能聚合运营", "value": "storage_aggregation_solution"},
                        {"label": "配网规划", "value": "distribution_planning_solution"},
                        {"label": "新能源功率预测", "value": "power_forecast_solution"},
                        {"label": "虚拟电厂/源网荷储协同", "value": "vpp_coordination_solution"},
                        {"label": "其他场景", "value": "other_solution"},
                    ],
                    "grid_environment_options": [
                        {"label": "不涉及/待判断", "value": "not_involved"},
                        {"label": "配电网", "value": "distribution_network"},
                        {"label": "输电网", "value": "transmission_network"},
                        {"label": "园区微网", "value": "microgrid"},
                        {"label": "综合能源场景", "value": "integrated_energy"},
                    ],
                    "equipment_type_options": [
                        {"label": "不涉及/待判断", "value": "not_involved"},
                        {"label": "线路", "value": "line"},
                        {"label": "变压器", "value": "transformer"},
                        {"label": "开关柜", "value": "switchgear"},
                        {"label": "综合故障", "value": "comprehensive"},
                        {"label": "馈线/台区", "value": "feeder_transformer_area"},
                        {"label": "储能单元", "value": "energy_storage_unit"},
                    ],
                    "resource_type_options": [
                        {"label": "不涉及/待判断", "value": "not_involved"},
                        {"label": "分布式储能", "value": "distributed_storage"},
                        {"label": "工商业储能", "value": "commercial_storage"},
                        {"label": "用户侧储能", "value": "behind_the_meter_storage"},
                        {"label": "光伏+储能", "value": "pv_storage"},
                        {"label": "风光储协同", "value": "wind_pv_storage"},
                        {"label": "可调负荷/充电桩/储能混合资源", "value": "hybrid_flexible_resources"},
                    ],
                    "data_basis_options": [
                        {"label": "SCADA", "value": "scada"},
                        {"label": "EMS/AGC/AVC", "value": "ems_agc_avc"},
                        {"label": "在线监测", "value": "online_monitoring"},
                        {"label": "历史工单", "value": "historical_workorder"},
                        {"label": "图像巡检", "value": "inspection_image"},
                        {"label": "电价/市场交易数据", "value": "market_price_data"},
                        {"label": "气象数据", "value": "weather_data"},
                        {"label": "负荷曲线", "value": "load_curve"},
                        {"label": "新能源发电曲线", "value": "renewable_curve"},
                        {"label": "电池BMS/PCS数据", "value": "bms_pcs_data"},
                    ],
                    "target_capability_options": [
                        {"label": "故障预警", "value": "fault_warning"},
                        {"label": "故障诊断", "value": "fault_diagnosis"},
                        {"label": "根因分析", "value": "root_cause_analysis"},
                        {"label": "辅助处置", "value": "assisted_dispatch"},
                        {"label": "储能聚合运营", "value": "storage_aggregation_operation"},
                        {"label": "市场报价/套利优化", "value": "market_bidding_optimization"},
                        {"label": "配网规划优化", "value": "distribution_planning_optimization"},
                        {"label": "新能源功率预测", "value": "renewable_power_forecast"},
                        {"label": "虚拟电厂协同调度", "value": "vpp_dispatch_coordination"},
                    ],
                    "market_policy_focus_options": [
                        {"label": "现货市场", "value": "spot_market"},
                        {"label": "中长期交易", "value": "mid_long_term_market"},
                        {"label": "辅助服务", "value": "ancillary_services"},
                        {"label": "需求响应", "value": "demand_response"},
                        {"label": "峰谷套利", "value": "peak_valley_arbitrage"},
                    ],
                    "planning_objective_options": [
                        {"label": "网架优化", "value": "grid_topology_optimization"},
                        {"label": "重过载治理", "value": "overload_mitigation"},
                        {"label": "新能源消纳", "value": "renewable_consumption"},
                        {"label": "供电可靠性提升", "value": "reliability_improvement"},
                        {"label": "投资效益最优", "value": "investment_benefit_optimization"},
                    ],
                    "forecast_target_options": [
                        {"label": "短时功率预测", "value": "ultra_short_term_forecast"},
                        {"label": "日内功率预测", "value": "intra_day_forecast"},
                        {"label": "日前功率预测", "value": "day_ahead_forecast"},
                        {"label": "偏差考核优化", "value": "deviation_assessment_optimization"},
                    ],
                    "coordination_scope_options": [
                        {"label": "不涉及/待判断", "value": "not_involved"},
                        {"label": "源网荷储协同", "value": "source_grid_load_storage"},
                        {"label": "虚拟电厂聚合", "value": "virtual_power_plant"},
                        {"label": "园区综合能源协同", "value": "campus_integrated_energy"},
                        {"label": "配网-市场协同", "value": "distribution_market_coordination"},
                    ],
                    "lifecycle_goal_options": [
                        {"label": "不涉及/待判断", "value": "not_involved"},
                        {"label": "收益最大化", "value": "revenue_maximization"},
                        {"label": "寿命收益平衡", "value": "lifecycle_revenue_balance"},
                        {"label": "安全优先", "value": "safety_first"},
                        {"label": "综合收益最优", "value": "comprehensive_benefit_optimization"},
                    ],
                    "default_params": {
                        "scenario": "fault_diagnosis_solution",
                        "grid_environment": "distribution_network",
                        "equipment_type": "comprehensive",
                        "resource_type": "not_involved",
                        "data_basis": ["scada", "online_monitoring", "historical_workorder"],
                        "target_capability": ["fault_diagnosis", "root_cause_analysis"],
                        "market_policy_focus": [],
                        "planning_objective": [],
                        "forecast_target": [],
                        "coordination_scope": "not_involved",
                        "lifecycle_goal": "not_involved",
                    },
                },
            }
        )
