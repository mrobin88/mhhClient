import { getApiUrl } from '../config/api'

let csrfToken: string | null = null

/** CSRF cookie lives on the API host — never read document.cookie on the static app. */
export async function refreshCsrfToken(): Promise<string> {
  const resp = await fetch(getApiUrl('/api/staff/csrf/'), { credentials: 'include' })
  const body = await resp.json().catch(() => null)
  const token = String(body?.csrfToken ?? '')
  csrfToken = token
  return token
}

export function setCsrfToken(token: string) {
  csrfToken = token || null
}

async function ensureCsrfToken(): Promise<string> {
  if (csrfToken) return csrfToken
  return refreshCsrfToken()
}

export async function staffFetch(endpoint: string, options: RequestInit = {}): Promise<Response> {
  const headers = new Headers(options.headers || {})
  const method = (options.method || 'GET').toUpperCase()
  if (method !== 'GET' && method !== 'HEAD') {
    const token = await ensureCsrfToken()
    if (token) headers.set('X-CSRFToken', token)
  }
  return fetch(getApiUrl(endpoint), {
    ...options,
    headers,
    credentials: 'include',
  })
}

export function clearStaffSession() {
  csrfToken = null
}
