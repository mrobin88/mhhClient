<template>
  <section class="space-y-3">
    <div class="staff-card p-4">
      <div class="staff-panel-header">
        <span class="material-symbols-outlined" aria-hidden="true">group</span>
        <h3>Find a client</h3>
        <StaffTip text="Search by name or phone, then tap the person. On their page you can fix contact info and sign them up for Orientation or JRT." />
      </div>
      <input
        v-model="query"
        type="search"
        placeholder="Name or phone"
        class="staff-input"
        @input="debouncedSearch"
      />

      <div class="mt-3">
        <p class="text-xs font-semibold uppercase tracking-wider text-stone-500 mb-1.5">
          Program
          <StaffTip text="Show only people signed up for one program. Tap the same chip again to clear it." />
        </p>
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

      <div v-if="program === 'pit_stop'" class="mt-3">
        <p class="text-xs font-semibold uppercase tracking-wider text-stone-500 mb-1.5">
          Pit Stop stage
          <StaffTip text="Applicants signed up but are not accepted yet. Workers have a portal login and can clock in." />
        </p>
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
    </div>

    <SkeletonClientList v-if="loading" />
    <div v-else-if="error" class="staff-card p-4 text-center space-y-3">
      <p class="text-sm text-stone-600">{{ error }}</p>
      <button type="button" class="staff-btn staff-btn-secondary" @click="search">Try again</button>
    </div>
    <p v-else-if="clients.length === 0" class="text-sm text-stone-500 text-center py-8">No clients found.</p>

    <ul v-else class="space-y-2">
      <li v-for="client in clients" :key="client.id">
        <button
          type="button"
          class="staff-card w-full text-left px-4 py-3 hover:border-orange-300 transition-colors"
          @click="router.push({ name: 'ClientDetail', params: { id: client.id } })"
        >
          <p class="font-semibold">{{ client.full_name }}</p>
          <p class="text-sm text-stone-600">{{ client.phone }} · {{ client.status }}</p>
          <p class="text-xs text-stone-500 mt-0.5">
            {{ client.training_interest_display }}
            <template v-if="client.training_interest === 'pit_stop'">
              · {{ client.pit_stop_stage_display }}
            </template>
          </p>
        </button>
      </li>
    </ul>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { staffFetch } from '../api'
import { friendlyError, networkErrorMessage } from '../utils/errors'
import SkeletonClientList from './SkeletonClientList.vue'
import StaffTip from './StaffTip.vue'

interface ClientRow {
  id: number
  full_name: string
  phone: string
  status: string
  training_interest: string
  training_interest_display: string
  pit_stop_stage: string
  pit_stop_stage_display: string
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

const router = useRouter()
const query = ref('')
const program = ref('')
const stage = ref('')
const clients = ref<ClientRow[]>([])
const loading = ref(false)
const error = ref('')
let debounceTimer: ReturnType<typeof setTimeout> | null = null

function setProgram(value: string) {
  program.value = program.value === value ? '' : value
  if (program.value !== 'pit_stop') stage.value = ''
  search()
}

function setStage(value: string) {
  stage.value = stage.value === value ? '' : value
  search()
}

async function search() {
  loading.value = true
  error.value = ''
  try {
    const params = new URLSearchParams()
    if (query.value.trim()) params.set('q', query.value.trim())
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
  debounceTimer = setTimeout(search, 250)
}

onMounted(search)
</script>
