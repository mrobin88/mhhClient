<template>
  <div class="worker-portal min-h-screen bg-slate-50 text-slate-900 antialiased">
    <WorkerLogin v-if="!isAuthenticated" @login-success="handleLoginSuccess" />

    <template v-else>
      <header class="sticky top-0 z-20 bg-white border-b border-slate-200 shadow-sm">
        <div class="max-w-lg mx-auto px-4 pt-4 pb-3 flex items-start justify-between gap-3">
          <div class="min-w-0">
            <h1 class="text-lg font-semibold text-slate-900 leading-tight">PitStop Coverage Board</h1>
            <p class="text-sm text-slate-500 truncate mt-0.5">{{ workerName }}</p>
          </div>
          <button
            type="button"
            class="shrink-0 text-sm font-semibold text-slate-700 hover:text-slate-950 py-1.5 px-2 rounded-lg hover:bg-slate-100"
            @click="logout"
          >
            Sign out
          </button>
        </div>
        <nav class="max-w-lg mx-auto flex items-center gap-1 px-3 pb-2" aria-label="Main">
          <button
            type="button"
            @click="tab = 'open'"
            :class="tab === 'open' ? tabActive : tabIdle"
          >
            <BriefcaseIcon class="w-4 h-4" aria-hidden="true" />
            Coverage
          </button>
          <button
            type="button"
            @click="tab = 'mine'"
            :class="tab === 'mine' ? tabActive : tabIdle"
          >
            <ClipboardDocumentListIcon class="w-4 h-4" aria-hidden="true" />
            Responses
          </button>
          <button
            type="button"
            @click="tab = 'notes'"
            :class="tab === 'notes' ? tabActive : tabIdle"
          >
            <DocumentTextIcon class="w-4 h-4" aria-hidden="true" />
            Notes
          </button>
          <button
            type="button"
            @click="tab = 'timeOff'"
            :class="tab === 'timeOff' ? tabActive : tabIdle"
          >
            <CalendarDaysIcon class="w-4 h-4" aria-hidden="true" />
            Time off
          </button>
        </nav>
      </header>

      <main class="max-w-lg mx-auto px-4 py-5 pb-28">
        <WorkerTimeClock class="mb-4" />
        <WorkerOpenShifts v-if="tab === 'open'" @interest-recorded="onInterestRecorded" />
        <WorkerMyRequests v-else-if="tab === 'mine'" :key="myRequestsKey" />
        <WorkerNotes v-else-if="tab === 'notes'" />
        <WorkerTimeOffRequests v-else />
      </main>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import {
  BriefcaseIcon,
  ClipboardDocumentListIcon,
  DocumentTextIcon,
  CalendarDaysIcon,
} from '@heroicons/vue/24/outline'
import { workerFetch } from './api'
import WorkerLogin from './components/WorkerLogin.vue'
import WorkerOpenShifts from './components/WorkerOpenShifts.vue'
import WorkerMyRequests from './components/WorkerMyRequests.vue'
import WorkerTimeClock from './components/WorkerTimeClock.vue'
import WorkerNotes from './components/WorkerNotes.vue'
import WorkerTimeOffRequests from './components/WorkerTimeOffRequests.vue'

const isAuthenticated = ref(false)
const workerAccount = ref<Record<string, unknown> | null>(null)
const tab = ref<'open' | 'mine' | 'notes' | 'timeOff'>('open')
const myRequestsKey = ref(0)

const tabActive =
  'flex-1 min-w-0 inline-flex items-center justify-center gap-1 rounded-lg border border-teal-700 bg-teal-50 px-2 py-1.5 text-[11px] font-bold text-teal-900'
const tabIdle =
  'flex-1 min-w-0 inline-flex items-center justify-center gap-1 rounded-lg border border-transparent px-2 py-1.5 text-[11px] font-semibold text-slate-600 hover:bg-slate-100 hover:text-slate-950'

const workerName = computed(() => {
  const n = workerAccount.value?.client_name
  return typeof n === 'string' ? n : 'Worker'
})

function handleLoginSuccess(data: { token: string; worker_account: Record<string, unknown> }) {
  isAuthenticated.value = true
  workerAccount.value = data.worker_account
  localStorage.setItem('worker_token', data.token)
  localStorage.setItem('worker_account', JSON.stringify(data.worker_account))
  tab.value = 'open'
}

function onInterestRecorded() {
  myRequestsKey.value += 1
  tab.value = 'mine'
}

function resetToLogin() {
  localStorage.removeItem('worker_token')
  localStorage.removeItem('worker_account')
  isAuthenticated.value = false
  workerAccount.value = null
  tab.value = 'open'
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
