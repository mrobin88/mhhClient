<template>
  <div class="space-y-2">
    <p class="text-xs font-semibold text-stone-500 uppercase tracking-wide">Add to a class</p>

    <div v-if="classBusy" class="relative">
      <div class="absolute inset-0 bg-white/70 rounded-xl flex items-center justify-center z-10">
        <BulldozerLoader label="Updating classes…" />
      </div>
    </div>

    <CardSkeleton v-if="loading" variant="list" :count="2" />
    <template v-else>
      <div v-if="enrolled.length" class="space-y-1.5">
        <p class="text-xs text-stone-500">Already signed up</p>
        <div
          v-for="ec in enrolled"
          :key="ec.enrollment_id"
          class="text-sm border-t border-stone-100 pt-1.5 first:border-0 first:pt-0"
        >
          <span class="font-medium">{{ ec.template_name }}</span>
          <span
            class="staff-roster-badge ml-1.5"
            :class="ec.confirmed ? 'is-yes' : 'is-wait'"
          >
            {{ ec.confirmed ? 'Confirmed' : 'Waiting for YES' }}
          </span>
          <div class="text-xs text-stone-500">
            {{ formatSessionDate(ec.session_date) }} · {{ formatTimeRange(ec.start_time, ec.end_time) }}
          </div>
        </div>
      </div>
      <p v-else class="text-sm text-stone-500">Not in an upcoming class yet.</p>

      <div class="staff-chip-row">
        <button
          v-for="chip in CATEGORY_CHIPS"
          :key="chip.value"
          type="button"
          class="staff-chip"
          :class="{ 'staff-chip-active': categoryFilter === chip.value }"
          @click="categoryFilter = chip.value"
        >
          {{ chip.label }}
        </button>
      </div>

      <div class="flex gap-2">
        <select v-model="selectedSessionId" class="staff-input flex-1">
          <option value="">
            {{ filteredSessions.length ? 'Choose a class date…' : 'No matching classes' }}
          </option>
          <optgroup
            v-for="(sessions, category) in groupedFilteredSessions"
            :key="category"
            :label="category"
          >
            <option
              v-for="s in sessions"
              :key="s.id"
              :value="s.id"
              :disabled="s.spots_remaining <= 0 || isAlreadyEnrolled(s.id)"
            >
              {{ s.template_name }} — {{ formatSessionDate(s.session_date) }}, {{ formatTimeRange(s.start_time, s.end_time) }}
              {{ isAlreadyEnrolled(s.id) ? '(already added)' : s.spots_remaining > 0 ? `(${s.spots_remaining} spots)` : '(full)' }}
            </option>
          </optgroup>
        </select>
        <button
          type="button"
          class="staff-btn staff-btn-primary shrink-0"
          :disabled="!selectedSessionId || classBusy"
          @click="enroll"
        >
          Add
        </button>
      </div>

      <div v-if="selectedSessionId" class="rounded-xl border border-stone-200 bg-stone-50 p-3">
        <p class="text-xs font-semibold text-stone-500 uppercase tracking-wide mb-1">Confirmation text</p>
        <p v-if="textPreviewLoading" class="text-xs text-stone-400">Loading message…</p>
        <template v-else-if="textPreview">
          <p class="text-sm text-stone-700 whitespace-pre-line">{{ textPreview.body }}</p>
          <p v-if="textPreview.will_send" class="text-xs text-emerald-700 font-semibold mt-1.5">
            Sends to {{ textPreview.to_phone }} when you press Add.
          </p>
          <p v-else class="text-xs text-amber-700 font-semibold mt-1.5">
            No text will be sent — {{ textPreview.reason }}
          </p>
        </template>
      </div>

      <p v-if="upcoming.length === 0" class="text-xs text-stone-400">
        No upcoming classes —
        <RouterLink to="/classes" class="staff-link font-semibold">schedule one</RouterLink>.
      </p>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import { staffFetch } from '../api'
import { friendlyError, networkErrorMessage } from '../utils/errors'
import { useToast } from '../composables/useToast'
import BulldozerLoader from './BulldozerLoader.vue'
import CardSkeleton from './dashboard/CardSkeleton.vue'

const CATEGORY_CHIPS = [
  { value: '', label: 'All' },
  { value: 'orientation', label: 'Orientation' },
  { value: 'job_readiness', label: 'JRT' },
  { value: 'resume_workshop', label: 'Resume' },
  { value: 'training', label: 'Skills' },
  { value: 'other', label: 'Other' },
]

interface UpcomingSession {
  id: number
  template_name: string
  category: string
  category_display: string
  session_date: string
  start_time: string
  end_time: string
  spots_remaining: number
}

interface ClassTextPreview {
  will_send: boolean
  reason: string
  to_phone: string
  body: string
}

interface ClientClassEnrollment {
  enrollment_id: number
  session_id: number
  template_name: string
  session_date: string
  start_time: string
  end_time: string
  confirmed: boolean
}

const props = defineProps<{ clientId: number }>()

const toast = useToast()
const upcoming = ref<UpcomingSession[]>([])
const enrolled = ref<ClientClassEnrollment[]>([])
const selectedSessionId = ref<number | ''>('')
const classBusy = ref(false)
const loading = ref(true)
const categoryFilter = ref('')
const textPreview = ref<ClassTextPreview | null>(null)
const textPreviewLoading = ref(false)

const filteredSessions = computed(() => {
  if (!categoryFilter.value) return upcoming.value
  return upcoming.value.filter((s) => s.category === categoryFilter.value)
})

const groupedFilteredSessions = computed(() => {
  const groups: Record<string, UpcomingSession[]> = {}
  for (const s of filteredSessions.value) {
    if (!groups[s.category_display]) groups[s.category_display] = []
    groups[s.category_display].push(s)
  }
  return groups
})

function isAlreadyEnrolled(sessionId: number) {
  return enrolled.value.some((e) => e.session_id === sessionId)
}

function formatSessionDate(dateStr: string) {
  const d = new Date(`${dateStr}T00:00:00`)
  return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })
}

function formatTimeRange(start: string, end: string) {
  const fmt = (t: string) => {
    const [h, m] = t.split(':').map(Number)
    const period = h >= 12 ? 'PM' : 'AM'
    const hour12 = h % 12 === 0 ? 12 : h % 12
    return `${hour12}:${String(m).padStart(2, '0')} ${period}`
  }
  return `${fmt(start)}–${fmt(end)}`
}

async function loadClasses() {
  loading.value = true
  try {
    const [upcomingResp, clientClassesResp] = await Promise.all([
      staffFetch('/api/staff/classes/upcoming/'),
      staffFetch(`/api/staff/clients/${props.clientId}/classes/`),
    ])
    const upcomingBody = upcomingResp.ok ? await upcomingResp.json() : { results: [] }
    upcoming.value = upcomingBody.results || []
    const clientClassesBody = clientClassesResp.ok ? await clientClassesResp.json() : { results: [] }
    enrolled.value = clientClassesBody.results || []
  } catch {
    /* Search still shows client info if class load fails. */
  } finally {
    loading.value = false
  }
}

async function loadTextPreview(sessionId: number) {
  textPreviewLoading.value = true
  textPreview.value = null
  try {
    const resp = await staffFetch(
      `/api/staff/classes/${sessionId}/text-preview/?client_id=${props.clientId}`,
    )
    if (!resp.ok) return
    textPreview.value = await resp.json()
  } catch {
    /* Enrolling still works without preview. */
  } finally {
    textPreviewLoading.value = false
  }
}

watch(
  () => props.clientId,
  () => {
    selectedSessionId.value = ''
    textPreview.value = null
    categoryFilter.value = ''
    loadClasses()
  },
  { immediate: true },
)

watch(selectedSessionId, (sessionId) => {
  if (!sessionId) {
    textPreview.value = null
    return
  }
  loadTextPreview(Number(sessionId))
})

async function enroll() {
  if (!selectedSessionId.value) return
  classBusy.value = true
  try {
    const resp = await staffFetch(`/api/staff/classes/${selectedSessionId.value}/enroll/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ client_id: props.clientId }),
    })
    const body = await resp.json().catch(() => null)
    if (!resp.ok) {
      toast.error(friendlyError(body, 'Could not add client to that class.'))
      return
    }
    toast.success(body?.message || 'Added to class.')
    if (body?.text_warning) toast.error(body.text_warning)
    selectedSessionId.value = ''
    await loadClasses()
  } catch (e) {
    toast.error(networkErrorMessage(e))
  } finally {
    classBusy.value = false
  }
}
</script>
