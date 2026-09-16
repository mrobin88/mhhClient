<template>
  <div class="staff-roster">
    <div class="staff-roster-toolbar">
      <button
        type="button"
        class="staff-btn staff-btn-secondary staff-btn-sm"
        :disabled="busy || loading"
        @click="printRoster"
      >
        <span class="material-symbols-outlined" aria-hidden="true">print</span>
        Print roster
      </button>
      <button
        v-if="sessionStatus !== 'cancelled'"
        type="button"
        class="staff-btn staff-btn-danger staff-btn-sm"
        :disabled="busy"
        @click="ask('cancel')"
      >
        Cancel this date
      </button>
      <button
        type="button"
        class="staff-btn staff-btn-danger-solid staff-btn-sm"
        :disabled="busy"
        @click="ask('delete')"
      >
        Delete this date
      </button>
    </div>

    <div v-if="pending === 'cancel'" class="staff-roster-confirm">
      <p>
        Cancel this date? People on the roster get a text that the class is cancelled.
        The date stays on the list as Cancelled.
      </p>
      <div class="staff-roster-confirm-actions">
        <button type="button" class="staff-btn staff-btn-secondary staff-btn-sm" @click="pending = null">
          Keep the date
        </button>
        <button
          type="button"
          class="staff-btn staff-btn-danger staff-btn-sm"
          :disabled="busy"
          @click="cancelDate"
        >
          Yes, cancel it
        </button>
      </div>
    </div>

    <div v-else-if="pending === 'delete'" class="staff-roster-confirm is-delete">
      <p>
        Delete this date? It is removed completely.
        <template v-if="sessionStatus === 'scheduled'">
          People on the roster get a text that the class is cancelled.
        </template>
      </p>
      <div class="staff-roster-confirm-actions">
        <button type="button" class="staff-btn staff-btn-secondary staff-btn-sm" @click="pending = null">
          Keep the date
        </button>
        <button
          type="button"
          class="staff-btn staff-btn-danger-solid staff-btn-sm"
          :disabled="busy"
          @click="deleteDate"
        >
          Yes, delete it
        </button>
      </div>
    </div>

    <p v-if="loading" class="staff-roster-empty">Loading roster…</p>
    <p v-else-if="roster.length === 0" class="staff-roster-empty">No one signed up yet.</p>
    <template v-else>
      <p class="staff-roster-summary">{{ roster.length }} signed up</p>
      <div
        v-for="r in roster"
        :key="r.enrollment_id"
        class="staff-roster-row staff-roster-row-simple"
      >
        <div class="staff-roster-who">
          <RouterLink
            :to="{ name: 'ClientDetail', params: { id: r.client_id } }"
            class="staff-roster-name"
          >
            {{ displayName(r) }}
          </RouterLink>
        </div>
        <select
          class="staff-input staff-roster-status"
          :value="r.status"
          :disabled="busyId === r.enrollment_id"
          aria-label="Attendance"
          @change="onStatusChange(r, $event)"
        >
          <option v-for="opt in STATUS_OPTIONS" :key="opt.value" :value="opt.value">
            {{ opt.label }}
          </option>
        </select>
        <button
          v-if="pendingRemoveId === r.enrollment_id"
          type="button"
          class="staff-btn staff-btn-danger-solid staff-btn-sm"
          :disabled="busyId === r.enrollment_id"
          @click="removePerson(r)"
        >
          Text &amp; remove
        </button>
        <button
          v-else
          type="button"
          class="staff-btn staff-btn-ghost staff-btn-sm staff-roster-remove"
          :disabled="busyId === r.enrollment_id"
          @click="pendingRemoveId = r.enrollment_id"
        >
          Remove
        </button>
      </div>
      <p v-if="pendingRemoveId" class="staff-roster-hint">
        They will get a text that we are working on a new date — they can call, come in, or wait.
        <button type="button" class="staff-link" @click="pendingRemoveId = null">Never mind</button>
      </p>
    </template>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import { staffFetch } from '../api'
import { friendlyError, networkErrorMessage } from '../utils/errors'
import { useToast } from '../composables/useToast'

const props = withDefaults(defineProps<{
  sessionId: number
  sessionName?: string
  sessionDate?: string
  sessionStatus?: string
  facilitator?: string
  location?: string
  startTime?: string
  endTime?: string
  programLabel?: string
}>(), {
  sessionName: '',
  sessionDate: '',
  sessionStatus: 'scheduled',
  facilitator: '',
  location: '',
  startTime: '',
  endTime: '',
  programLabel: '',
})

const emit = defineEmits<{
  changed: []
  cancelled: []
  deleted: []
}>()

const toast = useToast()

const STATUS_OPTIONS = [
  { value: 'registered', label: 'Registered' },
  { value: 'attended', label: 'Here' },
  { value: 'no_show', label: 'No show' },
  { value: 'cancelled', label: 'Removed' },
]

interface RosterEntry {
  enrollment_id: number
  client_id: number
  client_full_name: string
  first_name: string
  last_name: string
  phone: string
  email: string
  status: string
  status_display: string
  confirmed: boolean
}

const roster = ref<RosterEntry[]>([])
const loading = ref(true)
const busy = ref(false)
const busyId = ref<number | null>(null)
const pending = ref<'cancel' | 'delete' | null>(null)
const pendingRemoveId = ref<number | null>(null)

function displayName(entry: RosterEntry) {
  const last = (entry.last_name || '').trim()
  const first = (entry.first_name || '').trim()
  if (last || first) return [last, first].filter(Boolean).join(', ')
  return entry.client_full_name || 'No name on file'
}

function formatDate(dateStr: string) {
  const d = new Date(`${dateStr}T00:00:00`)
  if (Number.isNaN(d.getTime())) return dateStr
  return d.toLocaleDateString(undefined, {
    weekday: 'long',
    month: 'long',
    day: 'numeric',
    year: 'numeric',
  })
}

function formatTime(t: string) {
  if (!t) return ''
  const [h, m] = t.split(':').map(Number)
  const period = h >= 12 ? 'PM' : 'AM'
  const hour12 = h % 12 === 0 ? 12 : h % 12
  return `${hour12}:${String(m).padStart(2, '0')} ${period}`
}

function escapeHtml(value: string) {
  return value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

async function loadRoster() {
  loading.value = true
  try {
    const resp = await staffFetch(`/api/staff/classes/${props.sessionId}/roster/`)
    const body = resp.ok ? await resp.json() : { roster: [] }
    roster.value = body.roster || []
  } catch {
    roster.value = []
  } finally {
    loading.value = false
  }
}

function ask(kind: 'cancel' | 'delete') {
  pending.value = pending.value === kind ? null : kind
  pendingRemoveId.value = null
}

function printRoster() {
  const names = roster.value.map((r) => displayName(r))
  const blankRows = Math.max(6, 12 - names.length)
  const timeRange = [formatTime(props.startTime), formatTime(props.endTime)].filter(Boolean).join(' – ')
  const meta = [
    props.programLabel,
    props.sessionDate ? formatDate(props.sessionDate) : '',
    timeRange,
    props.location,
    props.facilitator ? `Facilitator: ${props.facilitator}` : '',
  ].filter(Boolean).join(' · ')

  const rows = [
    ...names.map((name) => `
      <tr>
        <td class="check"></td>
        <td class="name">${escapeHtml(name)}</td>
        <td class="notes"></td>
      </tr>`),
    ...Array.from({ length: blankRows }, () => `
      <tr>
        <td class="check"></td>
        <td class="name"></td>
        <td class="notes"></td>
      </tr>`),
  ].join('')

  const html = `<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>${escapeHtml(props.sessionName || 'Class roster')}</title>
  <style>
    @page { margin: 0.6in; }
    body { font-family: Georgia, "Times New Roman", serif; color: #111; margin: 0; }
    h1 { font-size: 20px; margin: 0 0 4px; }
    .meta { font-size: 12px; margin-bottom: 14px; }
    table { width: 100%; border-collapse: collapse; }
    th, td { border: 1px solid #222; padding: 8px 10px; font-size: 13px; }
    th { text-align: left; background: #f3f3f3; }
    td.check { width: 36px; }
    td.name { width: 42%; }
    td.notes { height: 28px; }
    .pad { margin-top: 22px; }
    .pad h2 { font-size: 14px; margin: 0 0 8px; }
    .lines { border: 1px solid #222; min-height: 160px; }
    .lines div { border-bottom: 1px solid #ccc; height: 28px; }
  </style>
</head>
<body>
  <h1>${escapeHtml(props.sessionName || 'Class roster')}</h1>
  <p class="meta">${escapeHtml(meta)} · ${names.length} signed up</p>
  <table>
    <thead>
      <tr><th></th><th>Name</th><th>Notes</th></tr>
    </thead>
    <tbody>${rows}</tbody>
  </table>
  <div class="pad">
    <h2>Class notes</h2>
    <div class="lines">
      <div></div><div></div><div></div><div></div><div></div>
    </div>
  </div>
</body>
</html>`

  const frame = window.open('', '_blank')
  if (!frame) {
    toast.error('Allow pop-ups to print the roster.')
    return
  }
  frame.document.write(html)
  frame.document.close()
  frame.focus()
  frame.print()
}

async function cancelDate() {
  busy.value = true
  try {
    const resp = await staffFetch(`/api/staff/classes/sessions/${props.sessionId}/`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status: 'cancelled' }),
    })
    const body = await resp.json().catch(() => null)
    if (!resp.ok) {
      toast.error(friendlyError(body, 'Could not cancel that date.'))
      return
    }
    toast.success(body?.message || 'Date cancelled.')
    pending.value = null
    emit('cancelled')
    emit('changed')
  } catch (e) {
    toast.error(networkErrorMessage(e))
  } finally {
    busy.value = false
  }
}

async function deleteDate() {
  busy.value = true
  try {
    const resp = await staffFetch(`/api/staff/classes/sessions/${props.sessionId}/`, {
      method: 'DELETE',
    })
    const body = await resp.json().catch(() => null)
    if (!resp.ok) {
      toast.error(friendlyError(body, 'Could not delete that date.'))
      return
    }
    toast.success(body?.message || 'Date deleted.')
    pending.value = null
    emit('deleted')
    emit('changed')
  } catch (e) {
    toast.error(networkErrorMessage(e))
  } finally {
    busy.value = false
  }
}

async function onStatusChange(entry: RosterEntry, event: Event) {
  const newStatus = (event.target as HTMLSelectElement).value
  const previous = entry.status
  busyId.value = entry.enrollment_id
  try {
    const resp = await staffFetch(`/api/staff/classes/enrollments/${entry.enrollment_id}/status/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status: newStatus }),
    })
    const body = await resp.json().catch(() => null)
    if (!resp.ok) {
      toast.error(friendlyError(body, 'Could not update that.'))
      ;(event.target as HTMLSelectElement).value = previous
      return
    }
    if (newStatus === 'cancelled') {
      roster.value = roster.value.filter((r) => r.enrollment_id !== entry.enrollment_id)
      toast.success(body?.message || 'Removed.')
    } else {
      entry.status = newStatus
    }
    emit('changed')
  } catch (e) {
    ;(event.target as HTMLSelectElement).value = previous
    toast.error(networkErrorMessage(e))
  } finally {
    busyId.value = null
  }
}

async function removePerson(entry: RosterEntry) {
  busyId.value = entry.enrollment_id
  try {
    const resp = await staffFetch(`/api/staff/classes/enrollments/${entry.enrollment_id}/status/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status: 'cancelled' }),
    })
    const body = await resp.json().catch(() => null)
    if (!resp.ok) {
      toast.error(friendlyError(body, 'Could not remove them.'))
      return
    }
    roster.value = roster.value.filter((r) => r.enrollment_id !== entry.enrollment_id)
    pendingRemoveId.value = null
    toast.success(body?.message || 'Removed. They were texted about a new date.')
    emit('changed')
  } catch (e) {
    toast.error(networkErrorMessage(e))
  } finally {
    busyId.value = null
  }
}

watch(() => props.sessionId, loadRoster)
onMounted(loadRoster)
</script>
