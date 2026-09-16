<template>
  <section class="space-y-3">
    <div class="staff-card p-4">
      <div class="staff-panel-header">
        <span class="material-symbols-outlined" aria-hidden="true">event</span>
        <h3>Classes &amp; Trainings</h3>
        <StaffTip text="Boxes on the calendar are class dates. Click one for the name list. Print the roster for notes during class. Set Program so a Guard Card class lands in Guard Card, not General." />
        <button
          type="button"
          class="staff-btn staff-btn-secondary shrink-0"
          @click="toggleCreateForm"
        >
          {{ showCreateForm || editingTemplateId ? 'Cancel' : '+ New class' }}
        </button>
      </div>
      <p class="text-xs text-stone-500 mb-3">
        Use the calendar to see when classes are set. Click a box for the sign-up list,
        mark who is here, and print a roster with space for notes. New classes and
        recurring dates are set up in the program columns below.
      </p>

      <ClassMonthCalendar
        ref="calendarRef"
        :selected-id="selectedSession?.id"
        @select="onCalendarSelect"
      />

      <div v-if="selectedSession" id="class-roster-panel" class="staff-cal-roster">
        <div class="staff-cal-roster-head">
          <div>
            <h4>{{ selectedSession.template_name }}</h4>
            <p>
              {{ formatSessionDate(selectedSession.session_date) }}
              · {{ formatTimeRange(selectedSession.start_time, selectedSession.end_time) }}
              <span v-if="selectedSession.location"> · {{ selectedSession.location }}</span>
              <span v-if="selectedSession.facilitator"> · {{ selectedSession.facilitator }}</span>
              · {{ selectedSession.enrolled_count }}/{{ selectedSession.capacity }} signed up
            </p>
          </div>
          <button type="button" class="staff-btn staff-btn-ghost staff-btn-sm" @click="selectedSession = null">
            Close
          </button>
        </div>
        <ClassRosterPanel
          :session-id="selectedSession.id"
          :session-name="selectedSession.template_name"
          :session-date="selectedSession.session_date"
          :session-status="selectedSession.status"
          :facilitator="selectedSession.facilitator"
          :location="selectedSession.location"
          :start-time="selectedSession.start_time"
          :end-time="selectedSession.end_time"
          :program-label="selectedSession.program_display"
          @changed="onSelectedRosterChanged"
          @cancelled="onSelectedCancelled"
          @deleted="onSelectedDeleted"
        />
      </div>
      <p v-else class="staff-cal-hint">Click a class on the calendar to open the name list.</p>

      <form v-if="showCreateForm || editingTemplateId" class="space-y-3 border border-stone-200 rounded-xl p-3 mb-3" @submit.prevent="submitTemplate">
        <p class="text-sm font-semibold text-stone-700">
          {{ editingTemplateId ? 'Edit class or JRT' : 'Create a class or JRT' }}
        </p>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div class="space-y-1">
            <label class="text-xs font-semibold text-stone-600">Class name</label>
            <input v-model="form.name" type="text" class="staff-input" placeholder="e.g. Resume Workshop" />
          </div>
          <div class="space-y-1">
            <label class="text-xs font-semibold text-stone-600">Program</label>
            <select v-model="form.program" class="staff-input">
              <option v-for="opt in PROGRAM_COLUMNS" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
            </select>
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

        <label v-if="editingTemplateId" class="flex items-center gap-2 text-sm text-stone-700">
          <input v-model="form.is_active" type="checkbox" />
          Active and available for new sessions
        </label>

        <div class="space-y-1">
          <label class="text-xs font-semibold text-stone-600">Notes (optional)</label>
          <textarea v-model="form.description" rows="2" class="staff-input" placeholder="Anything staff should know"></textarea>
        </div>

        <button type="submit" class="staff-btn staff-btn-primary w-full" :disabled="creating">
          {{ creating ? 'Saving…' : editingTemplateId ? 'Save class' : 'Create class' }}
        </button>
      </form>

      <h4 class="staff-cal-setup-title">Set up classes</h4>
      <p class="text-xs text-stone-500 mb-3">
        Classes sit in a column for their program (City Build, Pit Stop, CAPSA, Guard Card, General).
        Use the program menu to move a class. Click a date to open the name list above.
      </p>
      <CardSkeleton v-if="templatesLoading" variant="list" :count="3" />
      <p v-else-if="templatesError" class="text-sm text-stone-500">{{ templatesError }}</p>

      <div v-else class="staff-program-grid staff-fade-in">
        <section
          v-for="group in programGroups"
          :key="group.value"
          class="staff-program-col"
        >
          <div class="staff-program-col-header">
            <h4>{{ group.label }}</h4>
            <span>{{ group.templates.length }}</span>
          </div>
          <p v-if="group.templates.length === 0" class="staff-program-empty">
            No classes in this program yet.
          </p>
          <ul v-else class="space-y-2">
            <li
              v-for="t in group.templates"
              :key="t.id"
              class="border-t border-stone-200/80 pt-2 first:border-0 first:pt-0"
            >
          <div class="flex items-start justify-between gap-2">
            <button type="button" class="min-w-0 flex-1 text-left" @click="toggleTemplate(t.id)">
              <span class="block text-sm font-semibold truncate">{{ t.name }}</span>
              <span class="block text-xs text-stone-500">
                {{ t.category_display }} · {{ t.recurrence_summary }} · {{ t.capacity }} seats ·
                {{ t.upcoming_sessions_count }} upcoming
              </span>
            </button>
            <span class="material-symbols-outlined text-stone-400 shrink-0 mt-0.5" aria-hidden="true">
              {{ expandedTemplateId === t.id ? 'expand_less' : 'expand_more' }}
            </span>
          </div>

          <div v-if="expandedTemplateId === t.id" class="mt-2 pl-1 space-y-2">
            <div class="flex flex-wrap gap-2">
              <select
                class="staff-input staff-program-pick"
                :value="t.program"
                :disabled="movingProgramId === t.id"
                aria-label="Move to program"
                @change="setTemplateProgram(t, $event)"
              >
                <option v-for="opt in PROGRAM_COLUMNS" :key="opt.value" :value="opt.value">
                  {{ opt.label }}
                </option>
              </select>
              <button
                type="button"
                class="staff-btn staff-btn-secondary staff-btn-sm"
                @click="startEditTemplate(t)"
              >
                Edit class
              </button>
              <button
                v-if="t.recurrence !== 'none'"
                type="button"
                class="staff-btn staff-btn-secondary staff-btn-sm"
                :disabled="generatingId === t.id"
                @click="generateSessions(t)"
              >
                {{ generatingId === t.id ? 'Adding…' : 'Add more sessions (+60 days)' }}
              </button>
              <button
                type="button"
                class="staff-btn staff-btn-secondary staff-btn-sm"
                @click="toggleAddDateForm(t.id)"
              >
                + One-off date
              </button>
              <button
                type="button"
                class="staff-btn staff-btn-danger staff-btn-sm"
                :disabled="deletingTemplateId === t.id"
                @click="askDeleteTemplate(t.id)"
              >
                Delete class
              </button>
            </div>

            <div v-if="pendingDeleteTemplateId === t.id" class="staff-roster-confirm is-delete">
              <p>
                Delete this class and every date? People on upcoming dates get a text that the
                class is cancelled.
              </p>
              <div class="staff-roster-confirm-actions">
                <button type="button" class="staff-btn staff-btn-secondary staff-btn-sm" @click="pendingDeleteTemplateId = null">
                  Keep the class
                </button>
                <button
                  type="button"
                  class="staff-btn staff-btn-danger-solid staff-btn-sm"
                  :disabled="deletingTemplateId === t.id"
                  @click="deleteTemplate(t)"
                >
                  Yes, delete it
                </button>
              </div>
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
                <div class="flex items-center gap-2">
                  <button type="button" class="min-w-0 flex-1 flex items-center justify-between gap-2 text-left" @click="selectFromList(t, s)">
                    <span class="text-sm">
                      {{ formatSessionDate(s.session_date) }} · {{ formatTimeRange(s.start_time, s.end_time) }}
                      <span v-if="s.location" class="text-stone-500"> · {{ s.location }}</span>
                    </span>
                    <span
                      class="text-[10px] uppercase font-bold tracking-wide rounded-full px-2 py-0.5 shrink-0"
                      :class="s.status === 'cancelled' ? 'bg-red-100 text-red-700' : s.spots_remaining > 0 ? 'bg-emerald-100 text-emerald-700' : 'bg-stone-200 text-stone-600'"
                    >
                      {{ s.status === 'cancelled' ? 'Cancelled' : `${s.enrolled_count}/${s.capacity}` }}
                    </span>
                  </button>
                  <button type="button" class="text-xs font-semibold staff-link" @click="startEditSession(s)">Edit</button>
                </div>

                <form
                  v-if="editingSessionId === s.id"
                  class="mt-2 grid grid-cols-1 sm:grid-cols-2 gap-2"
                  @submit.prevent="submitSessionEdit(t.id)"
                >
                  <input v-model="sessionForm.session_date" type="date" class="staff-input" aria-label="Session date" />
                  <select v-model="sessionForm.status" class="staff-input" aria-label="Session status">
                    <option value="scheduled">Scheduled</option>
                    <option value="completed">Completed</option>
                    <option value="cancelled">Cancelled</option>
                  </select>
                  <input v-model="sessionForm.start_time" type="time" class="staff-input" aria-label="Start time" />
                  <input v-model="sessionForm.end_time" type="time" class="staff-input" aria-label="End time" />
                  <input v-model="sessionForm.location" class="staff-input" placeholder="Location" />
                  <input v-model="sessionForm.facilitator" class="staff-input" placeholder="Facilitator" />
                  <input v-model.number="sessionForm.capacity" type="number" min="1" class="staff-input" placeholder="Capacity" />
                  <div class="flex gap-2">
                    <button type="submit" class="staff-btn staff-btn-primary flex-1" :disabled="savingSession">Save</button>
                    <button type="button" class="staff-btn staff-btn-secondary" @click="editingSessionId = null">Cancel</button>
                  </div>
                </form>

              </div>
            </div>
          </div>
            </li>
          </ul>
        </section>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, reactive, ref } from 'vue'
import { staffFetch } from '../api'
import { friendlyError, networkErrorMessage } from '../utils/errors'
import { useToast } from '../composables/useToast'
import CardSkeleton from './dashboard/CardSkeleton.vue'
import ClassMonthCalendar, { type CalendarSession } from './ClassMonthCalendar.vue'
import ClassRosterPanel from './ClassRosterPanel.vue'
import StaffTip from './StaffTip.vue'

const toast = useToast()

const PROGRAM_COLUMNS = [
  { value: 'citybuild', label: 'City Build' },
  { value: 'pit_stop', label: 'Pit Stop' },
  { value: 'capsa', label: 'CAPSA' },
  { value: 'guard_card', label: 'Guard Card' },
  { value: 'general', label: 'General' },
]
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

interface ClassTemplate {
  id: number
  name: string
  program: string
  program_display: string
  category: string
  category_display: string
  description: string
  location: string
  facilitator: string
  capacity: number
  start_time: string
  end_time: string
  recurrence: 'none' | 'weekly' | 'monthly'
  recurrence_weekday: number | null
  recurrence_week_of_month: number | null
  recurrence_summary: string
  is_active: boolean
  upcoming_sessions_count: number
}

interface ClassSessionSummary {
  id: number
  session_date: string
  start_time: string
  end_time: string
  location: string
  facilitator: string
  capacity: number
  enrolled_count: number
  confirmed_count: number
  spots_remaining: number
  status: 'scheduled' | 'completed' | 'cancelled'
}

const templates = ref<ClassTemplate[]>([])
const templatesLoading = ref(true)
const templatesError = ref('')
const movingProgramId = ref<number | null>(null)

const knownPrograms = new Set(PROGRAM_COLUMNS.map((col) => col.value))
const programGroups = computed(() => {
  const groups = PROGRAM_COLUMNS.map((col) => ({
    ...col,
    templates: templates.value.filter((t) => t.program === col.value),
  }))
  const leftover = templates.value.filter((t) => !knownPrograms.has(t.program))
  if (leftover.length) {
    groups.push({
      value: 'other',
      label: leftover[0].program_display || 'Other',
      templates: leftover,
    })
  }
  return groups
})

const showCreateForm = ref(false)
const editingTemplateId = ref<number | null>(null)
const creating = ref(false)
const form = reactive({
  name: '',
  program: 'general',
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
  is_active: true,
})

const expandedTemplateId = ref<number | null>(null)
const sessionsByTemplate = reactive<Record<number, ClassSessionSummary[]>>({})
const sessionsLoadingId = ref<number | null>(null)
const generatingId = ref<number | null>(null)

const addDateTemplateId = ref<number | null>(null)
const addDateValue = ref('')
const addingDate = ref(false)

const calendarRef = ref<{ reload: () => Promise<void> } | null>(null)
const selectedSession = ref<CalendarSession | null>(null)
const editingSessionId = ref<number | null>(null)
const savingSession = ref(false)
const pendingDeleteTemplateId = ref<number | null>(null)
const deletingTemplateId = ref<number | null>(null)
const sessionForm = reactive({
  session_date: '',
  start_time: '',
  end_time: '',
  location: '',
  facilitator: '',
  capacity: 20,
  status: 'scheduled' as 'scheduled' | 'completed' | 'cancelled',
})

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

async function setTemplateProgram(t: ClassTemplate, event: Event) {
  const program = (event.target as HTMLSelectElement).value
  if (!program || program === t.program) return
  movingProgramId.value = t.id
  try {
    const resp = await staffFetch(`/api/staff/classes/templates/${t.id}/`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ program }),
    })
    const body = await resp.json().catch(() => null)
    if (!resp.ok) {
      toast.error(friendlyError(body, 'Could not move that class.'))
      ;(event.target as HTMLSelectElement).value = t.program
      return
    }
    toast.success(`Moved to ${PROGRAM_COLUMNS.find((col) => col.value === program)?.label || program}.`)
    await loadTemplates()
  } catch (e) {
    ;(event.target as HTMLSelectElement).value = t.program
    toast.error(networkErrorMessage(e))
  } finally {
    movingProgramId.value = null
  }
}

function toggleCreateForm() {
  if (showCreateForm.value || editingTemplateId.value) {
    showCreateForm.value = false
    editingTemplateId.value = null
    resetForm()
    return
  }
  showCreateForm.value = true
}

function resetForm() {
  form.name = ''
  form.program = 'general'
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
  form.is_active = true
}

function startEditTemplate(template: ClassTemplate) {
  editingTemplateId.value = template.id
  showCreateForm.value = false
  form.name = template.name
  form.program = template.program
  form.category = template.category
  form.recurrence = template.recurrence
  form.recurrence_weekday = template.recurrence_weekday ?? ''
  form.recurrence_week_of_month = template.recurrence_week_of_month ?? ''
  form.session_date = ''
  form.start_time = template.start_time
  form.end_time = template.end_time
  form.location = template.location
  form.facilitator = template.facilitator
  form.capacity = template.capacity
  form.description = template.description
  form.is_active = template.is_active
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

async function submitTemplate() {
  if (creating.value) return
  creating.value = true
  try {
    const editing = editingTemplateId.value
    const endpoint = editing
      ? `/api/staff/classes/templates/${editing}/`
      : '/api/staff/classes/templates/create/'
    const resp = await staffFetch(endpoint, {
      method: editing ? 'PATCH' : 'POST',
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
    editingTemplateId.value = null
    await loadTemplates()
    calendarRef.value?.reload()
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
    calendarRef.value?.reload()
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
    calendarRef.value?.reload()
  } catch (e) {
    toast.error(networkErrorMessage(e))
  } finally {
    addingDate.value = false
  }
}

function onCalendarSelect(session: CalendarSession) {
  selectedSession.value = session
  nextTick(() => {
    document.getElementById('class-roster-panel')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  })
}

function selectFromList(t: ClassTemplate, s: ClassSessionSummary) {
  onCalendarSelect({
    id: s.id,
    template_id: t.id,
    template_name: t.name,
    program: t.program,
    program_display: t.program_display,
    session_date: s.session_date,
    start_time: s.start_time,
    end_time: s.end_time,
    location: s.location,
    facilitator: s.facilitator,
    capacity: s.capacity,
    enrolled_count: s.enrolled_count,
    spots_remaining: s.spots_remaining,
    status: s.status,
  })
}

function onRosterChanged(templateId: number) {
  loadSessions(templateId)
  loadTemplates()
  calendarRef.value?.reload()
}

function onSelectedRosterChanged() {
  if (selectedSession.value?.template_id) onRosterChanged(selectedSession.value.template_id)
  else {
    loadTemplates()
    calendarRef.value?.reload()
  }
}

function onSelectedCancelled() {
  if (selectedSession.value) selectedSession.value = { ...selectedSession.value, status: 'cancelled' }
  onSelectedRosterChanged()
}

function onSelectedDeleted() {
  const templateId = selectedSession.value?.template_id
  const sessionId = selectedSession.value?.id
  selectedSession.value = null
  if (templateId && sessionId) {
    sessionsByTemplate[templateId] = (sessionsByTemplate[templateId] || []).filter((s) => s.id !== sessionId)
  }
  loadTemplates()
  calendarRef.value?.reload()
}

function askDeleteTemplate(templateId: number) {
  pendingDeleteTemplateId.value = pendingDeleteTemplateId.value === templateId ? null : templateId
}

async function deleteTemplate(t: ClassTemplate) {
  deletingTemplateId.value = t.id
  try {
    const resp = await staffFetch(`/api/staff/classes/templates/${t.id}/`, { method: 'DELETE' })
    const body = await resp.json().catch(() => null)
    if (!resp.ok) {
      toast.error(friendlyError(body, 'Could not delete that class.'))
      return
    }
    toast.success(body?.message || 'Class deleted.')
    pendingDeleteTemplateId.value = null
    if (expandedTemplateId.value === t.id) expandedTemplateId.value = null
    if (selectedSession.value?.template_id === t.id) selectedSession.value = null
    await loadTemplates()
    calendarRef.value?.reload()
  } catch (e) {
    toast.error(networkErrorMessage(e))
  } finally {
    deletingTemplateId.value = null
  }
}

function startEditSession(session: ClassSessionSummary) {
  editingSessionId.value = session.id
  sessionForm.session_date = session.session_date
  sessionForm.start_time = session.start_time.slice(0, 5)
  sessionForm.end_time = session.end_time.slice(0, 5)
  sessionForm.location = session.location
  sessionForm.facilitator = session.facilitator
  sessionForm.capacity = session.capacity
  sessionForm.status = session.status
}

async function submitSessionEdit(templateId: number) {
  if (!editingSessionId.value || savingSession.value) return
  savingSession.value = true
  try {
    const resp = await staffFetch(`/api/staff/classes/sessions/${editingSessionId.value}/`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(sessionForm),
    })
    const body = await resp.json().catch(() => null)
    if (!resp.ok) {
      toast.error(friendlyError(body, 'Could not update that session.'))
      return
    }
    toast.success(body?.message || 'Session updated.')
    editingSessionId.value = null
    await Promise.all([loadSessions(templateId), loadTemplates()])
    calendarRef.value?.reload()
  } catch (e) {
    toast.error(networkErrorMessage(e))
  } finally {
    savingSession.value = false
  }
}

onMounted(loadTemplates)
</script>
