export interface OptionItem {
  label: string
  value: string
}

export interface MetaOptions {
  scenario_options: OptionItem[]
  grid_environment_options: OptionItem[]
  equipment_type_options: OptionItem[]
  resource_type_options: OptionItem[]
  data_basis_options: OptionItem[]
  target_capability_options: OptionItem[]
  market_policy_focus_options: OptionItem[]
  planning_objective_options: OptionItem[]
  forecast_target_options: OptionItem[]
  coordination_scope_options: OptionItem[]
  lifecycle_goal_options: OptionItem[]
  default_params: Record<string, string | string[]>
}
