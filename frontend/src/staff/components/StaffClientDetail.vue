<template>
  <section :class="['space-y-3', formDirty ? 'staff-client-page-dirty' : '']">
    <button type="button" class="text-sm font-semibold staff-link" @click="goBack">
      ← Back
    </button>

    <BulldozerLoader v-if="loading" label="Loading client…" />
    <div v-else-if="error" class="staff-card p-4 text-center space-y-3">
      <p class="text-sm">{{ error }}</p>
      <button type="button" class="staff-btn staff-btn-secondary" @click="load">Retry</button>
    </div>

    <template v-else-if="client">
      <header id="client-info" class="staff-card p-4 staff-client-hero">
        <div class="flex items-start justify-between gap-3">
          <div class="min-w-0">
            <h1 class="text-xl font-bold leading-tight">{{ displayName }}</h1>
            <p class="mt-1">
              <a v-if="phoneHref" :href="phoneHref" class="staff-activity-link">{{ form.phone }}</a>
              <span v-else class="text-stone-500 text-sm">No phone</span>
              <span v-if="form.email" class="text-stone-500"> · </span>
              <a v-if="form.email" :href="`mailto:${form.email}`" class="staff-activity-link">{{ form.email }}</a>
            </p>
          </div>
          <span class="staff-client-row-status shrink-0">{{ form.status }}</span>
        </div>

        <div class="staff-client-hero-chips">
          <span>{{ programLabel }}</span>
          <span v-if="stageLabel">{{ stageLabel }}</span>
          <span>Staff: {{ client.staff_name || 'Unassigned' }}</span>
        </div>

        <div class="staff-client-actions">
          <a v-if="phoneHref" :href="phoneHref" class="staff-btn staff-btn-secondary">
            <span class="material-symbols-outlined" aria-hidden="true">call</span>
            Call
          </a>
          <RouterLink
            :to="{ name: 'Messages', query: { client: String(client.id) } }"
            class="staff-btn staff-btn-secondary"
          >
            <span class="material-symbols-outlined" aria-hidden="true">chat</span>
            Message
          </RouterLink>
          <button type="button" class="staff-btn staff-btn-secondary" @click="jumpTo('client-classes')">
            <span class="material-symbols-outlined" aria-hidden="true">event</span>
            Class
          </button>
          <button type="button" class="staff-btn staff-btn-secondary" @click="jumpTo('client-notes')">
            <span class="material-symbols-outlined" aria-hidden="true">edit_note</span>
            Note
          </button>
        </div>
      </header>

      <nav class="staff-client-jump" aria-label="On this page">
        <button type="button" :class="{ 'is-active': hopActive === 'classes' }" @click="jumpTo('client-classes')">
          Classes
        </button>
        <button type="button" :class="{ 'is-active': hopActive === 'notes' }" @click="jumpTo('client-notes')">
          Notes
        </button>
        <button
          v-if="form.training_interest === 'pit_stop'"
          type="button"
          @click="jumpTo('client-pitstop')"
        >
          Pit Stop
        </button>
        <button
          v-if="form.training_interest === 'citybuild'"
          type="button"
          @click="jumpTo('client-citybuild')"
        >
          City Build
        </button>
        <button type="button" :class="{ 'is-active': editingDetails }" @click="toggleDetails">
          Details
        </button>
        <RouterLink :to="{ name: 'CreateSkill', query: { client: String(client.id) } }">
          Skill note
        </RouterLink>
      </nav>

      <div id="client-classes" class="staff-card p-4">
        <div class="staff-panel-header">
          <span class="material-symbols-outlined" aria-hidden="true">event</span>
          <h3>Classes</h3>
          <StaffTip text="Add them to Orientation, JRT, or another class. They get an informational text with the date and time." />
        </div>
        <ClientQuickEnroll :client-id="client.id" allow-remove />
      </div>

      <div id="client-notes" class="staff-card p-4 relative">
        <div
          v-if="noteBusy"
          class="absolute inset-0 bg-white/70 rounded-xl flex items-center justify-center z-10"
        >
          <BulldozerLoader label="Saving note…" />
        </div>
        <div class="staff-panel-header">
          <span class="material-symbols-outlined" aria-hidden="true">edit_note</span>
          <h3>Notes</h3>
          <StaffTip text="Write what happened when they came in. Newest notes are at the top." />
        </div>
        <textarea
          v-model="noteContent"
          rows="3"
          class="staff-input mb-3"
          placeholder="What happened today?"
        />
        <button
          type="button"
          class="staff-btn staff-btn-primary w-full mb-4"
          :disabled="noteBusy || !noteContent.trim()"
          @click="saveNote"
        >
          Save note
        </button>
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

      <div v-if="form.training_interest === 'pit_stop'" id="client-pitstop" class="staff-card p-4 relative">
        <div
          v-if="promoteBusy"
          class="absolute inset-0 bg-white/70 rounded-xl flex items-center justify-center z-10"
        >
          <BulldozerLoader label="Setting up portal access…" />
        </div>
        <div class="staff-panel-header">
          <span class="material-symbols-outlined" aria-hidden="true">badge</span>
          <h3>Pit Stop</h3>
          <StaffTip text="Applicant means they signed up but have not been accepted yet. Worker means they can clock in." />
        </div>

        <div class="staff-field mb-3">
          <label for="cd-stage">Stage</label>
          <select id="cd-stage" v-model="form.pit_stop_stage" class="staff-input">
            <option v-for="opt in PIT_STOP_STAGE_OPTIONS" :key="opt.value" :value="opt.value">
              {{ opt.label }}
            </option>
          </select>
        </div>

        <div
          v-if="pitStopApplication"
          class="rounded-lg border border-stone-200 bg-stone-50 p-3 mb-3 space-y-1"
        >
          <div class="flex items-center justify-between gap-2">
            <p class="text-sm font-semibold text-stone-800">Application</p>
            <span class="text-xs font-bold staff-link">
              {{ pitStopApplication.review_status_display }}
            </span>
          </div>
          <p class="text-sm text-stone-600">
            Age {{ pitStopApplication.age ?? 'unknown' }} · area code
            {{ pitStopApplication.area_code || 'unknown' }}
          </p>
          <p class="text-sm text-stone-600">
            Resume: {{ pitStopApplication.has_resume ? 'on file' : 'missing' }} ·
            {{ pitStopApplication.position_applied_for }}
          </p>
          <p class="text-sm text-stone-600">
            Available days:
            {{ pitStopApplication.available_days.length ? pitStopApplication.available_days.join(', ') : 'none selected' }}
          </p>
          <p v-if="pitStopApplication.review_notes" class="text-sm text-stone-700 pt-1">
            Review notes: {{ pitStopApplication.review_notes }}
          </p>
          <RouterLink
            :to="{ name: 'PitStopApplicationDetail', params: { id: pitStopApplication.id } }"
            class="inline-block text-xs font-semibold staff-link pt-1"
          >
            Open full application →
          </RouterLink>
        </div>

        <div v-if="workerPortal" class="rounded-lg border border-stone-200 bg-stone-50 p-3 space-y-1">
          <p class="text-sm font-semibold text-stone-800">
            Worker portal: {{ workerPortal.portal_access ? 'On' : 'Turned off' }}
          </p>
          <p class="text-sm text-stone-600">Login phone: {{ workerPortal.login_phone }}</p>
          <p class="text-sm text-stone-600">Roster status: {{ workerPortal.worker_status_display }}</p>
          <p class="text-sm text-stone-600">
            Last clock in: {{ workerPortal.last_clock_in ? formatDateTime(workerPortal.last_clock_in) : 'Never' }}
          </p>
          <p class="text-xs text-stone-500 pt-1">
            To turn portal access off or reset a PIN, use Django admin → Worker Accounts.
          </p>
        </div>

        <div v-else class="space-y-2">
          <p class="text-sm text-stone-600">
            No worker portal yet. Giving access creates a login so they can clock in. PIN is the last 4 digits of their phone.
          </p>
          <button
            type="button"
            class="staff-btn staff-btn-primary w-full"
            :disabled="promoteBusy"
            @click="promoteToWorker"
          >
            Give worker portal access
          </button>
        </div>
      </div>

      <div v-if="form.training_interest === 'citybuild'" id="client-citybuild" class="staff-card p-4">
        <div class="staff-panel-header">
          <span class="material-symbols-outlined" aria-hidden="true">apartment</span>
          <h3>City Build</h3>
          <StaffTip text="Pre-registration is everything before the CBA 12-week program. Enrolled and Arrived mean they are in the 12-week program." />
        </div>

        <div class="staff-field mb-3">
          <label for="cd-citybuild-stage">Stage</label>
          <select id="cd-citybuild-stage" v-model="form.citybuild_stage" class="staff-input">
            <optgroup
              v-for="group in CITYBUILD_STAGE_GROUPS"
              :key="group.label"
              :label="group.label"
            >
              <option v-for="opt in group.options" :key="opt.value" :value="opt.value">
                {{ opt.label }}
              </option>
            </optgroup>
          </select>
        </div>

        <p
          v-if="form.citybuild_stage === 'in_the_running'"
          class="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-stone-700"
        >
          In the running means it is time for file submission.
          <template v-if="citybuildPacket">
            Packet: {{ citybuildPacket.on_file }} of {{ citybuildPacket.total }} items on file
            <template v-if="citybuildPacket.missing_count">
              ({{ citybuildPacket.missing_count }} still needed).
            </template>
          </template>
          Use the document upload link below so they can send files.
        </p>
        <p v-else-if="form.citybuild_stage === 'drug_test'" class="text-sm text-stone-600">
          They are at the drug-test step. Do not record a positive or negative result here.
        </p>
        <p
          v-else-if="form.citybuild_stage === 'enrolled' || form.citybuild_stage === 'arrived'"
          class="text-sm text-stone-600"
        >
          This person is in the CBA 12-week program.
        </p>
      </div>

      <ClientUploadInvites :client-id="client.id" />

      <div id="client-details" class="staff-card p-4 relative">
        <div
          v-if="saveBusy"
          class="absolute inset-0 bg-white/70 rounded-xl flex items-center justify-center z-10"
        >
          <BulldozerLoader label="Saving…" />
        </div>
        <div class="staff-panel-header">
          <span class="material-symbols-outlined" aria-hidden="true">badge</span>
          <h3>Contact &amp; program</h3>
          <StaffTip text="Fix name, phone, program, or status. Tap Save when the bar appears at the bottom." />
          <button type="button" class="staff-link text-xs font-semibold shrink-0" @click="editingDetails = !editingDetails">
            {{ editingDetails ? 'Hide' : 'Edit' }}
          </button>
        </div>

        <template v-if="editingDetails">
          <div class="staff-field-grid staff-field-grid-2 mb-3">
            <div class="staff-field">
              <label for="cd-first">First name</label>
              <input id="cd-first" v-model="form.first_name" type="text" class="staff-input" autocomplete="given-name" />
            </div>
            <div class="staff-field">
              <label for="cd-last">Last name</label>
              <input id="cd-last" v-model="form.last_name" type="text" class="staff-input" autocomplete="family-name" />
            </div>
            <div class="staff-field">
              <label for="cd-phone">Phone</label>
              <input id="cd-phone" v-model="form.phone" type="tel" class="staff-input" autocomplete="tel" />
            </div>
            <div class="staff-field">
              <label for="cd-email">Email</label>
              <input id="cd-email" v-model="form.email" type="email" class="staff-input" autocomplete="email" />
            </div>
            <div class="staff-field">
              <label for="cd-status">Status</label>
              <select id="cd-status" v-model="form.status" class="staff-input">
                <option v-for="opt in STATUS_OPTIONS" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
              </select>
            </div>
            <div class="staff-field">
              <label for="cd-program">Program</label>
              <select id="cd-program" v-model="form.training_interest" class="staff-input">
                <option v-for="opt in PROGRAM_OPTIONS" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
              </select>
            </div>
            <div class="staff-field">
              <label for="cd-employment">Employment status</label>
              <select id="cd-employment" v-model="form.employment_status" class="staff-input">
                <option v-for="opt in EMPLOYMENT_OPTIONS" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
              </select>
            </div>
            <div class="staff-field">
              <label for="cd-language">Preferred language</label>
              <select id="cd-language" v-model="form.language" class="staff-input">
                <option v-for="opt in LANGUAGE_OPTIONS" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
              </select>
            </div>
            <div class="staff-field">
              <label for="cd-start">Program start date</label>
              <input id="cd-start" v-model="form.program_start_date" type="date" class="staff-input" />
            </div>
            <div class="staff-field">
              <label for="cd-done">Program completed date</label>
              <input id="cd-done" v-model="form.program_completed_date" type="date" class="staff-input" />
            </div>
          </div>

          <details class="mb-1">
            <summary class="text-sm font-semibold text-stone-600 cursor-pointer select-none">
              Address (optional)
            </summary>
            <div class="staff-field-grid staff-field-grid-2 mt-2">
              <div class="staff-field" style="grid-column: 1 / -1;">
                <label for="cd-address">Street</label>
                <input id="cd-address" v-model="form.address" type="text" class="staff-input" />
              </div>
              <div class="staff-field">
                <label for="cd-city">City</label>
                <input id="cd-city" v-model="form.city" type="text" class="staff-input" />
              </div>
              <div class="staff-field">
                <label for="cd-state">State</label>
                <input id="cd-state" v-model="form.state" type="text" class="staff-input" />
              </div>
              <div class="staff-field">
                <label for="cd-zip">ZIP</label>
                <input id="cd-zip" v-model="form.zip_code" type="text" class="staff-input" />
              </div>
            </div>
          </details>
        </template>
        <p v-else class="text-sm text-stone-500">
          Name, phone, program, and address stay here so the top of the page stays clear.
        </p>
      </div>

      <div v-if="formDirty" class="staff-save-bar">
        <p class="text-sm font-semibold">Unsaved changes</p>
        <button
          type="button"
          class="staff-btn staff-btn-primary"
          :disabled="saveBusy"
          @click="saveClient"
        >
          {{ saveBusy ? 'Saving…' : 'Save' }}
        </button>
      </div>
    </template>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { staffFetch } from '../api'
import { friendlyError, networkErrorMessage } from '../utils/errors'
import { useToast } from '../composables/useToast'
import BulldozerLoader from './BulldozerLoader.vue'
import StaffTip from './StaffTip.vue'
import ClientUploadInvites from './ClientUploadInvites.vue'
import ClientQuickEnroll from './ClientQuickEnroll.vue'

const route = useRoute()
const router = useRouter()
const toast = useToast()

const STATUS_OPTIONS = [
  { value: 'active', label: 'Active' },
  { value: 'completed', label: 'Completed' },
  { value: 'inactive', label: 'Inactive' },
  { value: 'pending', label: 'Pending (legacy)' },
]

const PROGRAM_OPTIONS = [
  { value: 'capsa', label: 'CAPSA' },
  { value: 'citybuild', label: 'City Build' },
  { value: 'pit_stop', label: 'Pit Stop' },
  { value: 'guard_card', label: 'Security Guard Card Training' },
  { value: 'general', label: 'General Employment Assistance' },
]

const PIT_STOP_STAGE_OPTIONS = [
  { value: 'applicant', label: 'Applicant — not yet accepted' },
  { value: 'waitlisted', label: 'Waitlisted' },
  { value: 'active_participant', label: 'Active participant' },
  { value: 'worker', label: 'Worker (has portal login)' },
  { value: 'exited', label: 'Exited program' },
]

const CITYBUILD_STAGE_GROUPS = [
  {
    label: 'Pre-registration',
    options: [
      { value: 'general_interest', label: 'General interest' },
      { value: 'interview_scheduled', label: 'Interview scheduled' },
      { value: 'interview_completed', label: 'Interview completed' },
      { value: 'drug_test', label: 'Drug test' },
      { value: 'in_the_running', label: 'In the running — file submission' },
      { value: 'waitlisted', label: 'Waitlisted' },
      { value: 'accepted', label: 'Accepted' },
      { value: 'dropped', label: 'Dropped' },
    ],
  },
  {
    label: 'CBA 12-week program',
    options: [
      { value: 'enrolled', label: 'Enrolled' },
      { value: 'arrived', label: 'Arrived' },
      { value: 'completed', label: 'Completed' },
    ],
  },
]

const EMPLOYMENT_OPTIONS = [
  { value: 'unemployed', label: 'Unemployed' },
  { value: 'part_time', label: 'Part-time' },
  { value: 'full_time', label: 'Full-time' },
  { value: 'underemployed', label: 'Underemployed' },
  { value: 'student', label: 'Student' },
  { value: 'other', label: 'Other' },
]

const LANGUAGE_OPTIONS = [
  { value: 'en', label: 'English' },
  { value: 'es', label: 'Spanish' },
  { value: 'zh', label: 'Chinese' },
  { value: 'vi', label: 'Vietnamese' },
  { value: 'tl', label: 'Tagalog/Filipino' },
  { value: 'other', label: 'Other' },
]

interface WorkerPortal {
  has_account: boolean
  login_phone: string
  portal_access: boolean
  worker_status: string
  worker_status_display: string
  last_login?: string | null
  last_clock_in?: string | null
}

interface PitStopApplication {
  id: number
  review_status: string
  review_status_display: string
  review_notes: string
  age: number | null
  area_code: string
  has_resume: boolean
  position_applied_for: string
  available_days: string[]
}

interface ClientDetail {
  id: number
  full_name: string
  first_name: string
  middle_name?: string | null
  last_name: string
  phone: string
  email?: string | null
  status: string
  training_interest: string
  pit_stop_stage: string
  pit_stop_stage_display?: string
  citybuild_stage: string
  citybuild_stage_display?: string
  citybuild_packet?: { on_file: number; total: number; missing_count: number } | null
  worker_portal?: WorkerPortal | null
  pit_stop_application?: PitStopApplication | null
  employment_status: string
  language: string
  address?: string | null
  city?: string | null
  state?: string | null
  zip_code?: string | null
  program_start_date?: string | null
  program_completed_date?: string | null
  staff_name?: string | null
}

interface CaseNote {
  id: number
  note_date: string
  content: string
  staff_member: string
}

const emptyForm = () => ({
  first_name: '',
  last_name: '',
  phone: '',
  email: '',
  status: 'active',
  training_interest: 'general',
  pit_stop_stage: 'applicant',
  citybuild_stage: 'general_interest',
  employment_status: 'unemployed',
  language: 'en',
  address: '',
  city: '',
  state: '',
  zip_code: '',
  program_start_date: '',
  program_completed_date: '',
})

const client = ref<ClientDetail | null>(null)
const form = reactive(emptyForm())
const savedSnapshot = ref('')
const notes = ref<CaseNote[]>([])
const loading = ref(true)
const error = ref('')
const noteContent = ref('')
const noteBusy = ref(false)
const saveBusy = ref(false)
const promoteBusy = ref(false)
const editingDetails = ref(false)

const formDirty = computed(() => Boolean(client.value) && JSON.stringify(form) !== savedSnapshot.value)
const workerPortal = computed(() => client.value?.worker_portal || null)
const pitStopApplication = computed(() => client.value?.pit_stop_application || null)
const citybuildPacket = computed(() => client.value?.citybuild_packet || null)

const displayName = computed(() => {
  if (!client.value) return ''
  const fromForm = `${form.first_name} ${form.last_name}`.trim()
  return fromForm || client.value.full_name
})

const programLabel = computed(
  () => PROGRAM_OPTIONS.find((opt) => opt.value === form.training_interest)?.label || form.training_interest,
)

const stageLabel = computed(() => {
  if (form.training_interest === 'pit_stop') {
    return PIT_STOP_STAGE_OPTIONS.find((opt) => opt.value === form.pit_stop_stage)?.label || ''
  }
  if (form.training_interest === 'citybuild') {
    for (const group of CITYBUILD_STAGE_GROUPS) {
      const hit = group.options.find((opt) => opt.value === form.citybuild_stage)
      if (hit) return hit.label
    }
  }
  return ''
})

const phoneHref = computed(() => {
  const digits = form.phone.replace(/\D/g, '')
  if (digits.length < 10) return ''
  return `tel:+${digits.length === 10 ? `1${digits}` : digits}`
})

const hopActive = computed(() => {
  const focus = String(route.query.focus || '')
  if (focus === 'notes') return 'notes' as const
  if (focus === 'classes') return 'classes' as const
  return 'profile' as const
})

function formatDateTime(value: string) {
  const d = new Date(value)
  return Number.isNaN(d.getTime())
    ? value
    : d.toLocaleString(undefined, {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
        hour: 'numeric',
        minute: '2-digit',
      })
}

function clientId() {
  return Number(route.params.id)
}

function goBack() {
  if (window.history.length > 1) router.back()
  else router.push({ name: 'Clients' })
}

function jumpTo(id: string) {
  if (id === 'client-details') editingDetails.value = true
  router.replace({ name: 'ClientDetail', params: { id: clientId() }, query: focusQuery(id) })
  requestAnimationFrame(() => {
    document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  })
}

function focusQuery(id: string) {
  if (id === 'client-notes') return { focus: 'notes' }
  if (id === 'client-classes') return { focus: 'classes' }
  if (id === 'client-pitstop') return { focus: 'pitstop' }
  if (id === 'client-citybuild') return { focus: 'citybuild' }
  return {}
}

function toggleDetails() {
  editingDetails.value = !editingDetails.value
  if (editingDetails.value) jumpTo('client-details')
}

function scrollToFocus() {
  const focus = String(route.query.focus || '')
  const ids: Record<string, string> = {
    notes: 'client-notes',
    classes: 'client-classes',
    pitstop: 'client-pitstop',
    citybuild: 'client-citybuild',
    details: 'client-details',
  }
  const id = ids[focus] || ''
  if (!id) return
  if (focus === 'details') editingDetails.value = true
  requestAnimationFrame(() => {
    document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  })
}

function syncForm(c: ClientDetail) {
  form.first_name = c.first_name || ''
  form.last_name = c.last_name || ''
  form.phone = c.phone || ''
  form.email = c.email || ''
  form.status = c.status || 'active'
  form.training_interest = c.training_interest || 'general'
  form.pit_stop_stage = c.pit_stop_stage || 'applicant'
  form.citybuild_stage = c.citybuild_stage || 'general_interest'
  form.employment_status = c.employment_status || 'unemployed'
  form.language = c.language || 'en'
  form.address = c.address || ''
  form.city = c.city || ''
  form.state = c.state || ''
  form.zip_code = c.zip_code || ''
  form.program_start_date = c.program_start_date || ''
  form.program_completed_date = c.program_completed_date || ''
  savedSnapshot.value = JSON.stringify(form)
}

async function saveClient() {
  if (!form.first_name.trim() || !form.last_name.trim()) {
    toast.error('First and last name are required.')
    editingDetails.value = true
    return
  }
  if (!form.phone.trim()) {
    toast.error('Phone number is required.')
    editingDetails.value = true
    return
  }
  saveBusy.value = true
  try {
    const resp = await staffFetch(`/api/staff/clients/${clientId()}/`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        first_name: form.first_name.trim(),
        last_name: form.last_name.trim(),
        phone: form.phone.trim(),
        email: form.email.trim() || null,
        status: form.status,
        training_interest: form.training_interest,
        pit_stop_stage: form.pit_stop_stage,
        citybuild_stage: form.citybuild_stage,
        employment_status: form.employment_status,
        language: form.language,
        address: form.address.trim() || null,
        city: form.city.trim() || null,
        state: form.state.trim() || null,
        zip_code: form.zip_code.trim() || null,
        program_start_date: form.program_start_date || null,
        program_completed_date: form.program_completed_date || null,
      }),
    })
    const body = await resp.json().catch(() => null)
    if (!resp.ok) {
      toast.error(friendlyError(body, 'Could not save client info.'))
      return
    }
    client.value = body
    syncForm(body)
    toast.success('Client info saved.')
  } catch (e) {
    toast.error(networkErrorMessage(e))
  } finally {
    saveBusy.value = false
  }
}

async function promoteToWorker() {
  if (formDirty.value) {
    toast.error('Save your changes first, then give portal access.')
    return
  }
  const ok = window.confirm(
    `Give ${displayName.value} worker portal access? They will be able to log in and clock in with their phone and a PIN (last 4 digits of their phone).`,
  )
  if (!ok) return

  promoteBusy.value = true
  try {
    const resp = await staffFetch(`/api/staff/clients/${clientId()}/pitstop/promote/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    })
    const body = await resp.json().catch(() => null)
    if (!resp.ok) {
      toast.error(friendlyError(body, 'Could not give portal access.'))
      return
    }
    client.value = body.client
    syncForm(body.client)
    toast.success(body.message || 'Worker portal access created.')
  } catch (e) {
    toast.error(networkErrorMessage(e))
  } finally {
    promoteBusy.value = false
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
    const body = await clientResp.json()
    client.value = body
    syncForm(body)
    notes.value = notesResp.ok ? await notesResp.json() : []
    scrollToFocus()
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
watch(() => route.query.focus, () => {
  if (client.value) scrollToFocus()
})
</script>
