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

let sessionExpiredHandler: (() => void) | null = null

/** Lets the app send people back to sign-in instead of showing a raw API error. */
export function setSessionExpiredHandler(handler: () => void) {
  sessionExpiredHandler = handler
}

/**
 * Django answers an expired session with 403 and "Authentication credentials
 * were not provided", which reads like a permissions problem but only means
 * "sign in again". A logged-in user who lacks access gets a different message,
 * so check the body rather than the status alone.
 */
async function isSignedOutResponse(resp: Response): Promise<boolean> {
  if (resp.status === 401) return true
  if (resp.status !== 403) return false
  try {
    const body = await resp.clone().json()
    const detail = typeof body?.detail === 'string' ? body.detail.toLowerCase() : ''
    return detail.includes('authentication credentials')
  } catch {
    return false
  }
}

export async function staffFetch(endpoint: string, options: RequestInit = {}): Promise<Response> {
  const headers = new Headers(options.headers || {})
  const method = (options.method || 'GET').toUpperCase()
  if (method !== 'GET' && method !== 'HEAD') {
    const token = await ensureCsrfToken()
    if (token) headers.set('X-CSRFToken', token)
  }
  const resp = await fetch(getApiUrl(endpoint), {
    ...options,
    headers,
    credentials: 'include',
  })

  if (await isSignedOutResponse(resp)) {
    csrfToken = null
    sessionExpiredHandler?.()
  }

  return resp
}

export function clearStaffSession() {
  csrfToken = null
}
