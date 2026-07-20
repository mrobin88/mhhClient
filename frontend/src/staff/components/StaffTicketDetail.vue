<template>
  <section class="space-y-3">
    <button type="button" class="text-sm font-semibold text-orange-600" @click="router.push({ name: 'Tickets' })">
      ← All tickets
    </button>

    <BulldozerLoader v-if="loading" label="Loading ticket…" />
    <div v-else-if="error" class="staff-card p-4 text-center space-y-3">
      <p class="text-sm">{{ error }}</p>
      <button type="button" class="staff-btn staff-btn-secondary" @click="load">Retry</button>
    </div>

    <template v-else-if="ticket">
      <div class="staff-card p-4">
        <div class="flex items-start justify-between gap-2 mb-2">
          <h2 class="text-lg font-bold">#{{ ticket.id }} · {{ ticket.title }}</h2>
          <span
            class="text-[10px] uppercase font-bold tracking-wide rounded-full px-2 py-0.5 shrink-0"
            :class="statusClass(ticket.status)"
          >
            {{ ticket.status }}
          </span>
        </div>
        <p class="text-xs text-stone-500 mb-3">
          {{ ticket.priority_display }}
          · Opened by {{ ticket.submitted_by_name || 'Unknown' }}
          · {{ formatWhen(ticket.created_at) }}
          <span v-if="ticket.resolution_display"> · {{ ticket.resolution_display }}</span>
        </p>
        <p class="text-sm whitespace-pre-wrap">{{ ticket.description }}</p>
        <div v-if="ticket.tags?.length" class="staff-chip-row mt-3" style="margin-bottom: 0;">
          <span v-for="tag in ticket.tags" :key="tag" class="staff-chip staff-chip-active">{{ tag }}</span>
        </div>
      </div>

      <div class="staff-card p-4">
        <div class="staff-panel-header">
          <span class="material-symbols-outlined" aria-hidden="true">tune</span>
          <h3>Quick actions</h3>
          <StaffTip text="Change status, priority, assignee, or tags here without leaving the page. Resolution codes appear when you mark Resolved or Closed." />
        </div>
        <TicketQuickActionBox
          v-if="metaReady"
          :ticket-id="ticket.id"
          :ticket="ticket"
          :statuses="meta.statuses"
          :resolutions="meta.resolutions"
          :priorities="meta.priorities"
          :tags="meta.tags"
          :show-deep-link="false"
          @updated="onUpdated"
        />
      </div>

      <div class="staff-card p-4 space-y-3">
        <div class="staff-panel-header">
          <span class="material-symbols-outlined" aria-hidden="true">attach_file</span>
          <h3>Screenshots &amp; files</h3>
          <StaffTip text="Upload error screenshots or documents so tech can see what you saw." />
        </div>

        <ul v-if="ticket.attachments?.length" class="space-y-2">
          <li v-for="att in ticket.attachments" :key="att.id" class="flex items-center justify-between gap-2 border-t border-stone-100 pt-2 first:border-0 first:pt-0">
            <div class="min-w-0 text-sm">
              <a
                v-if="att.url"
                :href="att.url"
                target="_blank"
                rel="noopener"
                class="staff-activity-link truncate block"
              >
                {{ att.original_name || 'Attachment' }}
              </a>
              <span v-else class="truncate block">{{ att.original_name || 'Attachment' }}</span>
              <span class="text-xs text-stone-400">{{ formatWhen(att.created_at) }}</span>
            </div>
            <img
              v-if="isImage(att) && att.url"
              :src="att.url"
              :alt="att.original_name"
              class="w-14 h-14 object-cover rounded-md border border-stone-200 shrink-0"
            />
          </li>
        </ul>
        <p v-else class="text-sm text-stone-500">No files yet.</p>

        <input type="file" class="staff-input" multiple accept="image/*,.pdf,.doc,.docx,.txt" @change="onUpload" />
        <p v-if="uploading" class="text-xs text-stone-500">Uploading…</p>
      </div>
    </template>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { staffFetch } from '../api'
import { friendlyError, networkErrorMessage } from '../utils/errors'
import { useToast } from '../composables/useToast'
import BulldozerLoader from './BulldozerLoader.vue'
import StaffTip from './StaffTip.vue'
import TicketQuickActionBox from './TicketQuickActionBox.vue'

interface Attachment {
  id: number
  original_name: string
  content_type: string
  url: string
  created_at: string
}

interface TicketDetail {
  id: number
  title: string
  description: string
  status: string
  status_display: string
  resolution: string
  resolution_display: string
  priority: string
  priority_display: string
  tags: string[]
  submitted_by_name?: string | null
  assignee_id: number | null
  assignee_name: string | null
  created_at: string
  updated_at: string
  attachments?: Attachment[]
}

interface MetaOpt {
  value: string
  label: string
}

const route = useRoute()
const router = useRouter()
const toast = useToast()

const ticket = ref<TicketDetail | null>(null)
const loading = ref(true)
const error = ref('')
const uploading = ref(false)
const meta = reactive({
  statuses: [] as MetaOpt[],
  resolutions: [] as MetaOpt[],
  priorities: [] as MetaOpt[],
  tags: [] as MetaOpt[],
})

const metaReady = computed(() => meta.statuses.length > 0)

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

function isImage(att: Attachment) {
  return (att.content_type || '').startsWith('image/') || /\.(png|jpe?g|gif|webp)$/i.test(att.original_name || '')
}

function onUpdated(body: TicketDetail) {
  ticket.value = { ...ticket.value!, ...body }
}

async function loadMeta() {
  const resp = await staffFetch('/api/staff/tickets/meta/')
  if (!resp.ok) return
  const body = await resp.json()
  meta.statuses = body.statuses || []
  meta.resolutions = body.resolutions || []
  meta.priorities = body.priorities || []
  meta.tags = body.tags || []
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const id = Number(route.params.id)
    const resp = await staffFetch(`/api/staff/tickets/${id}/`)
    const body = await resp.json().catch(() => null)
    if (!resp.ok) {
      error.value = friendlyError(body, 'Ticket not found.')
      return
    }
    ticket.value = body
  } catch (e) {
    error.value = networkErrorMessage(e)
  } finally {
    loading.value = false
  }
}

async function onUpload(e: Event) {
  const input = e.target as HTMLInputElement
  const files = input.files ? Array.from(input.files) : []
  if (!files.length || !ticket.value) return
  uploading.value = true
  try {
    const fd = new FormData()
    for (const f of files) fd.append('attachments', f)
    const resp = await staffFetch(`/api/staff/tickets/${ticket.value.id}/attachments/`, {
      method: 'POST',
      body: fd,
    })
    const body = await resp.json().catch(() => null)
    if (!resp.ok) {
      toast.error(friendlyError(body, 'Upload failed.'))
      return
    }
    toast.success('File(s) uploaded.')
    await load()
  } catch (err) {
    toast.error(networkErrorMessage(err))
  } finally {
    uploading.value = false
    input.value = ''
  }
}

onMounted(async () => {
  await loadMeta()
  await load()
})
watch(() => route.params.id, load)
</script>
