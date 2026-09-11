export const DEFAULT_DASHBOARD_ORDER = [
  'recent-clients',
  'pitstop',
  'citybuild',
  'classes',
  'tickets',
  'documents',
] as const

export type DashboardModuleId = (typeof DEFAULT_DASHBOARD_ORDER)[number]

export function normalizeDashboardOrder(saved: unknown): string[] {
  const known = [...DEFAULT_DASHBOARD_ORDER]
  const seen = new Set<string>()
  const next: string[] = []
  if (Array.isArray(saved)) {
    for (const item of saved) {
      if (typeof item === 'string' && known.includes(item as DashboardModuleId) && !seen.has(item)) {
        next.push(item)
        seen.add(item)
      }
    }
  }
  for (const id of known) {
    if (!seen.has(id)) next.push(id)
  }
  return next
}

export function ordersMatch(a: string[] | undefined, b: readonly string[]): boolean {
  const left = Array.isArray(a) ? a : []
  if (left.length !== b.length) return false
  return left.every((id, index) => id === b[index])
}
