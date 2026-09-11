<template>
  <section class="space-y-3">
    <div class="staff-card p-4">
      <div class="staff-panel-header">
        <span class="material-symbols-outlined" aria-hidden="true">lightbulb</span>
        <h3>Suggestion box</h3>
        <StaffTip text="Drop an idea, a problem, or a request. Yours = notes you opened. Everyone = the whole box." />
        <button
          type="button"
          class="staff-btn staff-btn-secondary shrink-0"
          @click="showCreate = !showCreate"
        >
          {{ showCreate ? 'Cancel' : '+ New suggestion' }}
        </button>
      </div>

      <div class="staff-chip-row">
        <button
          type="button"
          class="staff-chip"
          :class="{ 'staff-chip-active': scope === 'mine' }"
          @click="setScope('mine')"
        >
          Yours
        </button>
        <button
          type="button"
          class="staff-chip"
          :class="{ 'staff-chip-active': scope === 'all' }"
          @click="setScope('all')"
        >
          Everyone
        </button>
      </div>
    </div>

    <form v-if="showCreate" class="staff-card p-4 space-y-3" @submit.prevent="createTicket">
      <div class="staff-panel-header">
        <span class="material-symbols-outlined" aria-hidden="true">add_circle</span>
        <h3>New suggestion</h3>
      </div>
      <div class="staff-field">
        <label>What kind?</label>
        <div class="staff-chip-row" style="margin-bottom: 0;">
          <button
            v-for="k in SUGGESTION_KINDS"
            :key="k.value"
            type="button"
            class="staff-chip"
            :class="{ 'staff-chip-active': form.kind === k.value }"
            @click="form.kind = k.value"
          >
            {{ k.label }}
          </button>
        </div>
        <p class="text-xs text-stone-500 mt-1">{{ kindHint }}</p>
      </div>
      <div class="staff-field">
        <label for="tk-desc">The idea, problem, or request</label>
        <textarea
          id="tk-desc"
          v-model="form.description"
          rows="4"
          class="staff-input"
          placeholder="Write it in your own words. A screenshot helps if something looks wrong."
        />
      </div>
      <div class="staff-field">
        <label for="tk-files">Screenshot or file (optional)</label>
        <input id="tk-files" type="file" class="staff-input" multiple accept="image/*,.pdf,.doc,.docx,.txt" @change="onFiles" />
        <p v-if="form.files.length" class="text-xs text-stone-500 mt-1">{{ form.files.length }} file(s) ready</p>
      </div>
      <button type="submit" class="staff-btn staff-btn-primary w-full" :disabled="creating">
        {{ creating ? 'Sending…' : 'Drop in the box' }}
      </button>
    </form>

    <BulldozerLoader v-if="loading" label="Loading suggestions…" />
    <div v-else-if="error" class="staff-card p-4 text-center space-y-3">
      <p class="text-sm">{{ error }}</p>
      <button type="button" class="staff-btn staff-btn-secondary" @click="load">Retry</button>
    </div>
    <p v-else-if="tickets.length === 0" class="text-sm text-stone-500 text-center py-8">
      Nothing in this list yet.
    </p>
    <ul v-else class="space-y-2">
      <li v-for="t in tickets" :key="t.id">
        <RouterLink
          :to="{ name: 'TicketDetail', params: { id: t.id } }"
          class="staff-card block p-4 staff-hover-accent transition-colors"
        >
          <div class="flex items-start justify-between gap-2">
            <div class="min-w-0">
              <p class="font-semibold truncate">{{ t.title }}</p>
              <p class="text-xs text-stone-500 mt-0.5">
                {{ suggestionKindLabel(t.tags) || t.status_display }}
                <span v-if="t.assignee_name"> · {{ t.assignee_name }}</span>
              </p>
            </div>
            <span
              class="text-[10px] uppercase font-bold tracking-wide rounded-full px-2 py-0.5 shrink-0"
              :class="statusClass(t.status)"
            >
              {{ t.status_display }}
            </span>
          </div>
          <p class="text-sm text-stone-600 mt-2 line-clamp-2">{{ t.description }}</p>
          <p class="text-xs text-stone-400 mt-2">
            Updated {{ formatWhen(t.updated_at) }}
            <span v-if="t.attachment_count"> · {{ t.attachment_count }} file(s)</span>
          </p>
        </RouterLink>
      </li>
    </ul>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { staffFetch } from '../api'
import { friendlyError, networkErrorMessage } from '../utils/errors'
import { useToast } from '../composables/useToast'
import {
  SUGGESTION_KINDS,
  suggestionKindFromTags,
  suggestionKindLabel,
  suggestionPriority,
  suggestionTitleFromBody,
  type SuggestionKind,
} from '../suggestions'
import BulldozerLoader from './BulldozerLoader.vue'
import StaffTip from './StaffTip.vue'

interface TicketRow {
  id: number
  title: string
  description: string
  status: string
  status_display: string
  tags?: string[]
  assignee_name?: string | null
  updated_at: string
  attachment_count: number
}

const route = useRoute()
const router = useRouter()
const toast = useToast()

const scope = ref<'mine' | 'all'>((route.query.scope as 'mine' | 'all') || 'mine')
const tickets = ref<TicketRow[]>([])
const loading = ref(true)
const error = ref('')
const showCreate = ref(false)
const creating = ref(false)
const form = reactive({
  kind: 'idea' as SuggestionKind,
  description: '',
  files: [] as File[],
})

const kindHint = computed(
  () => SUGGESTION_KINDS.find((k) => k.value === form.kind)?.hint || '',
)

function statusClass(status: string) {
  if (status === 'open') return 'bg-sky-100 text-sky-800'
  if (status === 'in_progress') return 'bg-amber-100 text-amber-800'
  if (status === 'blocked') return 'bg-red-100 text-red-800'
  if (status === 'resolved' || status === 'closed') return 'bg-emerald-100 text-emerald-800'
  return 'bg-stone-100 text-stone-600'
}

function formatWhen(iso: string) {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return ''
  return d.toLocaleString(undefined, { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' })
}

function setScope(next: 'mine' | 'all') {
  scope.value = next
  router.replace({ name: 'Tickets', query: { scope: next } })
  load()
}

function onFiles(e: Event) {
  const input = e.target as HTMLInputElement
  form.files = input.files ? Array.from(input.files) : []
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const resp = await staffFetch(`/api/staff/tickets/?scope=${scope.value}&limit=50`)
    const body = await resp.json().catch(() => null)
    if (!resp.ok) {
      error.value = friendlyError(body, 'Could not load suggestions.')
      return
    }
    tickets.value = body.results || []
  } catch (e) {
    error.value = networkErrorMessage(e)
  } finally {
    loading.value = false
  }
}

function applyCreatePrefill() {
  if (String(route.query.create || '') !== '1') return
  showCreate.value = true
  form.description = String(route.query.description || '').slice(0, 4000)
  const requestedTags = String(route.query.tags || '')
    .split(',')
    .map((value) => value.trim())
    .filter(Boolean)
  const fromTags = suggestionKindFromTags(requestedTags)
  if (fromTags) form.kind = fromTags
  const title = String(route.query.title || '').trim()
  if (title && !form.description) form.description = title
  else if (title && form.description && !form.description.startsWith(title)) {
    form.description = `${title}\n\n${form.description}`
  }
}

async function createTicket() {
  if (!form.description.trim()) {
    toast.error('Write the suggestion first.')
    return
  }
  creating.value = true
  try {
    const bodyText = form.description.trim()
    const fd = new FormData()
    fd.append('title', suggestionTitleFromBody(bodyText))
    fd.append('description', bodyText)
    fd.append('priority', suggestionPriority(form.kind))
    fd.append('tags', JSON.stringify([form.kind]))
    for (const f of form.files) fd.append('attachments', f)

    const resp = await staffFetch('/api/staff/tickets/', { method: 'POST', body: fd })
    const body = await resp.json().catch(() => null)
    if (!resp.ok) {
      toast.error(friendlyError(body, 'Could not send that suggestion.'))
      return
    }
    toast.success('In the suggestion box.')
    showCreate.value = false
    form.kind = 'idea'
    form.description = ''
    form.files = []
    await load()
  } catch (e) {
    toast.error(networkErrorMessage(e))
  } finally {
    creating.value = false
  }
}

onMounted(async () => {
  await load()
  applyCreatePrefill()
})
</script>
