<template>
  <section class="staff-card p-4">
    <div class="staff-panel-header">
      <span class="material-symbols-outlined" aria-hidden="true">event</span>
      <h3>Upcoming Classes &amp; Trainings</h3>
      <StaffTip text="Tap a class for the name list, mark who is here, or print a roster for notes." />
      <RouterLink
        to="/classes"
        class="text-xs font-semibold staff-link shrink-0"
      >
        Manage →
      </RouterLink>
    </div>

    <CardSkeleton v-if="loading" variant="list" :count="4" />
    <p v-else-if="error" class="text-sm text-stone-500">{{ error }}</p>
    <p v-else-if="sessions.length === 0" class="text-sm text-stone-500">
      No upcoming sessions yet.
      <RouterLink to="/classes" class="staff-link font-semibold">Add your first class →</RouterLink>
    </p>

    <div v-else class="staff-upcoming-programs staff-fade-in">
      <section
        v-for="group in programGroups"
        :key="group.value"
        class="staff-upcoming-program"
      >
        <h4 class="staff-upcoming-program-title">
          {{ group.label }}
          <span>{{ group.sessions.length }}</span>
        </h4>
        <ul class="space-y-1">
          <li v-for="s in group.sessions" :key="s.id" class="border-t border-stone-100 pt-2 first:border-0 first:pt-0">
            <button
              type="button"
              class="w-full flex items-center justify-between gap-2 text-left"
              @click="toggleRoster(s.id)"
            >
              <span class="min-w-0">
                <span class="block text-sm font-semibold truncate">{{ s.template_name }}</span>
                <span class="block text-xs text-stone-500">
                  {{ formatSessionDate(s.session_date) }} ·
                  {{ formatTimeRange(s.start_time, s.end_time) }}
                </span>
              </span>
              <span class="flex flex-col items-end gap-0.5 shrink-0">
                <span
                  class="text-[10px] uppercase font-bold tracking-wide rounded-full px-2 py-0.5"
                  :class="s.spots_remaining > 0 ? 'bg-emerald-100 text-emerald-700' : 'bg-stone-200 text-stone-600'"
                >
                  {{ s.spots_remaining > 0 ? `${s.spots_remaining} open` : 'full' }}
                </span>
                <span v-if="s.enrolled_count" class="text-[10px] text-stone-500">
                  {{ s.enrolled_count }} signed up
                </span>
              </span>
            </button>

            <div v-if="expandedId === s.id" class="mt-2">
              <ClassRosterPanel
                :session-id="s.id"
                :session-name="s.template_name"
                :session-date="s.session_date"
                :start-time="s.start_time"
                :end-time="s.end_time"
                :program-label="s.program_display"
                session-status="scheduled"
                @changed="load"
                @cancelled="onCancelled(s.id)"
                @deleted="onDeleted(s.id)"
              />
            </div>
          </li>
        </ul>
      </section>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { staffFetch } from '../../api'
import CardSkeleton from './CardSkeleton.vue'
import ClassRosterPanel from '../ClassRosterPanel.vue'
import StaffTip from '../StaffTip.vue'

const PROGRAM_COLUMNS = [
  { value: 'citybuild', label: 'City Build' },
  { value: 'pit_stop', label: 'Pit Stop' },
  { value: 'capsa', label: 'CAPSA' },
  { value: 'guard_card', label: 'Guard Card' },
  { value: 'general', label: 'General' },
]

interface UpcomingSession {
  id: number
  template_name: string
  program: string
  program_display: string
  category_display: string
  session_date: string
  start_time: string
  end_time: string
  spots_remaining: number
  enrolled_count: number
  confirmed_count: number
}

const sessions = ref<UpcomingSession[]>([])
const loading = ref(true)
const error = ref('')
const expandedId = ref<number | null>(null)

const knownPrograms = new Set(PROGRAM_COLUMNS.map((col) => col.value))
const programGroups = computed(() => {
  const groups = PROGRAM_COLUMNS.map((col) => ({
    ...col,
    sessions: sessions.value.filter((s) => s.program === col.value),
  })).filter((group) => group.sessions.length > 0)
  const leftover = sessions.value.filter((s) => !knownPrograms.has(s.program))
  if (leftover.length) {
    groups.push({
      value: leftover[0].program || 'other',
      label: leftover[0].program_display || 'Other',
      sessions: leftover,
    })
  }
  return groups
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
    sessions.value = body.results || []
  } catch {
    error.value = 'No connection.'
  } finally {
    loading.value = false
  }
}

function toggleRoster(sessionId: number) {
  expandedId.value = expandedId.value === sessionId ? null : sessionId
}

function onCancelled(sessionId: number) {
  expandedId.value = null
  sessions.value = sessions.value.filter((s) => s.id !== sessionId)
  load()
}

function onDeleted(sessionId: number) {
  sessions.value = sessions.value.filter((s) => s.id !== sessionId)
  expandedId.value = null
}

load()
</script>
