export interface PlatformModuleItem {
  module_id: string
  name: string
  description: string
  icon: string
  route_type: 'internal' | 'external'
  route_target: string
  open_mode: 'same_tab' | 'new_tab'
}

export interface PlatformModuleListData {
  items: PlatformModuleItem[]
}
