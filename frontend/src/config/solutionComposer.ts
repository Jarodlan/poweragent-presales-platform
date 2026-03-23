export interface ComposerParams {
  scenario: string
  grid_environment: string
  equipment_type: string
  resource_type: string
  data_basis: string[]
  target_capability: string[]
  market_policy_focus: string[]
  planning_objective: string[]
  forecast_target: string[]
  coordination_scope: string
  lifecycle_goal: string
}

export const DEFAULT_PARAMS: ComposerParams = {
  scenario: 'fault_diagnosis_solution',
  grid_environment: 'distribution_network',
  equipment_type: 'comprehensive',
  resource_type: 'not_involved',
  data_basis: ['scada', 'online_monitoring', 'historical_workorder'],
  target_capability: ['fault_diagnosis', 'root_cause_analysis'],
  market_policy_focus: [],
  planning_objective: [],
  forecast_target: [],
  coordination_scope: 'not_involved',
  lifecycle_goal: 'not_involved',
}

export const SCENARIO_PRESET_MAP: Record<string, Partial<ComposerParams>> = {
  fault_diagnosis_solution: {
    equipment_type: 'comprehensive',
    resource_type: 'not_involved',
    data_basis: ['scada', 'online_monitoring', 'historical_workorder'],
    target_capability: ['fault_diagnosis', 'root_cause_analysis'],
    market_policy_focus: [],
    planning_objective: [],
    forecast_target: [],
    coordination_scope: 'not_involved',
    lifecycle_goal: 'not_involved',
  },
  storage_aggregation_solution: {
    equipment_type: 'not_involved',
    resource_type: 'distributed_storage',
    data_basis: ['market_price_data', 'load_curve', 'bms_pcs_data'],
    target_capability: ['storage_aggregation_operation', 'market_bidding_optimization'],
    market_policy_focus: ['spot_market', 'peak_valley_arbitrage'],
    planning_objective: [],
    forecast_target: [],
    coordination_scope: 'not_involved',
    lifecycle_goal: 'lifecycle_revenue_balance',
  },
  distribution_planning_solution: {
    equipment_type: 'feeder_transformer_area',
    resource_type: 'not_involved',
    data_basis: ['scada', 'load_curve', 'renewable_curve'],
    target_capability: ['distribution_planning_optimization'],
    market_policy_focus: [],
    planning_objective: ['overload_mitigation', 'investment_benefit_optimization'],
    forecast_target: [],
    coordination_scope: 'not_involved',
    lifecycle_goal: 'not_involved',
  },
  power_forecast_solution: {
    equipment_type: 'not_involved',
    resource_type: 'not_involved',
    data_basis: ['weather_data', 'renewable_curve', 'historical_workorder'],
    target_capability: ['renewable_power_forecast'],
    market_policy_focus: [],
    planning_objective: [],
    forecast_target: ['day_ahead_forecast', 'deviation_assessment_optimization'],
    coordination_scope: 'not_involved',
    lifecycle_goal: 'not_involved',
  },
  vpp_coordination_solution: {
    equipment_type: 'not_involved',
    resource_type: 'hybrid_flexible_resources',
    data_basis: ['market_price_data', 'load_curve', 'renewable_curve', 'bms_pcs_data'],
    target_capability: ['vpp_dispatch_coordination', 'market_bidding_optimization'],
    market_policy_focus: ['spot_market', 'demand_response'],
    planning_objective: [],
    forecast_target: [],
    coordination_scope: 'virtual_power_plant',
    lifecycle_goal: 'comprehensive_benefit_optimization',
  },
  other_solution: {
    grid_environment: 'not_involved',
    equipment_type: 'not_involved',
    resource_type: 'not_involved',
    data_basis: [],
    target_capability: [],
    market_policy_focus: [],
    planning_objective: [],
    forecast_target: [],
    coordination_scope: 'not_involved',
    lifecycle_goal: 'not_involved',
  },
}
