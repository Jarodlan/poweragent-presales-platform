import { getStoredToken } from '@/api/http'

export function createTaskEventSource(streamUrl: string) {
  const normalized = streamUrl.startsWith('http') ? streamUrl : streamUrl
  const token = getStoredToken()
  if (!token) {
    return new EventSource(normalized)
  }

  const separator = normalized.includes('?') ? '&' : '?'
  return new EventSource(`${normalized}${separator}access_token=${encodeURIComponent(token)}`)
}
