const DEFAULT_HEADERS = {
  'Content-Type': 'application/json',
}

const TOKEN_STORAGE_KEY = 'poweragent_access_token'

interface ApiEnvelope<T> {
  code: number
  message: string
  data: T
}

export function getStoredToken() {
  return localStorage.getItem(TOKEN_STORAGE_KEY) || ''
}

export function setStoredToken(token: string) {
  localStorage.setItem(TOKEN_STORAGE_KEY, token)
}

export function clearStoredToken() {
  localStorage.removeItem(TOKEN_STORAGE_KEY)
}

export async function apiRequest<T>(input: string, init?: RequestInit): Promise<T> {
  const token = getStoredToken()
  const response = await fetch(input, {
    ...init,
    headers: {
      ...DEFAULT_HEADERS,
      ...(token ? { Authorization: `Token ${token}` } : {}),
      ...(init?.headers ?? {}),
    },
  })

  if (response.status === 401) {
    clearStoredToken()
    if (window.location.pathname !== '/login') {
      window.location.href = '/login'
    }
    throw new Error('登录状态已失效，请重新登录。')
  }

  if (!response.ok) {
    const text = await response.text()
    throw new Error(text || `Request failed with status ${response.status}`)
  }

  const payload = (await response.json()) as ApiEnvelope<T>
  if (payload.code !== 0) {
    throw new Error(payload.message || 'Request failed')
  }

  return payload.data
}
