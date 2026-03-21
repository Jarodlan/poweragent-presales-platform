const DEFAULT_HEADERS = {
  'Content-Type': 'application/json',
}

interface ApiEnvelope<T> {
  code: number
  message: string
  data: T
}

export async function apiRequest<T>(input: string, init?: RequestInit): Promise<T> {
  const response = await fetch(input, {
    ...init,
    headers: {
      ...DEFAULT_HEADERS,
      ...(init?.headers ?? {}),
    },
  })

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
