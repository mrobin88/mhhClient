<template>
  <section class="space-y-3">
    <div class="staff-card p-4">
      <div class="staff-panel-header">
        <span class="material-symbols-outlined" aria-hidden="true">event</span>
        <h3>Classes &amp; Trainings</h3>
        <StaffTip text="Create Orientation, Job Readiness Training (JRT), resume workshops, and other classes. Set them to repeat weekly or monthly, then mark who showed up." />
        <button
          type="button"
          class="staff-btn staff-btn-secondary shrink-0"
          @click="toggleCreateForm"
        >
          {{ showCreateForm ? 'Cancel' : '+ New class' }}
        </button>
      </div>
      <p class="text-xs text-stone-500 mb-3">
        Add classes, schedule recurring sessions, and track who attends — all from here.
        You can also enroll someone from their client page.
      </p>

      <form v-if="showCreateForm" class="space-y-3 border border-stone-200 rounded-xl p-3 mb-3" @submit.prevent="submitCreate">
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div class="space-y-1">
            <label class="text-xs font-semibold text-stone-600">Class name</label>
            <input v-model="form.name" type="text" class="staff-input" placeholder="e.g. Resume Workshop" />
          </div>
          <div class="space-y-1">
            <label class="text-xs font-semibold text-stone-600">Category</label>
            <select v-model="form.category" class="staff-input">
              <option v-for="opt in CATEGORY_OPTIONS" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
            </select>
          </div>
        </div>

        <div class="space-y-1">
          <label class="text-xs font-semibold text-stone-600">How often does it happen?</label>
          <select v-model="form.recurrence" class="staff-input">
            <option v-for="opt in RECURRENCE_OPTIONS" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
          </select>
        </div>

        <div v-if="form.recurrence === 'none'" class="space-y-1">
          <label class="text-xs font-semibold text-stone-600">Date</label>
          <input v-model="form.session_date" type="date" class="staff-input" />
        </div>

        <div v-else class="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div class="space-y-1">
            <label class="text-xs font-semibold text-stone-600">Day of the week</label>
            <select v-model.number="form.recurrence_weekday" class="staff-input">
              <option value="" disabled>Choose a day…</option>
              <option v-for="opt in WEEKDAY_OPTIONS" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
            </select>
          </div>
          <div v-if="form.recurrence === 'monthly'" class="space-y-1">
            <label class="text-xs font-semibold text-stone-600">Which week of the month</label>
            <select v-model.number="form.recurrence_week_of_month" class="staff-input">
              <option value="" disabled>Choose a week…</option>
              <option v-for="opt in WEEK_OF_MONTH_OPTIONS" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
            </select>
          </div>
        </div>

        <div class="grid grid-cols-2 gap-3">
          <div class="space-y-1">
            <label class="text-xs font-semibold text-stone-600">Start time</label>
            <input v-model="form.start_time" type="time" class="staff-input" />
          </div>
          <div class="space-y-1">
            <label class="text-xs font-semibold text-stone-600">End time</label>
            <input v-model="form.end_time" type="time" class="staff-input" />
          </div>
        </div>

        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div class="space-y-1">
            <label class="text-xs font-semibold text-stone-600">Location (optional)</label>
            <input v-model="form.location" type="text" class="staff-input" placeholder="Room or address" />
          </div>
          <div class="space-y-1">
            <label class="text-xs font-semibold text-stone-600">Facilitator (optional)</label>
            <input v-model="form.facilitator" type="text" class="staff-input" placeholder="Who's running it" />
          </div>
        </div>

        <div class="space-y-1">
          <label class="text-xs font-semibold text-stone-600">Seats</label>
          <input v-model.number="form.capacity" type="number" min="1" class="staff-input" />
        </div>

        <div class="space-y-1">
          <label class="text-xs font-semibold text-stone-600">Notes (optional)</label>
          <textarea v-model="form.description" rows="2" class="staff-input" placeholder="Anything staff should know" />
        </div>

        <button type="submit" class="staff-btn staff-btn-primary w-full" :disabled="creating">
          {{ creating ? 'Creating…' : 'Create class' }}
        </button>
      </form>

      <CardSkeleton v-if="templatesLoading" variant="list" :count="3" />
      <p v-else-if="templatesError" class="text-sm text-stone-500">{{ templatesError }}</p>
      <p v-else-if="templates.length === 0" class="text-sm text-stone-500">
        No classes yet — use "+ New class" above to add your first one.
      </p>

      <ul v-else class="space-y-2 staff-fade-in">
        <li
          v-for="t in templates"
          :key="t.id"
          class="border-t border-stone-100 pt-2 first:border-0 first:pt-0"
        >
          <div class="flex items-center justify-between gap-2">
            <button type="button" class="min-w-0 flex-1 text-left" @click="toggleTemplate(t.id)">
              <span class="block text-sm font-semibold truncate">{{ t.name }}</span>
              <span class="block text-xs text-stone-500">
                {{ t.category_display }} · {{ t.recurrence_summary }} · {{ t.capacity }} seats ·
                {{ t.upcoming_sessions_count }} upcoming
              </span>
            </button>
            <span class="material-symbols-outlined text-stone-400 shrink-0" aria-hidden="true">
              {{ expandedTemplateId === t.id ? 'expand_less' : 'expand_more' }}
            </span>
          </div>

          <div v-if="expandedTemplateId === t.id" class="mt-2 pl-1 space-y-2">
            <div class="flex flex-wrap gap-2">
              <button
                v-if="t.recurrence !== 'none'"
                type="button"
                class="staff-btn staff-btn-secondary"
                style="padding: 0.5rem 0.75rem; font-size: 0.8rem;"
                :disabled="generatingId === t.id"
                @click="generateSessions(t)"
              >
                {{ generatingId === t.id ? 'Adding…' : 'Add more sessions (+60 days)' }}
              </button>
              <button
                type="button"
                class="staff-btn staff-btn-secondary"
                style="padding: 0.5rem 0.75rem; font-size: 0.8rem;"
                @click="toggleAddDateForm(t.id)"
              >
                + One-off date
              </button>
            </div>

            <div v-if="addDateTemplateId === t.id" class="flex gap-2">
              <input v-model="addDateValue" type="date" class="staff-input flex-1" />
              <button
                type="button"
                class="staff-btn staff-btn-primary shrink-0"
                :disabled="!addDateValue || addingDate"
                @click="submitAddDate(t)"
              >
                Add
              </button>
            </div>

            <CardSkeleton v-if="sessionsLoadingId === t.id" variant="list" :count="2" />
            <p v-else-if="(sessionsByTemplate[t.id] || []).length === 0" class="text-xs text-stone-400">
              No upcoming sessions scheduled.
            </p>

            <div v-else class="space-y-1.5 staff-fade-in">
              <div
                v-for="s in sessionsByTemplate[t.id]"
                :key="s.id"
                class="staff-stat-tile"
              >
                <button type="button" class="w-full flex items-center justify-between gap-2 text-left" @click="toggleSessionRoster(s.id)">
                  <span class="text-sm">
                    {{ formatSessionDate(s.session_date) }} · {{ formatTimeRange(s.start_time, s.end_time) }}
                    <span v-if="s.location" class="text-stone-500"> · {{ s.location }}</span>
                  </span>
                  <span
                    class="text-[10px] uppercase font-bold tracking-wide rounded-full px-2 py-0.5 shrink-0"
                    :class="s.spots_remaining > 0 ? 'bg-emerald-100 text-emerald-700' : 'bg-stone-200 text-stone-600'"
                  >
                    {{ s.enrolled_count }}/{{ s.capacity }}
                  </span>
                </button>

                <div v-if="expandedSessionId === s.id" class="mt-2 space-y-1.5">
                  <p v-if="rosterLoadingId === s.id" class="text-xs text-stone-500">Loading roster…</p>
                  <template v-else>
                    <p v-if="(rosterBySession[s.id] || []).length === 0" class="text-xs text-stone-400">
                      No one signed up yet.
                    </p>
                    <div
                      v-for="r in rosterBySession[s.id]"
                      :key="r.enrollment_id"
                      class="flex items-center justify-between gap-2"
                    >
                      <RouterLink
                        :to="{ name: 'ClientDetail', params: { id: r.client_id } }"
                        class="text-xs font-medium text-stone-700 hover:text-orange-600 truncate"
                      >
                        {{ r.client_full_name }}
                      </RouterLink>
                      <select
                        class="staff-input shrink-0"
                        style="width: auto; padding: 0.35rem 1.75rem 0.35rem 0.6rem; font-size: 0.72rem;"
                        :value="r.status"
                        :disabled="statusUpdatingId === r.enrollment_id"
                        @change="onStatusChange(r, s.id, $event)"
                      >
                        <option v-for="opt in ENROLLMENT_STATUS_OPTIONS" :key="opt.value" :value="opt.value">
                          {{ opt.label }}
                        </option>
                      </select>
                    </div>
                  </template>
                </div>
              </div>
            </div>
          </div>
        </li>
      </ul>
    </div>
  </section>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { staffFetch } from '../api'
import { friendlyError, networkErrorMessage } from '../utils/errors'
import { useToast } from '../composables/useToast'
import CardSkeleton from './dashboard/CardSkeleton.vue'
import StaffTip from './StaffTip.vue'

const toast = useToast()

const CATEGORY_OPTIONS = [
  { value: 'orientation', label: 'Orientation' },
  { value: 'job_readiness', label: 'Job Readiness Training' },
  { value: 'resume_workshop', label: 'Resume & Application Workshop' },
  { value: 'training', label: 'Skills Training' },
  { value: 'other', label: 'Other' },
]
const RECURRENCE_OPTIONS = [
  { value: 'none', label: 'Does not repeat (one-time)' },
  { value: 'weekly', label: 'Weekly' },
  { value: 'monthly', label: 'Monthly' },
]
const WEEKDAY_OPTIONS = [
  { value: 0, label: 'Monday' },
  { value: 1, label: 'Tuesday' },
  { value: 2, label: 'Wednesday' },
  { value: 3, label: 'Thursday' },
  { value: 4, label: 'Friday' },
  { value: 5, label: 'Saturday' },
  { value: 6, label: 'Sunday' },
]
const WEEK_OF_MONTH_OPTIONS = [
  { value: 1, label: '1st' },
  { value: 2, label: '2nd' },
  { value: 3, label: '3rd' },
  { value: 4, label: '4th' },
]
const ENROLLMENT_STATUS_OPTIONS = [
  { value: 'registered', label: 'Registered' },
  { value: 'attended', label: 'Attended' },
  { value: 'no_show', label: 'No Show' },
  { value: 'cancelled', label: 'Removed' },
]

interface ClassTemplate {
  id: number
  name: string
  category: string
  category_display: string
  capacity: number
  recurrence: 'none' | 'weekly' | 'monthly'
  recurrence_summary: string
  upcoming_sessions_count: number
}

interface ClassSessionSummary {
  id: number
  session_date: string
  start_time: string
  end_time: string
  location: string
  capacity: number
  enrolled_count: number
  spots_remaining: number
}

interface RosterEntry {
  enrollment_id: number
  client_id: number
  client_full_name: string
  status: string
}

const templates = ref<ClassTemplate[]>([])
const templatesLoading = ref(true)
const templatesError = ref('')

const showCreateForm = ref(false)
const creating = ref(false)
const form = reactive({
  name: '',
  category: 'training',
  recurrence: 'none' as 'none' | 'weekly' | 'monthly',
  recurrence_weekday: '' as number | '',
  recurrence_week_of_month: '' as number | '',
  session_date: '',
  start_time: '10:00',
  end_time: '11:00',
  location: '',
  facilitator: '',
  capacity: 20,
  description: '',
})

const expandedTemplateId = ref<number | null>(null)
const sessionsByTemplate = reactive<Record<number, ClassSessionSummary[]>>({})
const sessionsLoadingId = ref<number | null>(null)
const generatingId = ref<number | null>(null)

const addDateTemplateId = ref<number | null>(null)
const addDateValue = ref('')
const addingDate = ref(false)

const expandedSessionId = ref<number | null>(null)
const rosterBySession = reactive<Record<number, RosterEntry[]>>({})
const rosterLoadingId = ref<number | null>(null)
const statusUpdatingId = ref<number | null>(null)

function formatSessionDate(dateStr: string) {
  const d = new Date(`${dateStr}T00:00:00`)
  if (Number.isNaN(d.getTime())) return dateStr
  return d.toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric' })
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

async function loadTemplates() {
  templatesLoading.value = true
  templatesError.value = ''
  try {
    const resp = await staffFetch('/api/staff/classes/templates/')
    if (!resp.ok) {
      templatesError.value = 'Could not load classes.'
      return
    }
    const body = await resp.json()
    templates.value = body.results || []
  } catch {
    templatesError.value = 'No connection.'
  } finally {
    templatesLoading.value = false
  }
}

function toggleCreateForm() {
  showCreateForm.value = !showCreateForm.value
}

function resetForm() {
  form.name = ''
  form.category = 'training'
  form.recurrence = 'none'
  form.recurrence_weekday = ''
  form.recurrence_week_of_month = ''
  form.session_date = ''
  form.start_time = '10:00'
  form.end_time = '11:00'
  form.location = ''
  form.facilitator = ''
  form.capacity = 20
  form.description = ''
}

async function submitCreate() {
  if (creating.value) return
  creating.value = true
  try {
    const resp = await staffFetch('/api/staff/classes/templates/create/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(form),
    })
    const body = await resp.json().catch(() => null)
    if (!resp.ok) {
      toast.error(friendlyError(body, 'Could not create that class.'))
      return
    }
    toast.success(body?.message || 'Class created.')
    resetForm()
    showCreateForm.value = false
    await loadTemplates()
  } catch (e) {
    toast.error(networkErrorMessage(e))
  } finally {
    creating.value = false
  }
}

async function loadSessions(templateId: number) {
  sessionsLoadingId.value = templateId
  try {
    const resp = await staffFetch(`/api/staff/classes/templates/${templateId}/sessions/`)
    const body = resp.ok ? await resp.json() : { results: [] }
    sessionsByTemplate[templateId] = body.results || []
  } catch {
    sessionsByTemplate[templateId] = sessionsByTemplate[templateId] || []
  } finally {
    sessionsLoadingId.value = null
  }
}

function toggleTemplate(templateId: number) {
  if (expandedTemplateId.value === templateId) {
    expandedTemplateId.value = null
    return
  }
  expandedTemplateId.value = templateId
  addDateTemplateId.value = null
  if (!sessionsByTemplate[templateId]) loadSessions(templateId)
}

async function generateSessions(t: ClassTemplate) {
  generatingId.value = t.id
  try {
    const resp = await staffFetch(`/api/staff/classes/templates/${t.id}/generate-sessions/`, { method: 'POST' })
    const body = await resp.json().catch(() => null)
    if (!resp.ok) {
      toast.error(friendlyError(body, 'Could not schedule more sessions.'))
      return
    }
    toast.success(body?.message || 'Sessions added.')
    await Promise.all([loadSessions(t.id), loadTemplates()])
  } catch (e) {
    toast.error(networkErrorMessage(e))
  } finally {
    generatingId.value = null
  }
}

function toggleAddDateForm(templateId: number) {
  addDateTemplateId.value = addDateTemplateId.value === templateId ? null : templateId
  addDateValue.value = ''
}

async function submitAddDate(t: ClassTemplate) {
  if (!addDateValue.value || addingDate.value) return
  addingDate.value = true
  try {
    const resp = await staffFetch('/api/staff/classes/sessions/create/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ template_id: t.id, session_date: addDateValue.value }),
    })
    const body = await resp.json().catch(() => null)
    if (!resp.ok) {
      toast.error(friendlyError(body, 'Could not add that date.'))
      return
    }
    toast.success(body?.message || 'Date added.')
    addDateTemplateId.value = null
    addDateValue.value = ''
    await Promise.all([loadSessions(t.id), loadTemplates()])
  } catch (e) {
    toast.error(networkErrorMessage(e))
  } finally {
    addingDate.value = false
  }
}

async function toggleSessionRoster(sessionId: number) {
  if (expandedSessionId.value === sessionId) {
    expandedSessionId.value = null
    return
  }
  expandedSessionId.value = sessionId
  if (rosterBySession[sessionId]) return
  rosterLoadingId.value = sessionId
  try {
    const resp = await staffFetch(`/api/staff/classes/${sessionId}/roster/`)
    const body = resp.ok ? await resp.json() : { roster: [] }
    rosterBySession[sessionId] = body.roster || []
  } catch {
    rosterBySession[sessionId] = rosterBySession[sessionId] || []
  } finally {
    rosterLoadingId.value = null
  }
}

async function onStatusChange(entry: RosterEntry, sessionId: number, event: Event) {
  const newStatus = (event.target as HTMLSelectElement).value
  const previous = entry.status
  statusUpdatingId.value = entry.enrollment_id
  try {
    const resp = await staffFetch(`/api/staff/classes/enrollments/${entry.enrollment_id}/status/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status: newStatus }),
    })
    const body = await resp.json().catch(() => null)
    if (!resp.ok) {
      toast.error(friendlyError(body, 'Could not update that.'))
      return
    }
    entry.status = newStatus
    if (newStatus === 'cancelled') {
      rosterBySession[sessionId] = (rosterBySession[sessionId] || []).filter(
        (r) => r.enrollment_id !== entry.enrollment_id,
      )
    }
    await loadSessions(templateIdForSession(sessionId))
  } catch (e) {
    entry.status = previous
    toast.error(networkErrorMessage(e))
  } finally {
    statusUpdatingId.value = null
  }
}

function templateIdForSession(sessionId: number): number {
  for (const [templateId, sessions] of Object.entries(sessionsByTemplate)) {
    if (sessions.some((s) => s.id === sessionId)) return Number(templateId)
  }
  return expandedTemplateId.value || 0
}

onMounted(loadTemplates)
</script>
