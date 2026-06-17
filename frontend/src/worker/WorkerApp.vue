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
        <nav class="max-w-md mx-auto flex items-center gap-1 px-2 py-2" aria-label="Main">
          <button
            type="button"
            @click="tab = 'assignments'"
            :class="tab === 'assignments' ? tabActive : tabIdle"
          >
            <BriefcaseIcon class="w-3.5 h-3.5" aria-hidden="true" />
            Clock
          </button>
          <button
            type="button"
            @click="tab = 'incident'"
            :class="tab === 'incident' ? tabActive : tabIdle"
          >
            <ExclamationTriangleIcon class="w-3.5 h-3.5" aria-hidden="true" />
            Incident
          </button>
          <button
            type="button"
            @click="tab = 'profile'"
            :class="tab === 'profile' ? tabActive : tabIdle"
          >
            <UserCircleIcon class="w-3.5 h-3.5" aria-hidden="true" />
            Profile
          </button>
        </nav>
      </header>

      <main class="max-w-md w-full mx-auto px-3 py-3 flex-1 overflow-y-auto">
        <WorkerAssignments v-if="tab === 'assignments'" />
        <WorkerIncidentReport v-else-if="tab === 'incident'" />
        <WorkerProfile v-else />
      </main>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import {
  BriefcaseIcon,
  ExclamationTriangleIcon,
  UserCircleIcon,
} from '@heroicons/vue/24/outline'
import { workerFetch } from './api'
import WorkerLogin from './components/WorkerLogin.vue'
import WorkerAssignments from './components/WorkerAssignments.vue'
import WorkerIncidentReport from './components/WorkerIncidentReport.vue'
import WorkerProfile from './components/WorkerProfile.vue'

const isAuthenticated = ref(false)
const workerAccount = ref<Record<string, unknown> | null>(null)
const tab = ref<'assignments' | 'incident' | 'profile'>('assignments')

const tabActive =
  'flex-1 min-w-0 inline-flex items-center justify-center gap-1 rounded-md border border-emerald-400/70 bg-emerald-500/20 px-2 py-1.5 text-[11px] font-bold text-emerald-200'
const tabIdle =
  'flex-1 min-w-0 inline-flex items-center justify-center gap-1 rounded-md border border-slate-700/70 bg-slate-900 px-2 py-1.5 text-[11px] font-semibold text-slate-300 hover:bg-slate-800 hover:text-white'

const workerName = computed(() => {
  const n = workerAccount.value?.client_name
  return typeof n === 'string' ? n : 'Worker'
})

const tickerItems = computed(() => {
  const now = new Date()
  const minute = String(now.getMinutes()).padStart(2, '0')
  const hour = now.getHours()
  return [
    `SHIFT CLOCK ${tab.value === 'assignments' ? 'OPEN' : 'READY'} +1.7%`,
    `LUNCH WINDOW TRACKED • ${hour}:${minute}`,
    'INCIDENT LINE LIVE • SUPERVISOR + DETAILS',
    'LOCATION SERVICES REQUIRED • VERIFIED',
  ]
})

function handleLoginSuccess(data: { token: string; worker_account: Record<string, unknown> }) {
  isAuthenticated.value = true
  workerAccount.value = data.worker_account
  localStorage.setItem('worker_token', data.token)
  localStorage.setItem('worker_account', JSON.stringify(data.worker_account))
  tab.value = 'assignments'
}

function resetToLogin() {
  localStorage.removeItem('worker_token')
  localStorage.removeItem('worker_account')
  isAuthenticated.value = false
  workerAccount.value = null
  tab.value = 'assignments'
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
})
</script>
