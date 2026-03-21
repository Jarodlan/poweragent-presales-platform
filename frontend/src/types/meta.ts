export interface OptionItem {
  label: string
  value: string
}

export interface MetaOptions {
  grid_environment_options: OptionItem[]
  equipment_type_options: OptionItem[]
  data_basis_options: OptionItem[]
  target_capability_options: OptionItem[]
  default_params: Record<string, string | string[]>
}
