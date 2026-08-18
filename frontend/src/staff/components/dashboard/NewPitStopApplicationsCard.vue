<template>
  <section class="staff-card p-4">
    <div class="staff-panel-header">
      <span class="material-symbols-outlined" aria-hidden="true">person_search</span>
      <h3>New Pit Stop applications</h3>
      <StaffTip text="People waiting for their first review. Open a name to see the application summary. Use Admin for the interview decision and review notes." />
      <a
        :href="adminUrl"
        target="_blank"
        rel="noopener"
        class="text-xs font-semibold text-orange-600 shrink-0"
      >
        Review all →
      </a>
    </div>

    <CardSkeleton v-if="loading" variant="list" :count="4" />
    <p v-else-if="error" class="text-sm text-stone-500">{{ error }}</p>
    <p v-else-if="applications.length === 0" class="text-sm text-emerald-700 font-semibold">
      No new applications waiting.
    </p>
    <template v-else>
      <p class="text-xs text-stone-500 mb-2">
        {{ totalNew }} waiting for review. Resume and date of birth are now required online.
      </p>
      <ul class="space-y-2 staff-fade-in">
        <li v-for="app in applications" :key="app.id">
          <RouterLink
            :to="{ name: 'ClientDetail', params: { id: app.client_id }, query: { focus: 'pitstop' } }"
            class="flex items-center justify-between gap-2 border-t border-stone-100 pt-2 first:border-0 first:pt-0"
          >
            <span class="min-w-0">
              <span class="block text-sm font-semibold truncate">{{ app.full_name }}</span>
              <span class="block text-xs text-stone-500">
                Age {{ app.age ?? 'unknown' }} · {{ app.area_code || 'no area code' }} ·
                {{ app.open_availability ? 'open availability' : 'limited availability' }}
              </span>
            </span>
            <span
              class="text-[10px] uppercase font-bold tracking-wide rounded-full px-2 py-0.5 shrink-0"
              :class="app.has_resume ? 'bg-emerald-100 text-emerald-700' : 'bg-red-100 text-red-700'"
            >
              {{ app.has_resume ? 'resume' : 'missing resume' }}
            </span>
          </RouterLink>
        </li>
      </ul>
    </template>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { getApiUrl } from '../../../config/api'
import { staffFetch } from '../../api'
import CardSkeleton from './CardSkeleton.vue'
import StaffTip from '../StaffTip.vue'

interface NewPitStopApplication {
  id: number
  client_id: number
  full_name: string
  age: number | null
  area_code: string
  has_resume: boolean
  open_availability: boolean
}

const applications = ref<NewPitStopApplication[]>([])
const totalNew = ref(0)
const loading = ref(true)
const error = ref('')
const adminUrl = getApiUrl('/admin/clients/pitstopapplication/')

async function load() {
  try {
    const resp = await staffFetch('/api/staff/dashboard/new-pitstop-applications/?limit=5')
    if (!resp.ok) {
      error.value = 'Could not load Pit Stop applications.'
      return
    }
    const body = await resp.json()
    applications.value = body.results || []
    totalNew.value = Number(body.total_new) || 0
  } catch {
    error.value = 'No connection.'
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>
