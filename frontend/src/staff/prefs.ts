import type { StaffUser } from './types'
import { normalizeHex } from './theme'

const LAST_ACCENT_KEY = 'mhh-staff-last-accent'
const PREFS_PREFIX = 'mhh-staff-prefs:'

export interface StaffPrefs {
  accent_color?: string
  dashboard_collapsed?: string[]
}

function safeParse(raw: string | null): StaffPrefs {
  if (!raw) return {}
  try {
    const parsed = JSON.parse(raw) as StaffPrefs
    return parsed && typeof parsed === 'object' ? parsed : {}
  } catch {
    return {}
  }
}

export function readLastAccent(): string {
  try {
    return normalizeHex(localStorage.getItem(LAST_ACCENT_KEY) || '')
  } catch {
    return ''
  }
}

export function writeLastAccent(hex: string) {
  try {
    const normalized = normalizeHex(hex)
    if (normalized) localStorage.setItem(LAST_ACCENT_KEY, normalized)
  } catch {
    /* private mode */
  }
}

export function readLocalPrefs(userId: number): StaffPrefs {
  try {
    return safeParse(localStorage.getItem(PREFS_PREFIX + userId))
  } catch {
    return {}
  }
}

export function writeLocalPrefs(userId: number, prefs: StaffPrefs) {
  try {
    const current = readLocalPrefs(userId)
    const next: StaffPrefs = { ...current, ...prefs }
    localStorage.setItem(PREFS_PREFIX + userId, JSON.stringify(next))
    if (next.accent_color) writeLastAccent(next.accent_color)
  } catch {
    /* private mode */
  }
}

export function hydrateStaffUser(user: StaffUser): StaffUser {
  const local = readLocalPrefs(user.id)
  const serverColor = normalizeHex(user.accent_color)
  const localColor = normalizeHex(local.accent_color)
  const collapsed = Array.isArray(local.dashboard_collapsed)
    ? local.dashboard_collapsed
    : Array.isArray(user.dashboard_collapsed)
      ? user.dashboard_collapsed
      : []
  const hydrated: StaffUser = {
    ...user,
    accent_color: localColor || serverColor || '',
    dashboard_collapsed: collapsed,
  }
  writeLocalPrefs(user.id, {
    accent_color: hydrated.accent_color,
    dashboard_collapsed: hydrated.dashboard_collapsed,
  })
  return hydrated
}
