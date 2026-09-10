<template>
  <div class="staff-roster">
    <div class="staff-roster-toolbar">
      <button
        type="button"
        class="staff-btn staff-btn-secondary staff-btn-sm"
        :disabled="busy"
        @click="exportCsv"
      >
        <span class="material-symbols-outlined" aria-hidden="true">download</span>
        Export CSV
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
      <p class="staff-roster-summary">
        {{ confirmedCount }} confirmed · {{ waitingCount }} waiting for YES
      </p>
      <div
        v-for="r in roster"
        :key="r.enrollment_id"
        class="staff-roster-row"
      >
        <div class="staff-roster-who">
          <RouterLink
            :to="{ name: 'ClientDetail', params: { id: r.client_id } }"
            class="staff-roster-name"
          >
            {{ displayName(r) }}
          </RouterLink>
          <span class="staff-roster-meta">{{ r.phone || 'No phone' }}</span>
        </div>
        <span
          class="staff-roster-badge"
          :class="r.confirmed ? 'is-yes' : 'is-wait'"
        >
          {{ r.confirmed ? 'Confirmed' : 'Waiting for YES' }}
        </span>
        <select
          class="staff-input staff-roster-status"
          :value="r.status"
          :disabled="busyId === r.enrollment_id"
          aria-label="Attendance status"
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
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import { staffFetch } from '../api'
import { friendlyError, networkErrorMessage } from '../utils/errors'
import { useToast } from '../composables/useToast'

const props = withDefaults(defineProps<{
  sessionId: number
  sessionName?: string
  sessionDate?: string
  sessionStatus?: string
}>(), {
  sessionName: '',
  sessionDate: '',
  sessionStatus: 'scheduled',
})

const emit = defineEmits<{
  changed: []
  cancelled: []
  deleted: []
}>()

const toast = useToast()

const STATUS_OPTIONS = [
  { value: 'registered', label: 'Registered' },
  { value: 'attended', label: 'Attended' },
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

const confirmedCount = computed(() => roster.value.filter((r) => r.confirmed).length)
const waitingCount = computed(() => roster.value.filter((r) => !r.confirmed).length)

function displayName(entry: RosterEntry) {
  const last = (entry.last_name || '').trim()
  const first = (entry.first_name || '').trim()
  if (last || first) return [last, first].filter(Boolean).join(', ')
  return entry.client_full_name
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

async function exportCsv() {
  busy.value = true
  try {
    const resp = await staffFetch(`/api/staff/classes/${props.sessionId}/roster.csv`)
    if (!resp.ok) {
      toast.error('Could not export that roster.')
      return
    }
    const blob = await resp.blob()
    const header = resp.headers.get('Content-Disposition') || ''
    const match = header.match(/filename="([^"]+)"/)
    const fallback = `${props.sessionName || 'class'}_${props.sessionDate || 'signin'}.csv`
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = match?.[1] || fallback
    link.click()
    URL.revokeObjectURL(url)
  } catch (e) {
    toast.error(networkErrorMessage(e))
  } finally {
    busy.value = false
  }
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
