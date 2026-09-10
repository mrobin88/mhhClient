export function friendlyError(
  body: Record<string, unknown> | null,
  fallback = 'Whoops, something didn’t go as planned. Want to try that again?',
): string {
  if (!body) return fallback
  if (typeof body.error === 'string' && body.error) return body.error
  if (typeof body.detail === 'string' && body.detail) return body.detail
  if (Array.isArray(body.non_field_errors) && body.non_field_errors[0]) {
    return String(body.non_field_errors[0])
  }
  const firstKey = Object.keys(body)[0]
  if (firstKey) {
    const val = body[firstKey]
    if (Array.isArray(val) && val[0]) return String(val[0])
    if (typeof val === 'string') return val
  }
  return fallback
}

export function networkErrorMessage(err: unknown): string {
  if (err instanceof TypeError) {
    return 'Hmm, can’t seem to reach the server. Double-check your internet and give it another shot.'
  }
  return 'Whoops, something didn’t go as planned. Want to try that again?'
}
