<template>
  <div class="worker-portal h-[100dvh] antialiased flex flex-col overflow-hidden">
    <WorkerLogin v-if="!isAuthenticated" @login-success="handleLoginSuccess" />

    <template v-else>
      <header class="worker-topbar shrink-0">
        <div class="max-w-md mx-auto px-3 pt-2 pb-2 flex items-center justify-between gap-2">
          <div class="min-w-0">
            <p class="worker-kicker">PitStop Worker Market</p>
            <h1 class="text-sm font-semibold text-white leading-tight">Shift Desk</h1>
            <p class="text-[11px] text-slate-400 truncate">{{ workerName }}</p>
          </div>
          <button
            type="button"
            class="worker-ghost-btn"
            @click="logout"
          >
            Sign out
          </button>
        </div>
        <div class="worker-ticker-shell">
          <div class="worker-ticker-track">
            <span v-for="(item, idx) in tickerItems" :key="`${idx}-${item}`" class="worker-ticker-item">
              {{ item }}
            </span>
          </div>
        </div>
        <nav class="worker-nav max-w-md mx-auto px-2 py-2" aria-label="Main">
          <button
            v-for="item in navItems"
            :key="item.key"
            type="button"
            class="worker-nav-btn"
            :class="tab === item.key ? 'worker-nav-btn-active' : 'worker-nav-btn-idle'"
            @click="tab = item.key"
          >
            {{ item.label }}
          </button>
        </nav>
      </header>

      <main class="max-w-md w-full mx-auto px-3 py-3 flex-1 overflow-y-auto">
        <WorkerAssignments v-if="tab === 'assignments'" />
        <WorkerFeedback v-else-if="tab === 'feedback'" />
        <WorkerIncidentReport v-else-if="tab === 'incident'" />
        <WorkerProfile v-else-if="tab === 'profile'" />
      </main>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { workerFetch } from './api'
import WorkerLogin from './components/WorkerLogin.vue'
import WorkerAssignments from './components/WorkerAssignments.vue'
import WorkerFeedback from './components/WorkerFeedback.vue'
import WorkerIncidentReport from './components/WorkerIncidentReport.vue'
import WorkerProfile from './components/WorkerProfile.vue'

type WorkerTab = 'assignments' | 'feedback' | 'incident' | 'profile'

interface WorkerDashboardSummary {
  is_clocked_in: boolean
  incident_reports_today: number
  incident_reports_week: number
  last_incident_at: string | null
  has_feedback_today: boolean
}

const isAuthenticated = ref(false)
const workerAccount = ref<Record<string, unknown> | null>(null)
const tab = ref<WorkerTab>('assignments')
const dashboardSummary = ref<WorkerDashboardSummary | null>(null)
let summaryTimer: ReturnType<typeof setInterval> | null = null

const navItems: Array<{ key: WorkerTab; label: string }> = [
  { key: 'assignments', label: 'Clock' },
  { key: 'feedback', label: 'Feedback' },
  { key: 'incident', label: 'Incident' },
  { key: 'profile', label: 'Profile' },
]

const workerName = computed(() => {
  const n = workerAccount.value?.client_name
  return typeof n === 'string' ? n : 'Worker'
})

function formatTimeOnly(iso: string | null) {
  if (!iso) return 'none'
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return 'none'
  return date.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })
}

const tickerItems = computed(() => {
  const now = new Date()
  const summary = dashboardSummary.value
  const localTime = now.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })
  return [
    `Clock ${summary?.is_clocked_in ? 'IN' : 'OUT'} • ${localTime}`,
    `Incidents today ${summary?.incident_reports_today ?? 0} • week ${summary?.incident_reports_week ?? 0}`,
    `Last incident ${formatTimeOnly(summary?.last_incident_at || null)}`,
    `Daily feedback ${summary?.has_feedback_today ? 'submitted' : 'pending'}`,
  ]
})

async function loadDashboardSummary() {
  if (!localStorage.getItem('worker_token')) return
  try {
    const resp = await workerFetch('/api/worker/dashboard-summary/')
    if (!resp.ok) return
    const body = await resp.json().catch(() => null)
    if (!body) return
    dashboardSummary.value = {
      is_clocked_in: Boolean(body.is_clocked_in),
      incident_reports_today: Number(body.incident_reports_today) || 0,
      incident_reports_week: Number(body.incident_reports_week) || 0,
      last_incident_at: typeof body.last_incident_at === 'string' ? body.last_incident_at : null,
      has_feedback_today: Boolean(body.has_feedback_today),
    }
  } catch {
    /* keep current ticker values */
  }
}

function startSummaryPolling() {
  if (summaryTimer) clearInterval(summaryTimer)
  summaryTimer = setInterval(() => {
    loadDashboardSummary()
  }, 60_000)
}

function handleLoginSuccess(data: { token: string; worker_account: Record<string, unknown> }) {
  isAuthenticated.value = true
  workerAccount.value = data.worker_account
  localStorage.setItem('worker_token', data.token)
  localStorage.setItem('worker_account', JSON.stringify(data.worker_account))
  tab.value = 'assignments'
  loadDashboardSummary()
  startSummaryPolling()
}

function resetToLogin() {
  localStorage.removeItem('worker_token')
  localStorage.removeItem('worker_account')
  isAuthenticated.value = false
  workerAccount.value = null
  tab.value = 'assignments'
  dashboardSummary.value = null
  if (summaryTimer) {
    clearInterval(summaryTimer)
    summaryTimer = null
  }
}

function logout() {
  if (localStorage.getItem('worker_token')) {
    workerFetch('/api/worker/logout/', { method: 'POST' })
  }
  resetToLogin()
}

async function validateExistingSession() {
  const token = localStorage.getItem('worker_token')
  const savedAccount = localStorage.getItem('worker_account')
  if (!token || !savedAccount) return

  isAuthenticated.value = true
  try {
    workerAccount.value = JSON.parse(savedAccount)
  } catch {
    resetToLogin()
    return
  }

  try {
    const resp = await workerFetch('/api/worker/profile/')
    if (!resp.ok) {
      resetToLogin()
      return
    }
    const profile = await resp.json()
    workerAccount.value = profile
    localStorage.setItem('worker_account', JSON.stringify(profile))
    await loadDashboardSummary()
    startSummaryPolling()
  } catch {
    /* offline: keep optimistic session */
  }
}

function onSessionExpired() {
  resetToLogin()
}

onMounted(() => {
  window.addEventListener('worker-session-expired', onSessionExpired)
  validateExistingSession()
})

onBeforeUnmount(() => {
  window.removeEventListener('worker-session-expired', onSessionExpired)
  if (summaryTimer) clearInterval(summaryTimer)
})
</script>
