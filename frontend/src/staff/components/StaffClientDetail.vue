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
      <ClientHopBar
        :client-id="client.id"
        :client-name="displayName"
        :active="hopActive"
      />

      <!-- Contact & status (editable) -->
      <div id="client-info" class="staff-card p-4 relative">
        <div
          v-if="saveBusy"
          class="absolute inset-0 bg-white/70 rounded-xl flex items-center justify-center z-10"
        >
          <BulldozerLoader label="Saving…" />
        </div>
        <div class="staff-panel-header">
          <span class="material-symbols-outlined" aria-hidden="true">badge</span>
          <h3>Client info</h3>
          <StaffTip text="Fix the person’s name, phone, email, program, or status here. Tap Save when done — changes apply right away." />
        </div>

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
            <label for="cd-phone">
              Phone
              <StaffTip text="Main number we call or text. Digits only is fine — we store what you type." />
            </label>
            <input id="cd-phone" v-model="form.phone" type="tel" class="staff-input" autocomplete="tel" />
          </div>
          <div class="staff-field">
            <label for="cd-email">Email</label>
            <input id="cd-email" v-model="form.email" type="email" class="staff-input" autocomplete="email" />
          </div>
          <div class="staff-field">
            <label for="cd-status">
              Status
              <StaffTip text="Active = currently working with us. Completed = finished a program. Inactive = not coming in right now." />
            </label>
            <select id="cd-status" v-model="form.status" class="staff-input">
              <option v-for="opt in STATUS_OPTIONS" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
            </select>
          </div>
          <div class="staff-field">
            <label for="cd-program">
              Program
              <StaffTip text="Which MHH program this person signed up for. Use General if they are not in CAPSA, City Build, or Pit Stop." />
            </label>
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
            <label for="cd-start">
              Program start date
              <StaffTip text="When they began with us. Optional — leave blank if you do not know yet." />
            </label>
            <input id="cd-start" v-model="form.program_start_date" type="date" class="staff-input" />
          </div>
          <div class="staff-field">
            <label for="cd-done">Program completed date</label>
            <input id="cd-done" v-model="form.program_completed_date" type="date" class="staff-input" />
          </div>
        </div>

        <details class="mb-3">
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

        <p class="text-xs text-stone-500 mb-3">
          Assigned staff: <span class="font-semibold text-stone-700">{{ client.staff_name || 'Unassigned' }}</span>
        </p>

        <button
          type="button"
          class="staff-btn staff-btn-primary w-full"
          :disabled="saveBusy || !formDirty"
          @click="saveClient"
        >
          {{ saveBusy ? 'Saving…' : formDirty ? 'Save changes' : 'No changes' }}
        </button>
      </div>

      <!-- Classes & Orientation -->
      <div id="client-classes" class="staff-card p-4 relative">
        <div
          v-if="classBusy"
          class="absolute inset-0 bg-white/70 rounded-xl flex items-center justify-center z-10"
        >
          <BulldozerLoader label="Updating classes…" />
        </div>
        <div class="staff-panel-header">
          <span class="material-symbols-outlined" aria-hidden="true">event</span>
          <h3>Classes &amp; Orientation</h3>
          <StaffTip text="Sign this person up for Orientation, Job Readiness Training (JRT), resume workshops, or other classes. Pick a filter, choose a date, then tap Add." />
        </div>

        <CardSkeleton v-if="classesLoading" variant="list" :count="2" />

        <template v-else>
          <div v-if="enrolledClasses.length" class="space-y-1.5 mb-3 staff-fade-in">
            <p class="text-xs font-semibold text-stone-500 uppercase tracking-wide">Already signed up</p>
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
          <p v-else class="text-sm text-stone-500 mb-3">Not signed up for any upcoming classes yet.</p>

          <p class="text-xs font-semibold text-stone-500 uppercase tracking-wide mb-1.5">
            Add to a class
            <StaffTip text="Filter by type (JRT = Job Readiness Training), then pick the exact date/time from the list." />
          </p>
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
              @click="enrollInClass"
            >
              Add
            </button>
          </div>
          <p v-if="upcomingSessions.length === 0" class="text-xs text-stone-400 mt-1.5">
            No upcoming classes scheduled yet —
            <RouterLink to="/classes" class="text-orange-600 font-semibold">create one on the Classes page</RouterLink>.
          </p>
          <p v-else-if="filteredSessions.length === 0" class="text-xs text-stone-400 mt-1.5">
            Nothing in this filter. Try “All” or add a class on the
            <RouterLink to="/classes" class="text-orange-600 font-semibold">Classes</RouterLink> page.
          </p>
        </template>
      </div>

      <!-- Quick case note -->
      <div id="client-notes" class="staff-card p-4 relative">
        <div
          v-if="noteBusy"
          class="absolute inset-0 bg-white/70 rounded-xl flex items-center justify-center z-10"
        >
          <BulldozerLoader label="Saving note…" />
        </div>
        <div class="staff-panel-header">
          <span class="material-symbols-outlined" aria-hidden="true">edit_note</span>
          <h3>Quick case note</h3>
          <StaffTip text="Write what happened when they came in — orientation, interview, paperwork, etc. This is the main place staff should leave a record." />
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
          <StaffTip text="Past notes from any staff member. Newest first." />
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
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { staffFetch } from '../api'
import { friendlyError, networkErrorMessage } from '../utils/errors'
import { useToast } from '../composables/useToast'
import BulldozerLoader from './BulldozerLoader.vue'
import CardSkeleton from './dashboard/CardSkeleton.vue'
import StaffTip from './StaffTip.vue'
import ClientHopBar from './ClientHopBar.vue'

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
  { value: 'general', label: 'General Employment Assistance' },
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

const CATEGORY_CHIPS = [
  { value: '', label: 'All' },
  { value: 'orientation', label: 'Orientation' },
  { value: 'job_readiness', label: 'JRT' },
  { value: 'resume_workshop', label: 'Resume' },
  { value: 'training', label: 'Skills' },
  { value: 'other', label: 'Other' },
]

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

const emptyForm = () => ({
  first_name: '',
  last_name: '',
  phone: '',
  email: '',
  status: 'active',
  training_interest: 'general',
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

const upcomingSessions = ref<UpcomingSession[]>([])
const enrolledClasses = ref<ClientClassEnrollment[]>([])
const selectedSessionId = ref<number | ''>('')
const classBusy = ref(false)
const classesLoading = ref(true)
const categoryFilter = ref('')

const formDirty = computed(() => JSON.stringify(form) !== savedSnapshot.value)

const filteredSessions = computed(() => {
  if (!categoryFilter.value) return upcomingSessions.value
  return upcomingSessions.value.filter((s) => s.category === categoryFilter.value)
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
  return enrolledClasses.value.some((e) => e.session_id === sessionId)
}

function syncForm(c: ClientDetail) {
  form.first_name = c.first_name || ''
  form.last_name = c.last_name || ''
  form.phone = c.phone || ''
  form.email = c.email || ''
  form.status = c.status || 'active'
  form.training_interest = c.training_interest || 'general'
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

const displayName = computed(() => {
  if (!client.value) return ''
  const fromForm = `${form.first_name} ${form.last_name}`.trim()
  return fromForm || client.value.full_name
})

const hopActive = computed(() => {
  const focus = String(route.query.focus || '')
  if (focus === 'notes') return 'notes' as const
  if (focus === 'classes') return 'classes' as const
  return 'profile' as const
})

function scrollToFocus() {
  const focus = String(route.query.focus || '')
  const id = focus === 'notes' ? 'client-notes' : focus === 'classes' ? 'client-classes' : ''
  if (!id) return
  requestAnimationFrame(() => {
    document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  })
}

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

async function saveClient() {
  if (!form.first_name.trim() || !form.last_name.trim()) {
    toast.error('First and last name are required.')
    return
  }
  if (!form.phone.trim()) {
    toast.error('Phone number is required.')
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
    const body = await clientResp.json()
    client.value = body
    syncForm(body)
    notes.value = notesResp.ok ? await notesResp.json() : []
    await loadClasses()
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
