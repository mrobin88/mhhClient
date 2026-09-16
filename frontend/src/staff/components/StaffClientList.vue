<template>
  <section class="space-y-3">
    <div class="staff-card p-4 space-y-3">
      <div class="staff-panel-header">
        <span class="material-symbols-outlined" aria-hidden="true">group</span>
        <h3>Clients</h3>
        <StaffTip text="This is the roster. Search, filter by program, then open someone to add them to a class or leave a note." />
      </div>
      <input
        ref="searchInput"
        v-model="searchQuery"
        type="search"
        placeholder="Name or phone"
        class="staff-input staff-search-hero-input"
        autocomplete="off"
        @input="debouncedSearch"
      />
      <div class="staff-home-actions">
        <RouterLink :to="{ name: 'ClientCreate' }" class="staff-btn staff-btn-primary">
          <span class="material-symbols-outlined" aria-hidden="true">person_add</span>
          Add a client
        </RouterLink>
      </div>

      <div>
        <p class="text-xs font-semibold uppercase tracking-wider text-stone-500 mb-1.5">Program</p>
        <div class="staff-chip-row">
          <button
            v-for="chip in PROGRAM_CHIPS"
            :key="chip.value || 'all'"
            type="button"
            class="staff-chip"
            :class="{ 'staff-chip-active': program === chip.value }"
            @click="setProgram(chip.value)"
          >
            {{ chip.label }}
          </button>
        </div>
      </div>

      <div v-if="program === 'pit_stop'">
        <p class="text-xs font-semibold uppercase tracking-wider text-stone-500 mb-1.5">Pit Stop stage</p>
        <div class="staff-chip-row">
          <button
            v-for="chip in STAGE_CHIPS"
            :key="chip.value || 'all'"
            type="button"
            class="staff-chip"
            :class="{ 'staff-chip-active': stage === chip.value }"
            @click="setStage(chip.value)"
          >
            {{ chip.label }}
          </button>
        </div>
      </div>

      <div v-if="program === 'citybuild'">
        <p class="text-xs font-semibold uppercase tracking-wider text-stone-500 mb-1.5">City Build stage</p>
        <div class="staff-chip-row">
          <button
            v-for="chip in CITYBUILD_STAGE_CHIPS"
            :key="chip.value || 'all'"
            type="button"
            class="staff-chip"
            :class="{ 'staff-chip-active': stage === chip.value }"
            @click="setStage(chip.value)"
          >
            {{ chip.label }}
          </button>
        </div>
      </div>
    </div>

    <p v-if="!loading && !error" class="text-xs font-semibold text-stone-500 px-1">
      {{ clients.length }} {{ clients.length === 1 ? 'person' : 'people' }}
    </p>

    <SkeletonClientList v-if="loading" />
    <div v-else-if="error" class="staff-card p-4 text-center space-y-3">
      <p class="text-sm text-stone-600">{{ error }}</p>
      <button type="button" class="staff-btn staff-btn-secondary" @click="search">Try again</button>
    </div>
    <div v-else-if="clients.length === 0" class="staff-card p-4 text-center space-y-2">
      <p class="text-sm text-stone-500">No clients match that search.</p>
      <RouterLink :to="{ name: 'ClientCreate' }" class="staff-link font-semibold">Add a client →</RouterLink>
    </div>

    <ul v-else class="space-y-2">
      <li v-for="client in clients" :key="client.id">
        <RouterLink
          :to="{ name: 'ClientDetail', params: { id: client.id } }"
          class="staff-card staff-client-row"
        >
          <div class="min-w-0 flex-1">
            <p class="font-semibold truncate">{{ client.full_name }}</p>
            <p class="text-sm text-stone-600 truncate">
              {{ client.phone }}
              <span v-if="client.email"> · {{ client.email }}</span>
            </p>
            <p class="text-xs text-stone-500 mt-0.5 truncate">
              {{ client.training_interest_display }}
              <template v-if="stageFor(client)"> · {{ stageFor(client) }}</template>
              <template v-if="client.staff_name"> · {{ client.staff_name }}</template>
            </p>
          </div>
          <span class="staff-client-row-status">{{ client.status }}</span>
          <span class="material-symbols-outlined staff-client-row-chevron" aria-hidden="true">chevron_right</span>
        </RouterLink>
      </li>
    </ul>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { staffFetch } from '../api'
import { friendlyError, networkErrorMessage } from '../utils/errors'
import SkeletonClientList from './SkeletonClientList.vue'
import StaffTip from './StaffTip.vue'

interface ClientRow {
  id: number
  full_name: string
  phone: string
  email?: string | null
  status: string
  staff_name?: string | null
  training_interest: string
  training_interest_display: string
  pit_stop_stage: string
  pit_stop_stage_display: string
  citybuild_stage: string
  citybuild_stage_display: string
}

const PROGRAM_CHIPS = [
  { value: '', label: 'All' },
  { value: 'capsa', label: 'CAPSA' },
  { value: 'citybuild', label: 'City Build' },
  { value: 'pit_stop', label: 'Pit Stop' },
  { value: 'guard_card', label: 'Guard Card' },
  { value: 'general', label: 'General' },
]

const STAGE_CHIPS = [
  { value: '', label: 'All' },
  { value: 'applicant', label: 'Applicants' },
  { value: 'waitlisted', label: 'Waitlisted' },
  { value: 'active_participant', label: 'Active' },
  { value: 'worker', label: 'Workers' },
  { value: 'exited', label: 'Exited' },
]

const CITYBUILD_STAGE_CHIPS = [
  { value: '', label: 'All' },
  { value: 'general_interest', label: 'Interest' },
  { value: 'interview_scheduled', label: 'Interview set' },
  { value: 'interview_completed', label: 'Interviewed' },
  { value: 'drug_test', label: 'Drug test' },
  { value: 'in_the_running', label: 'File packet' },
  { value: 'waitlisted', label: 'Waitlisted' },
  { value: 'accepted', label: 'Accepted' },
  { value: 'dropped', label: 'Dropped' },
  { value: 'enrolled', label: 'Enrolled' },
  { value: 'arrived', label: 'Arrived' },
  { value: 'completed', label: 'Completed' },
]

const route = useRoute()
const router = useRouter()
const searchQuery = ref('')
const program = ref('')
const stage = ref('')
const clients = ref<ClientRow[]>([])
const loading = ref(false)
const error = ref('')
const searchInput = ref<HTMLInputElement | null>(null)
let debounceTimer: ReturnType<typeof setTimeout> | null = null

function stageFor(client: ClientRow) {
  if (client.training_interest === 'pit_stop') return client.pit_stop_stage_display
  if (client.training_interest === 'citybuild') return client.citybuild_stage_display
  return ''
}

function currentQuery() {
  const next: Record<string, string> = {}
  if (program.value) next.program = program.value
  if ((program.value === 'pit_stop' || program.value === 'citybuild') && stage.value) {
    next.stage = stage.value
  }
  if (searchQuery.value.trim()) next.q = searchQuery.value.trim()
  return next
}

function writeFilters() {
  router.replace({ name: 'Clients', query: currentQuery() })
}

function setProgram(value: string) {
  program.value = program.value === value ? '' : value
  if (program.value !== 'pit_stop' && program.value !== 'citybuild') stage.value = ''
  writeFilters()
}

function setStage(value: string) {
  stage.value = stage.value === value ? '' : value
  writeFilters()
}

async function search() {
  loading.value = true
  error.value = ''
  try {
    const params = new URLSearchParams()
    if (searchQuery.value.trim()) params.set('q', searchQuery.value.trim())
    if (program.value) params.set('program', program.value)
    if (stage.value) params.set('stage', stage.value)
    const resp = await staffFetch(`/api/staff/clients/?${params.toString()}`)
    const body = await resp.json().catch(() => null)
    if (!resp.ok) {
      error.value = friendlyError(body, 'Could not load clients.')
      return
    }
    clients.value = body
  } catch (e) {
    error.value = networkErrorMessage(e)
  } finally {
    loading.value = false
  }
}

function debouncedSearch() {
  if (debounceTimer) clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => {
    writeFilters()
  }, 250)
}

function applyRouteFilters() {
  const qProgram = String(route.query.program || '')
  program.value = qProgram
  const qStage = String(route.query.stage || '')
  stage.value = qProgram === 'pit_stop' || qProgram === 'citybuild' ? qStage : ''
  searchQuery.value = String(route.query.q || '')
}

onMounted(() => {
  searchInput.value?.focus()
})

watch(
  () => [route.query.program, route.query.stage, route.query.q],
  () => {
    applyRouteFilters()
    search()
  },
  { immediate: true },
)
</script>
