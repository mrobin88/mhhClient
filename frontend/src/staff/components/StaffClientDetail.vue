<template>
  <section class="space-y-3">
    <button type="button" class="text-sm font-semibold text-orange-600" @click="router.back()">
      ← Back
    </button>

    <BulldozerLoader v-if="loading" label="Loading client…" />
    <div v-else-if="error" class="staff-card p-4 text-center space-y-3">
      <p class="text-sm">{{ error }}</p>
      <button type="button" class="staff-btn staff-btn-secondary" @click="load">Retry</button>
    </div>

    <template v-else-if="client">
      <div class="staff-card p-4">
        <h2 class="text-lg font-bold">{{ client.full_name }}</h2>
        <p class="text-sm text-stone-600">{{ client.phone }}</p>
        <p class="text-sm text-stone-600">{{ client.status }} · {{ client.staff_name || 'Unassigned' }}</p>
      </div>

      <div class="staff-card p-4 relative">
        <div
          v-if="classBusy"
          class="absolute inset-0 bg-white/70 rounded-xl flex items-center justify-center z-10"
        >
          <BulldozerLoader label="Updating classes…" />
        </div>
        <div class="staff-panel-header">
          <span class="material-symbols-outlined" aria-hidden="true">event</span>
          <h3>Classes &amp; Orientation</h3>
        </div>

        <CardSkeleton v-if="classesLoading" variant="list" :count="2" />

        <template v-else>
        <div v-if="enrolledClasses.length" class="space-y-1.5 mb-3 staff-fade-in">
          <div
            v-for="ec in enrolledClasses"
            :key="ec.enrollment_id"
            class="flex items-center justify-between gap-2 border-t border-stone-100 pt-1.5 first:border-0 first:pt-0"
          >
            <div class="text-sm">
              <span class="font-medium">{{ ec.template_name }}</span>
              <span class="text-stone-500"> · {{ ec.category_display }}</span>
              <div class="text-xs text-stone-500">
                {{ formatSessionDate(ec.session_date) }} · {{ formatTimeRange(ec.start_time, ec.end_time) }}
                <span v-if="ec.location"> · {{ ec.location }}</span>
              </div>
            </div>
            <button
              type="button"
              class="text-xs font-semibold text-red-600 shrink-0"
              :disabled="classBusy"
              @click="unenrollFromClass(ec)"
            >
              Remove
            </button>
          </div>
        </div>
        <p v-else class="text-sm text-stone-500 mb-3">Not signed up for any upcoming classes.</p>

        <div class="flex gap-2">
          <select v-model="selectedSessionId" class="staff-input flex-1">
            <option value="">Add to an upcoming class…</option>
            <optgroup
              v-for="(sessions, category) in groupedSessions"
              :key="category"
              :label="category"
            >
              <option v-for="s in sessions" :key="s.id" :value="s.id" :disabled="s.spots_remaining <= 0">
                {{ s.template_name }} — {{ formatSessionDate(s.session_date) }}, {{ formatTimeRange(s.start_time, s.end_time) }}
                ({{ s.spots_remaining > 0 ? s.spots_remaining + ' spots left' : 'full' }})
              </option>
            </optgroup>
          </select>
          <button
            type="button"
            class="staff-btn staff-btn-primary shrink-0"
            :disabled="!selectedSessionId || classBusy"
            @click="enrollInClass"
          >
            Add
          </button>
        </div>
        <p v-if="upcomingSessions.length === 0" class="text-xs text-stone-400 mt-1.5">
          No upcoming classes scheduled yet —
          <RouterLink to="/classes" class="text-orange-600 font-semibold">add one</RouterLink>.
        </p>
        </template>
      </div>

      <div class="staff-card p-4 relative">
        <div
          v-if="noteBusy"
          class="absolute inset-0 bg-white/70 rounded-xl flex items-center justify-center z-10"
        >
          <BulldozerLoader label="Saving note…" />
        </div>
        <div class="staff-panel-header">
          <span class="material-symbols-outlined" aria-hidden="true">edit_note</span>
          <h3>Quick case note</h3>
        </div>
        <textarea
          v-model="noteContent"
          rows="4"
          class="staff-input mb-3"
          placeholder="What happened today?"
        />
        <button
          type="button"
          class="staff-btn staff-btn-primary w-full"
          :disabled="noteBusy || !noteContent.trim()"
          @click="saveNote"
        >
          Save note
        </button>
      </div>

      <div class="staff-card p-4">
        <div class="staff-panel-header">
          <span class="material-symbols-outlined" aria-hidden="true">history_edu</span>
          <h3>Recent notes</h3>
        </div>
        <p v-if="notes.length === 0" class="text-sm text-stone-500">No notes yet.</p>
        <article
          v-for="note in notes"
          :key="note.id"
          class="border-t border-stone-100 pt-2 first:border-0 first:pt-0"
        >
          <p class="text-xs text-stone-500">{{ note.note_date }} · {{ note.staff_member }}</p>
          <p class="text-sm whitespace-pre-wrap">{{ note.content }}</p>
        </article>
      </div>
    </template>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { staffFetch } from '../api'
import { friendlyError, networkErrorMessage } from '../utils/errors'
import { useToast } from '../composables/useToast'
import BulldozerLoader from './BulldozerLoader.vue'
import CardSkeleton from './dashboard/CardSkeleton.vue'

const route = useRoute()
const router = useRouter()
const toast = useToast()

interface ClientDetail {
  id: number
  full_name: string
  phone: string
  status: string
  staff_name?: string
}

interface CaseNote {
  id: number
  note_date: string
  content: string
  staff_member: string
}

interface UpcomingSession {
  id: number
  template_name: string
  category: string
  category_display: string
  session_date: string
  start_time: string
  end_time: string
  location: string
  spots_remaining: number
}

interface ClientClassEnrollment {
  enrollment_id: number
  session_id: number
  template_name: string
  category_display: string
  session_date: string
  start_time: string
  end_time: string
  location: string
  status: string
}

const client = ref<ClientDetail | null>(null)
const notes = ref<CaseNote[]>([])
const loading = ref(true)
const error = ref('')
const noteContent = ref('')
const noteBusy = ref(false)

const upcomingSessions = ref<UpcomingSession[]>([])
const enrolledClasses = ref<ClientClassEnrollment[]>([])
const selectedSessionId = ref<number | ''>('')
const classBusy = ref(false)
const classesLoading = ref(true)

const groupedSessions = computed(() => {
  const groups: Record<string, UpcomingSession[]> = {}
  for (const s of upcomingSessions.value) {
    if (!groups[s.category_display]) groups[s.category_display] = []
    groups[s.category_display].push(s)
  }
  return groups
})

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

const clientId = () => Number(route.params.id)

async function loadClasses() {
  classesLoading.value = true
  try {
    const id = clientId()
    const [upcomingResp, clientClassesResp] = await Promise.all([
      staffFetch('/api/staff/classes/upcoming/'),
      staffFetch(`/api/staff/clients/${id}/classes/`),
    ])
    const upcomingBody = upcomingResp.ok ? await upcomingResp.json() : { results: [] }
    upcomingSessions.value = upcomingBody.results || []
    const clientClassesBody = clientClassesResp.ok ? await clientClassesResp.json() : { results: [] }
    enrolledClasses.value = clientClassesBody.results || []
  } catch {
    /* Classes card degrades gracefully if this fails; client info still loads. */
  } finally {
    classesLoading.value = false
  }
}

async function enrollInClass() {
  if (!selectedSessionId.value) return
  classBusy.value = true
  try {
    const resp = await staffFetch(`/api/staff/classes/${selectedSessionId.value}/enroll/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ client_id: clientId() }),
    })
    const body = await resp.json().catch(() => null)
    if (!resp.ok) {
      toast.error(friendlyError(body, 'Could not add client to that class.'))
      return
    }
    toast.success(body?.message || 'Added to class.')
    selectedSessionId.value = ''
    await loadClasses()
  } catch (e) {
    toast.error(networkErrorMessage(e))
  } finally {
    classBusy.value = false
  }
}

async function unenrollFromClass(enrollment: ClientClassEnrollment) {
  classBusy.value = true
  try {
    const resp = await staffFetch(`/api/staff/classes/${enrollment.session_id}/unenroll/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ client_id: clientId() }),
    })
    const body = await resp.json().catch(() => null)
    if (!resp.ok) {
      toast.error(friendlyError(body, 'Could not remove client from that class.'))
      return
    }
    toast.success('Removed from class.')
    await loadClasses()
  } catch (e) {
    toast.error(networkErrorMessage(e))
  } finally {
    classBusy.value = false
  }
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const id = clientId()
    const [clientResp, notesResp] = await Promise.all([
      staffFetch(`/api/staff/clients/${id}/`),
      staffFetch(`/api/staff/clients/${id}/notes/`),
    ])
    if (!clientResp.ok) {
      error.value = 'Client not found.'
      return
    }
    client.value = await clientResp.json()
    notes.value = notesResp.ok ? await notesResp.json() : []
    loadClasses()
  } catch (e) {
    error.value = networkErrorMessage(e)
  } finally {
    loading.value = false
  }
}

async function saveNote() {
  if (!noteContent.value.trim()) return
  noteBusy.value = true
  try {
    const resp = await staffFetch(`/api/staff/clients/${clientId()}/notes/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        note_date: new Date().toISOString().slice(0, 10),
        note_type: 'general',
        content: noteContent.value.trim(),
      }),
    })
    const body = await resp.json().catch(() => null)
    if (!resp.ok) {
      toast.error(friendlyError(body, 'Could not save your note.'))
      return
    }
    noteContent.value = ''
    toast.success('Case note saved.')
    const notesResp = await staffFetch(`/api/staff/clients/${clientId()}/notes/`)
    notes.value = notesResp.ok ? await notesResp.json() : notes.value
  } catch (e) {
    toast.error(networkErrorMessage(e))
  } finally {
    noteBusy.value = false
  }
}

onMounted(load)
watch(() => route.params.id, load)
</script>
