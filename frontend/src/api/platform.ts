import { apiRequest } from './http'
import type { PlatformModuleListData } from '@/types/platform'

export function fetchPlatformModules() {
  return apiRequest<PlatformModuleListData>('/api/v1/platform/modules')
}
