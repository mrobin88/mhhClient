<template>
  <div class="worker-portal h-[100dvh] bg-slate-50 text-slate-900 antialiased flex flex-col overflow-hidden">
    <WorkerLogin v-if="!isAuthenticated" @login-success="handleLoginSuccess" />

    <template v-else>
      <header class="bg-white border-b border-slate-200 shrink-0">
        <div class="max-w-md mx-auto px-3 pt-2 pb-1.5 flex items-center justify-between gap-2">
          <div class="min-w-0">
            <h1 class="text-sm font-semibold text-slate-900 leading-tight">PitStop Worker</h1>
            <p class="text-[11px] text-slate-500 truncate">{{ workerName }}</p>
          </div>
          <button
            type="button"
            class="shrink-0 text-[11px] font-semibold text-slate-600 hover:text-slate-900 py-1 px-2 rounded-md hover:bg-slate-100"
            @click="logout"
          >
            Sign out
          </button>
        </div>
        <nav class="max-w-md mx-auto flex items-center gap-1 px-2 pb-1.5" aria-label="Main">
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
            @click="tab = 'profile'"
            :class="tab === 'profile' ? tabActive : tabIdle"
          >
            <UserCircleIcon class="w-3.5 h-3.5" aria-hidden="true" />
            Profile
          </button>
        </nav>
      </header>

      <main class="max-w-md w-full mx-auto px-3 py-2 flex-1 overflow-y-auto">
        <WorkerAssignments v-if="tab === 'assignments'" />
        <WorkerProfile v-else />
      </main>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import {
  BriefcaseIcon,
  UserCircleIcon,
} from '@heroicons/vue/24/outline'
import { workerFetch } from './api'
import WorkerLogin from './components/WorkerLogin.vue'
import WorkerAssignments from './components/WorkerAssignments.vue'
import WorkerProfile from './components/WorkerProfile.vue'

const isAuthenticated = ref(false)
const workerAccount = ref<Record<string, unknown> | null>(null)
const tab = ref<'assignments' | 'profile'>('assignments')

const tabActive =
  'flex-1 min-w-0 inline-flex items-center justify-center gap-1 rounded-md border border-teal-700 bg-teal-50 px-2 py-1 text-[11px] font-bold text-teal-900'
const tabIdle =
  'flex-1 min-w-0 inline-flex items-center justify-center gap-1 rounded-md border border-transparent px-2 py-1 text-[11px] font-semibold text-slate-600 hover:bg-slate-100 hover:text-slate-950'

const workerName = computed(() => {
  const n = workerAccount.value?.client_name
  return typeof n === 'string' ? n : 'Worker'
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
