import { apiRequest } from './http'
import type { MetaOptions } from '@/types/meta'

export function fetchMetaOptions() {
  return apiRequest<MetaOptions>('/api/v1/meta/options')
}
