export function createTaskEventSource(streamUrl: string) {
  const normalized = streamUrl.startsWith('http') ? streamUrl : streamUrl
  return new EventSource(normalized)
}
