<template>
  <div class="min-h-screen bg-slate-50 text-slate-900 antialiased">
    <WorkerLogin v-if="!isAuthenticated" @login-success="handleLoginSuccess" />

    <template v-else>
      <header class="sticky top-0 z-20 bg-white border-b border-slate-200 shadow-sm">
        <div class="max-w-lg mx-auto px-4 pt-4 pb-2 flex items-start justify-between gap-3">
          <div class="min-w-0">
            <h1 class="text-lg font-semibold text-slate-900 leading-tight">Open shifts</h1>
            <p class="text-sm text-slate-500 truncate mt-0.5">{{ workerName }}</p>
          </div>
          <button
            type="button"
            class="shrink-0 text-sm font-semibold text-teal-700 hover:text-teal-800 py-1.5 px-2 rounded-lg hover:bg-teal-50"
            @click="logout"
          >
            Sign out
          </button>
        </div>
        <nav class="max-w-lg mx-auto flex px-2 pb-0" aria-label="Main">
          <button
            type="button"
            @click="tab = 'open'"
            :class="tab === 'open' ? tabActive : tabIdle"
          >
            <BriefcaseIcon class="w-5 h-5 mb-1" aria-hidden="true" />
            Shifts open
          </button>
          <button
            type="button"
            @click="tab = 'mine'"
            :class="tab === 'mine' ? tabActive : tabIdle"
          >
            <ClipboardDocumentListIcon class="w-5 h-5 mb-1" aria-hidden="true" />
            My requests
          </button>
        </nav>
      </header>

      <main class="max-w-lg mx-auto px-4 py-5 pb-28">
        <WorkerOpenShifts v-if="tab === 'open'" @interest-recorded="onInterestRecorded" />
        <WorkerMyRequests v-else :key="myRequestsKey" />
      </main>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { BriefcaseIcon, ClipboardDocumentListIcon } from '@heroicons/vue/24/outline'
import { workerFetch } from './api'
import WorkerLogin from './components/WorkerLogin.vue'
import WorkerOpenShifts from './components/WorkerOpenShifts.vue'
import WorkerMyRequests from './components/WorkerMyRequests.vue'

const isAuthenticated = ref(false)
const workerAccount = ref<Record<string, unknown> | null>(null)
const tab = ref<'open' | 'mine'>('open')
const myRequestsKey = ref(0)

const tabActive =
  'flex-1 flex flex-col items-center py-3 text-xs font-semibold text-teal-700 border-b-2 border-teal-600'
const tabIdle =
  'flex-1 flex flex-col items-center py-3 text-xs font-semibold text-slate-500 border-b-2 border-transparent hover:text-slate-700'

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
