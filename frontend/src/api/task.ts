import { apiRequest } from './http'

export function cancelTask(taskId: string) {
  return apiRequest<{ task_id: string; status: string }>(`/api/v1/solution/tasks/${taskId}/cancel`, {
    method: 'POST',
  })
}
