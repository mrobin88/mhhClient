<template>
  <section class="space-y-3">
    <div class="staff-card p-4">
      <div class="staff-panel-header">
        <span class="material-symbols-outlined" aria-hidden="true">confirmation_number</span>
        <h3>Tickets</h3>
        <StaffTip text="Report bugs, screenshot errors, and track what needs fixing. Your tickets = ones you opened or were assigned. All tickets = everyone’s." />
        <button
          type="button"
          class="staff-btn staff-btn-secondary shrink-0"
          @click="showCreate = !showCreate"
        >
          {{ showCreate ? 'Cancel' : '+ New ticket' }}
        </button>
      </div>

      <div class="staff-chip-row">
        <button
          type="button"
          class="staff-chip"
          :class="{ 'staff-chip-active': scope === 'mine' }"
          @click="setScope('mine')"
        >
          Your tickets
        </button>
        <button
          type="button"
          class="staff-chip"
          :class="{ 'staff-chip-active': scope === 'all' }"
          @click="setScope('all')"
        >
          All tickets
        </button>
      </div>
    </div>

    <form v-if="showCreate" class="staff-card p-4 space-y-3" @submit.prevent="createTicket">
      <div class="staff-panel-header">
        <span class="material-symbols-outlined" aria-hidden="true">add_circle</span>
        <h3>New ticket</h3>
      </div>
      <div class="staff-field">
        <label for="tk-title">What’s needed (short title)</label>
        <input id="tk-title" v-model="form.title" type="text" class="staff-input" maxlength="200" placeholder="e.g. Client page won’t save phone" />
      </div>
      <div class="staff-field">
        <label for="tk-desc">Details</label>
        <textarea
          id="tk-desc"
          v-model="form.description"
          rows="4"
          class="staff-input"
          placeholder="What happened, what you expected, and steps to reproduce."
        />
      </div>
      <div class="staff-field">
        <label>How urgent?</label>
        <div class="staff-seg">
          <button
            v-for="opt in meta.priorities"
            :key="opt.value"
            type="button"
            class="staff-seg-btn"
            :class="{ 'staff-seg-btn-active': form.priority === opt.value }"
            @click="form.priority = opt.value"
          >
            {{ opt.value.toUpperCase() }}
          </button>
        </div>
        <p class="text-xs text-stone-500 mt-1">{{ priorityHint }}</p>
      </div>
      <div class="staff-field">
        <label>Tags</label>
        <div class="staff-chip-row" style="margin-bottom: 0;">
          <button
            v-for="opt in meta.tags"
            :key="opt.value"
            type="button"
            class="staff-chip"
            :class="{ 'staff-chip-active': form.tags.includes(opt.value) }"
            @click="toggleFormTag(opt.value)"
          >
            {{ opt.label }}
          </button>
        </div>
      </div>
      <div class="staff-field">
        <label for="tk-files">Screenshots / documents</label>
        <input id="tk-files" type="file" class="staff-input" multiple accept="image/*,.pdf,.doc,.docx,.txt" @change="onFiles" />
        <p v-if="form.files.length" class="text-xs text-stone-500 mt-1">{{ form.files.length }} file(s) ready</p>
      </div>
      <button type="submit" class="staff-btn staff-btn-primary w-full" :disabled="creating">
        {{ creating ? 'Creating…' : 'Create ticket' }}
      </button>
    </form>

    <BulldozerLoader v-if="loading" label="Loading tickets…" />
    <div v-else-if="error" class="staff-card p-4 text-center space-y-3">
      <p class="text-sm">{{ error }}</p>
      <button type="button" class="staff-btn staff-btn-secondary" @click="load">Retry</button>
    </div>
    <p v-else-if="tickets.length === 0" class="text-sm text-stone-500 text-center py-8">
      No tickets in this list yet.
    </p>
    <ul v-else class="space-y-2">
      <li v-for="t in tickets" :key="t.id">
        <RouterLink
          :to="{ name: 'TicketDetail', params: { id: t.id } }"
          class="staff-card block p-4 hover:border-orange-300 transition-colors"
        >
          <div class="flex items-start justify-between gap-2">
            <div class="min-w-0">
              <p class="font-semibold truncate">#{{ t.id }} · {{ t.title }}</p>
              <p class="text-xs text-stone-500 mt-0.5">
                {{ t.status_display }} · {{ t.priority_display }}
                <span v-if="t.assignee_name"> · {{ t.assignee_name }}</span>
              </p>
            </div>
            <span
              class="text-[10px] uppercase font-bold tracking-wide rounded-full px-2 py-0.5 shrink-0"
              :class="statusClass(t.status)"
            >
              {{ t.status }}
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
import BulldozerLoader from './BulldozerLoader.vue'
import StaffTip from './StaffTip.vue'

interface TicketRow {
  id: number
  title: string
  description: string
  status: string
  status_display: string
  priority: string
  priority_display: string
  assignee_name?: string | null
  updated_at: string
  attachment_count: number
}

interface MetaOpt {
  value: string
  label: string
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
const meta = reactive({
  priorities: [] as MetaOpt[],
  tags: [] as MetaOpt[],
  statuses: [] as MetaOpt[],
  resolutions: [] as MetaOpt[],
})

const form = reactive({
  title: '',
  description: '',
  priority: 'p2',
  tags: [] as string[],
  files: [] as File[],
})

const priorityHint = computed(() => {
  const hit = meta.priorities.find((p) => p.value === form.priority)
  return hit?.label || ''
})

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

function toggleFormTag(value: string) {
  const i = form.tags.indexOf(value)
  if (i >= 0) form.tags.splice(i, 1)
  else form.tags.push(value)
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
      error.value = friendlyError(body, 'Could not load tickets.')
      return
    }
    tickets.value = body.results || []
    if (body.meta) {
      meta.priorities = body.meta.priorities || []
      meta.tags = body.meta.tags || []
      meta.statuses = body.meta.statuses || []
      meta.resolutions = body.meta.resolutions || []
    }
  } catch (e) {
    error.value = networkErrorMessage(e)
  } finally {
    loading.value = false
  }
}

function applyCreatePrefill() {
  if (String(route.query.create || '') !== '1') return
  showCreate.value = true
  form.title = String(route.query.title || '').slice(0, 180)
  form.description = String(route.query.description || '').slice(0, 4000)
  const requestedTags = String(route.query.tags || '')
    .split(',')
    .map((value) => value.trim())
    .filter(Boolean)
  const allowedTags = new Set(meta.tags.map((option) => option.value))
  form.tags = requestedTags.filter((value) => allowedTags.has(value))
}

async function createTicket() {
  if (!form.title.trim() || !form.description.trim()) {
    toast.error('Title and details are required.')
    return
  }
  creating.value = true
  try {
    const fd = new FormData()
    fd.append('title', form.title.trim())
    fd.append('description', form.description.trim())
    fd.append('priority', form.priority)
    fd.append('tags', JSON.stringify(form.tags))
    for (const f of form.files) fd.append('attachments', f)

    const resp = await staffFetch('/api/staff/tickets/', { method: 'POST', body: fd })
    const body = await resp.json().catch(() => null)
    if (!resp.ok) {
      toast.error(friendlyError(body, 'Could not create ticket.'))
      return
    }
    toast.success('Ticket created.')
    showCreate.value = false
    form.title = ''
    form.description = ''
    form.priority = 'p2'
    form.tags = []
    form.files = []
    router.push({ name: 'TicketDetail', params: { id: body.id } })
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
