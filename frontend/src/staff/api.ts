import { getApiUrl } from '../config/api'

function getCookie(name: string): string | null {
  const match = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`))
  return match ? decodeURIComponent(match[1]) : null
}

let csrfToken: string | null = null

export async function ensureCsrfToken(): Promise<string> {
  if (csrfToken) return csrfToken
  const fromCookie = getCookie('csrftoken')
  if (fromCookie) {
    csrfToken = fromCookie
    return csrfToken
  }
  const resp = await fetch(getApiUrl('/api/staff/csrf/'), { credentials: 'include' })
  const body = await resp.json().catch(() => null)
  csrfToken = body?.csrfToken || ''
  return csrfToken
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
