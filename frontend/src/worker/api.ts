import { getApiUrl } from '../config/api'

function clearWorkerSession() {
  localStorage.removeItem('worker_token')
  localStorage.removeItem('worker_account')
}

/**
 * Fetch wrapper for worker portal endpoints.
 * - Prefixes backend base URL
 * - Adds Authorization header when a worker token exists
 * - If backend returns 401, clears local session so UI returns to login
 */
export async function workerFetch(
  endpoint: string,
  options: RequestInit = {}
): Promise<Response> {
  const token = localStorage.getItem('worker_token')
  const headers = new Headers(options.headers || {})

  // Only attach auth header if we have a token
  if (token) headers.set('Authorization', `Token ${token}`)

  const response = await fetch(getApiUrl(endpoint), {
    ...options,
    headers,
  })

  if (response.status === 401) {
    clearWorkerSession()
    // Let the app know the token is no longer valid (e.g., backend restarted)
    if (typeof window !== 'undefined') {
      window.dispatchEvent(new Event('worker-session-expired'))
    }
  }

  return response
}

