export const SUGGESTION_KINDS = [
  { value: 'idea', label: 'Idea', hint: 'A better way to do something' },
  { value: 'problem', label: 'Problem', hint: 'Something is broken or confusing' },
  { value: 'request', label: 'Request', hint: 'A change you need for your work' },
] as const

export type SuggestionKind = (typeof SUGGESTION_KINDS)[number]['value']

const KIND_PRIORITY: Record<SuggestionKind, string> = {
  idea: 'p4',
  problem: 'p2',
  request: 'p3',
}

export function suggestionPriority(kind: SuggestionKind) {
  return KIND_PRIORITY[kind]
}

export function suggestionTitleFromBody(body: string) {
  const first = body
    .trim()
    .split(/\n/)[0]
    .replace(/\s+/g, ' ')
    .trim()
  if (!first) return ''
  return first.length > 80 ? `${first.slice(0, 77).trim()}…` : first
}

export function suggestionKindFromTags(tags: string[] | undefined | null): SuggestionKind | '' {
  if (!tags?.length) return ''
  if (tags.includes('idea')) return 'idea'
  if (tags.includes('problem')) return 'problem'
  if (tags.includes('request')) return 'request'
  return ''
}

export function suggestionKindLabel(tags: string[] | undefined | null) {
  const kind = suggestionKindFromTags(tags)
  return SUGGESTION_KINDS.find((k) => k.value === kind)?.label || ''
}
