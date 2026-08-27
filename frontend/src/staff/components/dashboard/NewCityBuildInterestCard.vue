<template>
  <section class="staff-card p-4">
    <div class="staff-panel-header">
      <span class="material-symbols-outlined" aria-hidden="true">apartment</span>
      <h3>New City Build applications</h3>
      <StaffTip text="People who signed up for City Build and are still in pre-registration. Open a name to update Status & Tracking. Drug-test result is not stored." />
      <RouterLink
        :to="{ name: 'Clients', query: { program: 'citybuild' } }"
        class="text-xs font-semibold staff-link shrink-0"
      >
        Review all →
      </RouterLink>
    </div>

    <CardSkeleton v-if="loading" variant="list" :count="4" />
    <p v-else-if="error" class="text-sm text-stone-500">{{ error }}</p>
    <p v-else-if="applicants.length === 0" class="text-sm text-emerald-700 font-semibold">
      No new applications waiting.
    </p>
    <template v-else>
      <p class="text-xs text-stone-500 mb-2">
        {{ totalInterest }} waiting. Newest signups first.
      </p>
      <ul class="space-y-2 staff-fade-in">
        <li v-for="app in applicants" :key="app.id">
          <RouterLink
            :to="{ name: 'ClientDetail', params: { id: app.client_id }, query: { focus: 'citybuild' } }"
            class="flex items-center justify-between gap-2 border-t border-stone-100 pt-2 first:border-0 first:pt-0"
          >
            <span class="min-w-0">
              <span class="block text-sm font-semibold truncate">{{ app.full_name }}</span>
              <span class="block text-xs text-stone-500">
                {{ app.area_code || 'no area code' }} ·
                {{ app.info_session ? formatSessionDate(app.info_session.session_date) : 'no session yet' }}
                · Staff {{ app.staff_name || '—' }}
              </span>
            </span>
            <span
              class="text-[10px] uppercase font-bold tracking-wide rounded-full px-2 py-0.5 shrink-0"
              :class="stageChipClass(app.citybuild_stage)"
            >
              {{ app.citybuild_stage_display }}
            </span>
          </RouterLink>
        </li>
      </ul>
    </template>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { staffFetch } from '../../api'
import CardSkeleton from './CardSkeleton.vue'
import StaffTip from '../StaffTip.vue'

interface CityBuildInfoSession {
  id: number
  name: string
  session_date: string
  start_time: string
}

interface CityBuildInterest {
  id: number
  client_id: number
  full_name: string
  area_code: string
  staff_name: string
  citybuild_stage: string
  citybuild_stage_display: string
  info_session: CityBuildInfoSession | null
}

const applicants = ref<CityBuildInterest[]>([])
const totalInterest = ref(0)
const loading = ref(true)
const error = ref('')

function formatSessionDate(dateStr: string) {
  const d = new Date(`${dateStr}T00:00:00`)
  if (Number.isNaN(d.getTime())) return dateStr
  return d.toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric' })
}

function stageChipClass(stage: string) {
  if (stage === 'general_interest') return 'bg-amber-100 text-amber-800'
  if (stage === 'accepted') return 'bg-emerald-100 text-emerald-700'
  if (stage === 'waitlisted') return 'bg-stone-200 text-stone-600'
  return 'bg-sky-100 text-sky-800'
}

async function load() {
  try {
    const resp = await staffFetch('/api/staff/dashboard/citybuild-interest/?limit=5')
    if (!resp.ok) {
      error.value = 'Could not load City Build applications.'
      return
    }
    const body = await resp.json()
    applicants.value = body.results || []
    totalInterest.value = Number(body.total_interest) || 0
  } catch {
    error.value = 'No connection.'
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>
