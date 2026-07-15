<template>
  <section class="staff-card p-4">
    <div class="staff-panel-header">
      <span class="material-symbols-outlined" aria-hidden="true">event</span>
      <h3>Upcoming Classes &amp; Trainings</h3>
      <RouterLink
        to="/classes"
        class="text-xs font-semibold text-orange-600 shrink-0"
      >
        Manage →
      </RouterLink>
    </div>

    <CardSkeleton v-if="loading" variant="list" :count="4" />
    <p v-else-if="error" class="text-sm text-stone-500">{{ error }}</p>
    <p v-else-if="sessions.length === 0" class="text-sm text-stone-500">
      No upcoming sessions yet.
      <RouterLink to="/classes" class="text-orange-600 font-semibold">Add your first class →</RouterLink>
    </p>

    <ul v-else class="space-y-1 staff-fade-in">
      <li v-for="s in sessions" :key="s.id" class="border-t border-stone-100 pt-2 first:border-0 first:pt-0">
        <button
          type="button"
          class="w-full flex items-center justify-between gap-2 text-left"
          @click="toggleRoster(s.id)"
        >
          <span class="min-w-0">
            <span class="block text-sm font-semibold truncate">{{ s.template_name }}</span>
            <span class="block text-xs text-stone-500">
              {{ s.category_display }} · {{ formatSessionDate(s.session_date) }} ·
              {{ formatTimeRange(s.start_time, s.end_time) }}
            </span>
          </span>
          <span
            class="text-[10px] uppercase font-bold tracking-wide rounded-full px-2 py-0.5 shrink-0"
            :class="s.spots_remaining > 0 ? 'bg-emerald-100 text-emerald-700' : 'bg-stone-200 text-stone-600'"
          >
            {{ s.spots_remaining > 0 ? `${s.spots_remaining} open` : 'full' }}
          </span>
        </button>

        <div v-if="expandedId === s.id" class="mt-1.5 pl-1 space-y-1">
          <p v-if="rosterLoading" class="text-xs text-stone-500">Loading roster…</p>
          <template v-else>
            <p v-if="roster.length === 0" class="text-xs text-stone-400">No one signed up yet.</p>
            <RouterLink
              v-for="r in roster"
              :key="r.enrollment_id"
              :to="{ name: 'ClientDetail', params: { id: r.client_id } }"
              class="block text-xs text-stone-700 hover:text-orange-600"
            >
              {{ r.client_full_name }} <span class="text-stone-400">· {{ r.status_display }}</span>
            </RouterLink>
          </template>
        </div>
      </li>
    </ul>
  </section>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { RouterLink } from 'vue-router'
import { staffFetch } from '../../api'
import CardSkeleton from './CardSkeleton.vue'

interface UpcomingSession {
  id: number
  template_name: string
  category_display: string
  session_date: string
  start_time: string
  end_time: string
  spots_remaining: number
}

interface RosterEntry {
  enrollment_id: number
  client_id: number
  client_full_name: string
  status_display: string
}

const sessions = ref<UpcomingSession[]>([])
const loading = ref(true)
const error = ref('')

const expandedId = ref<number | null>(null)
const roster = ref<RosterEntry[]>([])
const rosterLoading = ref(false)

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

async function load() {
  loading.value = true
  error.value = ''
  try {
    const resp = await staffFetch('/api/staff/classes/upcoming/?days=30')
    if (!resp.ok) {
      error.value = 'Could not load upcoming classes.'
      return
    }
    const body = await resp.json()
    sessions.value = (body.results || []).slice(0, 8)
  } catch {
    error.value = 'No connection.'
  } finally {
    loading.value = false
  }
}

async function toggleRoster(sessionId: number) {
  if (expandedId.value === sessionId) {
    expandedId.value = null
    return
  }
  expandedId.value = sessionId
  rosterLoading.value = true
  roster.value = []
  try {
    const resp = await staffFetch(`/api/staff/classes/${sessionId}/roster/`)
    if (resp.ok) {
      const body = await resp.json()
      roster.value = body.roster || []
    }
  } finally {
    rosterLoading.value = false
  }
}

load()
</script>
