<template>
  <section class="space-y-3">
    <div class="staff-card p-4">
      <div class="staff-panel-header">
        <span class="material-symbols-outlined" aria-hidden="true">assignment_ind</span>
        <h3>Pit Stop applications</h3>
        <StaffTip text="The digital paper stack. Open a name to read the full application, resume, and program answers. You can print from the detail page." />
      </div>
      <p class="text-sm text-stone-600 mb-3">
        Review applications here instead of paper forms. Resume is required. The written answers
        show whether the person understands Pit Stop is a workforce program, not a job.
      </p>

      <div class="staff-chip-row">
        <button
          v-for="chip in statusChips"
          :key="chip.value"
          type="button"
          class="staff-chip"
          :class="{ 'staff-chip-active': statusFilter === chip.value }"
          @click="statusFilter = chip.value"
        >
          {{ chip.label }}
        </button>
      </div>

      <div class="staff-field mt-3">
        <label for="ps-search">Search name or phone</label>
        <input
          id="ps-search"
          v-model="search"
          type="search"
          class="staff-input"
          placeholder="Name or phone"
        />
      </div>
    </div>

    <CardSkeleton v-if="loading" variant="list" :count="6" />
    <div v-else-if="error" class="staff-card p-4 text-center space-y-3">
      <p class="text-sm">{{ error }}</p>
      <button type="button" class="staff-btn staff-btn-secondary" @click="load">Retry</button>
    </div>
    <p v-else-if="applications.length === 0" class="staff-card p-4 text-sm text-stone-600">
      No applications match this filter.
    </p>
    <ul v-else class="staff-card divide-y divide-stone-100">
      <li v-for="app in applications" :key="app.id">
        <RouterLink
          :to="{ name: 'PitStopApplicationDetail', params: { id: app.id } }"
          class="flex items-start justify-between gap-3 p-4 hover:bg-stone-50"
        >
          <span class="min-w-0">
            <span class="block text-sm font-semibold truncate">{{ app.full_name }}</span>
            <span class="block text-xs text-stone-500 mt-0.5">
              Age {{ app.age ?? 'unknown' }}
              · {{ app.area_code || 'no area code' }}
              · {{ app.position_applied_for }}
            </span>
            <span class="block text-xs text-stone-500">
              {{ formatWhen(app.created_at) }}
              · {{ app.open_availability ? 'has availability' : 'no shifts marked' }}
            </span>
          </span>
          <span class="flex flex-col items-end gap-1 shrink-0">
            <span
              class="text-[10px] uppercase font-bold tracking-wide rounded-full px-2 py-0.5"
              :class="statusClass(app.review_status)"
            >
              {{ app.review_status_display }}
            </span>
            <span
              class="text-[10px] uppercase font-bold tracking-wide rounded-full px-2 py-0.5"
              :class="app.has_resume ? 'bg-emerald-100 text-emerald-700' : 'bg-red-100 text-red-700'"
            >
              {{ app.has_resume ? 'resume' : 'missing resume' }}
            </span>
          </span>
        </RouterLink>
      </li>
    </ul>
    <p v-if="!loading && total > applications.length" class="text-xs text-stone-500 px-1">
      Showing {{ applications.length }} of {{ total }}. Narrow the search to see older ones.
    </p>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import CardSkeleton from './dashboard/CardSkeleton.vue'
import StaffTip from './StaffTip.vue'
import { staffFetch } from '../api'

interface PitStopListItem {
  id: number
  full_name: string
  age: number | null
  area_code: string
  position_applied_for: string
  review_status: string
  review_status_display: string
  has_resume: boolean
  open_availability: boolean
  created_at: string
}

const statusChips = [
  { value: '', label: 'All' },
  { value: 'new', label: 'Needs review' },
  { value: 'interviewed', label: 'Interviewed' },
  { value: 'maybe', label: 'Maybe' },
  { value: 'moving_forward', label: 'Moving forward' },
  { value: 'not_moving_forward', label: 'Not moving forward' },
]

const applications = ref<PitStopListItem[]>([])
const total = ref(0)
const loading = ref(true)
const error = ref('')
const statusFilter = ref('new')
const search = ref('')
let searchTimer: ReturnType<typeof setTimeout> | null = null

function statusClass(status: string) {
  if (status === 'new') return 'bg-amber-100 text-amber-800'
  if (status === 'interviewed') return 'bg-sky-100 text-sky-800'
  if (status === 'maybe') return 'bg-stone-200 text-stone-700'
  if (status === 'moving_forward') return 'bg-emerald-100 text-emerald-800'
  if (status === 'not_moving_forward') return 'bg-red-100 text-red-700'
  return 'bg-stone-100 text-stone-600'
}

function formatWhen(value: string) {
  const d = new Date(value)
  return Number.isNaN(d.getTime())
    ? value
    : d.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })
}

async function load() {
  loading.value = true
  error.value = ''
  const params = new URLSearchParams()
  if (statusFilter.value) params.set('status', statusFilter.value)
  if (search.value.trim()) params.set('q', search.value.trim())
  try {
    const resp = await staffFetch(`/api/staff/pitstop-applications/?${params}`)
    if (!resp.ok) {
      error.value = 'Could not load applications.'
      return
    }
    const body = await resp.json()
    applications.value = body.results || []
    total.value = Number(body.total) || 0
  } catch {
    error.value = 'No connection.'
  } finally {
    loading.value = false
  }
}

watch(statusFilter, load)
watch(search, () => {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(load, 250)
})

onMounted(load)
</script>
