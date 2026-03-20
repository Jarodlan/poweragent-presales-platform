from rest_framework.response import Response
from rest_framework.views import APIView


class MetaOptionsView(APIView):
    def get(self, request):
        return Response(
            {
                "code": 0,
                "message": "ok",
                "data": {
                    "grid_environment_options": [
                        {"label": "配电网", "value": "distribution_network"},
                        {"label": "输电网", "value": "transmission_network"},
                        {"label": "园区微网", "value": "microgrid"},
                        {"label": "综合能源场景", "value": "integrated_energy"},
                    ],
                    "equipment_type_options": [
                        {"label": "线路", "value": "line"},
                        {"label": "变压器", "value": "transformer"},
                        {"label": "开关柜", "value": "switchgear"},
                        {"label": "综合故障", "value": "comprehensive"},
                    ],
                    "data_basis_options": [
                        {"label": "SCADA", "value": "scada"},
                        {"label": "在线监测", "value": "online_monitoring"},
                        {"label": "历史工单", "value": "historical_workorder"},
                        {"label": "图像巡检", "value": "inspection_image"},
                    ],
                    "target_capability_options": [
                        {"label": "故障预警", "value": "fault_warning"},
                        {"label": "故障诊断", "value": "fault_diagnosis"},
                        {"label": "根因分析", "value": "root_cause_analysis"},
                        {"label": "辅助处置", "value": "assisted_dispatch"},
                    ],
                    "default_params": {
                        "grid_environment": "distribution_network",
                        "equipment_type": "comprehensive",
                        "data_basis": ["scada", "online_monitoring", "historical_workorder"],
                        "target_capability": ["fault_diagnosis", "root_cause_analysis"],
                    },
                },
            }
        )
