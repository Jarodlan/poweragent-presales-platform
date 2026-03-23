import type { ComposerParams } from '@/config/solutionComposer'

const SOLUTION_HANDOFF_STORAGE_KEY = 'poweragent.solutionHandoffDraft'

export interface SolutionHandoffDraft {
  source: 'customer-demand'
  sourceSessionId: string
  sourceReportId: string
  query: string
  params: ComposerParams
  createdAt: string
}

export function saveSolutionHandoffDraft(draft: SolutionHandoffDraft) {
  window.sessionStorage.setItem(SOLUTION_HANDOFF_STORAGE_KEY, JSON.stringify(draft))
}

export function consumeSolutionHandoffDraft(): SolutionHandoffDraft | null {
  const raw = window.sessionStorage.getItem(SOLUTION_HANDOFF_STORAGE_KEY)
  if (!raw) return null
  window.sessionStorage.removeItem(SOLUTION_HANDOFF_STORAGE_KEY)
  try {
    return JSON.parse(raw) as SolutionHandoffDraft
  } catch {
    return null
  }
}
