<template>
  <section class="space-y-3">
    <div class="no-print flex items-center justify-between gap-2">
      <button type="button" class="text-sm font-semibold staff-link" @click="router.push({ name: 'PitStopApplications' })">
        ← All Pit Stop applications
      </button>
      <button type="button" class="staff-btn staff-btn-secondary" @click="printPage">
        <span class="material-symbols-outlined" aria-hidden="true">print</span>
        Print
      </button>
    </div>

    <BulldozerLoader v-if="loading" label="Loading application…" />
    <div v-else-if="error" class="staff-card p-4 text-center space-y-3">
      <p class="text-sm">{{ error }}</p>
      <button type="button" class="staff-btn staff-btn-secondary" @click="load">Retry</button>
    </div>

    <template v-else-if="app">
      <div class="staff-card p-4 no-print space-y-3">
        <div class="staff-panel-header">
          <span class="material-symbols-outlined" aria-hidden="true">rate_review</span>
          <h3>Review</h3>
          <StaffTip text="This is the decision that used to get written on the paper application. Your name is saved when you update it." />
        </div>
        <div class="staff-field-grid staff-field-grid-2">
          <div class="staff-field">
            <label for="ps-status">Status</label>
            <select id="ps-status" v-model="review.review_status" class="staff-input">
              <option v-for="opt in reviewStatuses" :key="opt.value" :value="opt.value">
                {{ opt.label }}
              </option>
            </select>
          </div>
          <div class="staff-field">
            <label for="ps-interview">Interview date</label>
            <input id="ps-interview" v-model="review.interviewed_on" type="date" class="staff-input" />
          </div>
        </div>
        <div class="staff-field">
          <label for="ps-notes">Review notes</label>
          <textarea
            id="ps-notes"
            v-model="review.review_notes"
            rows="3"
            class="staff-input"
            placeholder="What you would have written on the paper form."
          />
        </div>
        <div class="flex items-center justify-between gap-2">
          <p class="text-xs text-stone-500">
            <template v-if="app.reviewed_by">Last updated by {{ app.reviewed_by }}</template>
            <template v-if="app.review_updated_at"> · {{ formatWhen(app.review_updated_at) }}</template>
          </p>
          <button
            type="button"
            class="staff-btn staff-btn-primary"
            :disabled="saveBusy || !reviewDirty"
            @click="saveReview"
          >
            {{ saveBusy ? 'Saving…' : reviewDirty ? 'Save review' : 'Saved' }}
          </button>
        </div>
        <p v-if="saveError" class="text-sm text-red-700">{{ saveError }}</p>
      </div>

      <article class="staff-card p-5 ps-print-sheet space-y-5">
        <header class="border-b border-stone-200 pb-3">
          <p class="text-[11px] uppercase tracking-wider text-stone-500 font-semibold">Mission Hiring Hall</p>
          <h2 class="text-xl font-bold text-stone-900">Pit Stop Participant Application</h2>
          <p class="text-sm text-stone-600">FY 26-27 · Submitted {{ formatWhen(app.created_at) }}</p>
        </header>

        <section>
          <h3 class="ps-section-title">Contact information</h3>
          <dl class="ps-grid">
            <div>
              <dt>Name</dt>
              <dd>{{ nameLine }}</dd>
            </div>
            <div>
              <dt>Age</dt>
              <dd>{{ app.age ?? '—' }}</dd>
            </div>
            <div>
              <dt>Phone</dt>
              <dd>{{ app.phone || '—' }}</dd>
            </div>
            <div>
              <dt>Email</dt>
              <dd>{{ app.email || '—' }}</dd>
            </div>
            <div class="ps-span-2">
              <dt>Address</dt>
              <dd>{{ addressLine }}</dd>
            </div>
          </dl>
        </section>

        <section>
          <h3 class="ps-section-title">Position</h3>
          <dl class="ps-grid">
            <div>
              <dt>Position applying for</dt>
              <dd>{{ app.position_applied_for || '—' }}</dd>
            </div>
            <div>
              <dt>Available start date</dt>
              <dd>{{ app.available_start_date || '—' }}</dd>
            </div>
            <div>
              <dt>Legally able to work in the U.S.?</dt>
              <dd>{{ app.can_work_us ? 'Yes' : 'No' }}</dd>
            </div>
            <div>
              <dt>Veteran?</dt>
              <dd>{{ app.is_veteran ? 'Yes' : 'No' }}</dd>
            </div>
            <div class="ps-span-2">
              <dt>Desired schedule</dt>
              <dd>{{ scheduleTypes || '—' }}</dd>
            </div>
          </dl>
        </section>

        <section>
          <h3 class="ps-section-title">Schedule availability</h3>
          <p v-if="!scheduleRows.length" class="text-sm text-stone-500">No shifts marked.</p>
          <table v-else class="ps-avail-table">
            <thead>
              <tr>
                <th>Day</th>
                <th>Shifts</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in scheduleRows" :key="row.day">
                <td>{{ row.day }}</td>
                <td>{{ row.slots }}</td>
              </tr>
            </tbody>
          </table>
        </section>

        <section>
          <h3 class="ps-section-title">Employment history</h3>
          <p v-if="!jobs.length" class="text-sm text-stone-500">None entered. Check the resume.</p>
          <div v-for="(job, index) in jobs" :key="index" class="ps-job">
            <p class="text-sm font-semibold">Job {{ index + 1 }}</p>
            <dl class="ps-grid">
              <div>
                <dt>Company</dt>
                <dd>{{ job.company_name || '—' }}</dd>
              </div>
              <div>
                <dt>Dates</dt>
                <dd>{{ job.dates_of_employment || '—' }}</dd>
              </div>
              <div>
                <dt>City / State</dt>
                <dd>{{ [job.city, job.state].filter(Boolean).join(', ') || '—' }}</dd>
              </div>
              <div>
                <dt>Job title</dt>
                <dd>{{ job.job_title || '—' }}</dd>
              </div>
              <div>
                <dt>Supervisor</dt>
                <dd>{{ job.manager_name || '—' }}</dd>
              </div>
              <div>
                <dt>Supervisor phone</dt>
                <dd>{{ job.manager_phone || '—' }}</dd>
              </div>
              <div class="ps-span-2">
                <dt>Responsibilities</dt>
                <dd class="whitespace-pre-wrap">{{ job.responsibilities || '—' }}</dd>
              </div>
            </dl>
          </div>
        </section>

        <section>
          <h3 class="ps-section-title">Education history</h3>
          <dl class="ps-grid">
            <div class="ps-span-2">
              <dt>High school</dt>
              <dd>{{ highSchoolLine }}</dd>
            </div>
            <div class="ps-span-2">
              <dt>Post-secondary</dt>
              <dd>{{ postSecondaryLine }}</dd>
            </div>
            <div v-if="app.education_history" class="ps-span-2">
              <dt>Notes</dt>
              <dd class="whitespace-pre-wrap">{{ app.education_history }}</dd>
            </div>
          </dl>
        </section>

        <section>
          <h3 class="ps-section-title">Program questions</h3>
          <p class="text-xs text-stone-500 mb-2">
            These answers are how we check that the applicant knows Pit Stop is a workforce
            program — not employment itself.
          </p>
          <div class="space-y-3">
            <div>
              <p class="text-xs font-semibold uppercase tracking-wide text-stone-500">What is Pit Stop?</p>
              <p class="text-sm whitespace-pre-wrap mt-1">{{ app.what_is_pit_stop || '—' }}</p>
            </div>
            <div>
              <p class="text-xs font-semibold uppercase tracking-wide text-stone-500">Why do you want to participate?</p>
              <p class="text-sm whitespace-pre-wrap mt-1">{{ app.why_participate || '—' }}</p>
            </div>
            <div>
              <p class="text-xs font-semibold uppercase tracking-wide text-stone-500">Goals after completing the program</p>
              <p class="text-sm whitespace-pre-wrap mt-1">{{ app.goals_after_program || '—' }}</p>
            </div>
            <div>
              <p class="text-xs font-semibold uppercase tracking-wide text-stone-500">How this program can support long-term workforce goals</p>
              <p class="text-sm whitespace-pre-wrap mt-1">{{ app.how_program_supports_goals || '—' }}</p>
            </div>
          </div>
        </section>

        <section>
          <h3 class="ps-section-title">Resume</h3>
          <p class="text-sm">
            <span
              class="text-[10px] uppercase font-bold tracking-wide rounded-full px-2 py-0.5 mr-2"
              :class="app.has_resume ? 'bg-emerald-100 text-emerald-700' : 'bg-red-100 text-red-700'"
            >
              {{ app.has_resume ? 'On file' : 'Missing' }}
            </span>
            <a
              v-if="resumeHref"
              :href="resumeHref"
              target="_blank"
              rel="noopener"
              class="staff-link text-sm font-semibold"
            >
              Open resume
            </a>
            <span v-else-if="!app.has_resume" class="text-stone-500">Ask for it before deciding.</span>
          </p>
        </section>

        <section class="border-t border-stone-200 pt-3">
          <dl class="ps-grid">
            <div>
              <dt>Signature</dt>
              <dd>{{ app.signature_name || '—' }}</dd>
            </div>
            <div>
              <dt>Date</dt>
              <dd>{{ app.signed_on || '—' }}</dd>
            </div>
          </dl>
        </section>

        <p class="text-xs text-stone-500 no-print">
          Client record:
          <RouterLink
            :to="{ name: 'ClientDetail', params: { id: app.client_id }, query: { focus: 'pitstop' } }"
            class="staff-link font-semibold"
          >
            Open {{ app.full_name }}
          </RouterLink>
        </p>
      </article>
    </template>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getApiUrl } from '../../config/api'
import { staffFetch } from '../api'
import BulldozerLoader from './BulldozerLoader.vue'
import StaffTip from './StaffTip.vue'

interface EmploymentJob {
  company_name?: string
  dates_of_employment?: string
  city?: string
  state?: string
  manager_name?: string
  manager_phone?: string
  job_title?: string
  responsibilities?: string
}

interface PitStopDetail {
  id: number
  client_id: number
  full_name: string
  first_name: string
  middle_name: string
  last_name: string
  phone: string
  email: string
  address: string
  city: string
  state: string
  zip_code: string
  age: number | null
  has_resume: boolean
  resume_url: string
  review_status: string
  position_applied_for: string
  available_start_date: string | null
  employment_desired: string[]
  can_work_us: boolean
  is_veteran: boolean
  weekly_schedule: Record<string, string[]>
  employment_history: EmploymentJob[]
  high_school_name: string
  high_school_city: string
  high_school_state: string
  post_secondary_name: string
  post_secondary_city: string
  post_secondary_state: string
  education_history: string
  what_is_pit_stop: string
  why_participate: string
  goals_after_program: string
  how_program_supports_goals: string
  signature_name: string
  signed_on: string | null
  interviewed_on: string | null
  review_notes: string
  reviewed_by: string
  review_updated_at: string | null
  created_at: string
}

const reviewStatuses = [
  { value: 'new', label: 'New — needs review' },
  { value: 'interviewed', label: 'Interviewed' },
  { value: 'maybe', label: 'Maybe' },
  { value: 'moving_forward', label: 'Moving forward' },
  { value: 'not_moving_forward', label: 'Not moving forward' },
]

const scheduleLabels: Record<string, string> = {
  full_time: 'Full-time',
  part_time: 'Part-time',
  relief_list: 'Relief list',
}

const shiftLabels: Record<string, string> = {
  '7-4': '7AM–4PM',
  '8-5': '8AM–5PM',
  '9-5': '9AM–5PM',
  '9-6': '9AM–6PM',
  '10-7': '10AM–7PM',
  '11-8': '11AM–8PM',
  '12-9': '12PM–9PM',
  '18-3': '6PM–3AM',
  '21-6': '9PM–6AM',
  '23-8': '11PM–8AM',
}

const route = useRoute()
const router = useRouter()
const app = ref<PitStopDetail | null>(null)
const loading = ref(true)
const error = ref('')
const saveBusy = ref(false)
const saveError = ref('')
const review = reactive({
  review_status: 'new',
  interviewed_on: '',
  review_notes: '',
})
const savedSnapshot = ref('')

const reviewDirty = computed(() => JSON.stringify(review) !== savedSnapshot.value)

const nameLine = computed(() => {
  if (!app.value) return '—'
  return [app.value.first_name, app.value.middle_name, app.value.last_name].filter(Boolean).join(' ')
})

const addressLine = computed(() => {
  if (!app.value) return '—'
  const line = [app.value.address, app.value.city, app.value.state, app.value.zip_code]
    .filter(Boolean)
    .join(', ')
  return line || '—'
})

const scheduleTypes = computed(() =>
  (app.value?.employment_desired || []).map((value) => scheduleLabels[value] || value).join(', '),
)

const scheduleRows = computed(() => {
  const schedule = app.value?.weekly_schedule || {}
  return Object.entries(schedule)
    .filter(([, times]) => Array.isArray(times) && times.length)
    .map(([day, times]) => ({
      day,
      slots: times.map((slot) => shiftLabels[slot] || slot).join(', '),
    }))
})

const jobs = computed(() =>
  (app.value?.employment_history || []).filter((job) => Object.values(job || {}).some(Boolean)),
)

const highSchoolLine = computed(() => {
  if (!app.value) return '—'
  return [app.value.high_school_name, app.value.high_school_city, app.value.high_school_state]
    .filter(Boolean)
    .join(', ') || '—'
})

const postSecondaryLine = computed(() => {
  if (!app.value) return '—'
  return [app.value.post_secondary_name, app.value.post_secondary_city, app.value.post_secondary_state]
    .filter(Boolean)
    .join(', ') || '—'
})

const resumeHref = computed(() => {
  if (!app.value?.resume_url) return ''
  return getApiUrl(app.value.resume_url)
})

function formatWhen(value: string) {
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

function applyReview(detail: PitStopDetail) {
  review.review_status = detail.review_status
  review.interviewed_on = detail.interviewed_on || ''
  review.review_notes = detail.review_notes || ''
  savedSnapshot.value = JSON.stringify(review)
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const resp = await staffFetch(`/api/staff/pitstop-applications/${route.params.id}/`)
    if (!resp.ok) {
      error.value = 'Could not load this application.'
      return
    }
    const body = await resp.json()
    app.value = body
    applyReview(body)
  } catch {
    error.value = 'No connection.'
  } finally {
    loading.value = false
  }
}

async function saveReview() {
  if (!app.value) return
  saveBusy.value = true
  saveError.value = ''
  try {
    const resp = await staffFetch(`/api/staff/pitstop-applications/${app.value.id}/`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        review_status: review.review_status,
        interviewed_on: review.interviewed_on || null,
        review_notes: review.review_notes,
      }),
    })
    if (!resp.ok) {
      saveError.value = 'Could not save the review.'
      return
    }
    const body = await resp.json()
    app.value = body
    applyReview(body)
  } catch {
    saveError.value = 'No connection.'
  } finally {
    saveBusy.value = false
  }
}

function printPage() {
  window.print()
}

onMounted(load)
</script>

<style scoped>
.ps-section-title {
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #57534e;
  margin-bottom: 0.5rem;
}
.ps-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 0.65rem 1.25rem;
}
@media (min-width: 640px) {
  .ps-grid {
    grid-template-columns: 1fr 1fr;
  }
  .ps-span-2 {
    grid-column: span 2;
  }
}
.ps-grid dt {
  font-size: 0.7rem;
  font-weight: 600;
  color: #78716c;
}
.ps-grid dd {
  font-size: 0.9rem;
  color: #1c1917;
}
.ps-job + .ps-job {
  margin-top: 0.85rem;
  padding-top: 0.85rem;
  border-top: 1px solid #e7e5e4;
}
.ps-avail-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.85rem;
}
.ps-avail-table th,
.ps-avail-table td {
  text-align: left;
  padding: 0.35rem 0.5rem;
  border-bottom: 1px solid #e7e5e4;
}
.ps-avail-table th {
  font-size: 0.7rem;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: #78716c;
}
</style>
