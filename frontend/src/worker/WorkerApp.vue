<template>
  <div class="min-h-screen bg-slate-100">
    <!-- Navigation Bar -->
    <nav v-if="isAuthenticated" class="bg-gradient-to-r from-blue-700 via-blue-600 to-indigo-700 text-white shadow-md">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3">
        <div class="flex justify-between items-center gap-4">
          <div class="min-w-0 flex-1">
            <p class="text-[10px] sm:text-xs font-semibold uppercase tracking-wider text-blue-200 truncate">
              Mission Hiring Hall · PitStop
            </p>
            <button
              type="button"
              @click="currentView = 'dashboard'"
              class="text-lg sm:text-xl font-bold hover:text-blue-100 transition text-left truncate block w-full"
            >
              Worker hub
            </button>
          </div>
          <div class="flex items-center gap-2 sm:gap-3 shrink-0">
            <span class="text-xs sm:text-sm font-medium text-right max-w-[140px] sm:max-w-[200px] truncate" :title="workerName">{{ workerName }}</span>
            <button
              type="button"
              @click="logout"
              class="bg-white/15 hover:bg-white/25 border border-white/30 px-3 py-2 rounded-lg text-xs sm:text-sm font-semibold transition"
            >
              Log out
            </button>
          </div>
        </div>
      </div>
    </nav>

    <!-- Bottom Navigation (All screens) -->
    <div v-if="isAuthenticated" class="fixed bottom-0 left-0 right-0 bg-white/95 backdrop-blur border-t border-slate-200 z-50 shadow-[0_-4px_20px_rgba(0,0,0,0.06)]">
      <div class="flex justify-around max-w-lg mx-auto">
        <button
          v-for="item in navItems"
          :key="item.id"
          type="button"
          @click="currentView = item.id"
          :class="[
            'flex-1 py-3 sm:py-4 text-center transition-all',
            currentView === item.id
              ? 'text-blue-600'
              : 'text-slate-600 hover:text-slate-900'
          ]"
        >
          <div
            :class="[
              'text-2xl sm:text-3xl mb-0.5',
              currentView === item.id ? 'scale-110' : ''
            ]"
          >{{ item.icon }}</div>
          <div
            :class="[
              'text-[10px] sm:text-xs font-bold uppercase tracking-wide',
              currentView === item.id ? 'text-blue-600' : 'text-slate-500'
            ]"
          >{{ item.label }}</div>
          <div
            v-if="currentView === item.id"
            class="h-0.5 w-8 mx-auto mt-1 rounded-full bg-blue-600"
          />
        </button>
      </div>
    </div>

    <!-- Main Content Area -->
    <div class="pb-20">
      <div class="max-w-3xl mx-auto px-4 py-4">
        <!-- Quick actions (ONLY on dashboard) -->
        <div v-if="isAuthenticated && currentView === 'dashboard'" class="mb-6 grid grid-cols-3 gap-2 sm:gap-3">
          <button
            type="button"
            @click="currentView = 'assignments'"
            class="bg-white border border-slate-200 shadow-sm hover:border-blue-400 hover:shadow rounded-xl p-3 sm:p-4 transition-all text-center"
          >
            <div class="text-2xl sm:text-3xl mb-1">📋</div>
            <div class="text-xs sm:text-sm font-bold text-slate-900">Shifts</div>
          </button>
          <button
            type="button"
            @click="currentView = 'availability'"
            class="bg-white border border-slate-200 shadow-sm hover:border-blue-400 hover:shadow rounded-xl p-3 sm:p-4 transition-all text-center"
          >
            <div class="text-2xl sm:text-3xl mb-1">📅</div>
            <div class="text-xs sm:text-sm font-bold text-slate-900">When I’m free</div>
          </button>
          <button
            type="button"
            @click="currentView = 'requests'"
            class="bg-white border border-slate-200 shadow-sm hover:border-blue-400 hover:shadow rounded-xl p-3 sm:p-4 transition-all text-center"
          >
            <div class="text-2xl sm:text-3xl mb-1">🔧</div>
            <div class="text-xs sm:text-sm font-bold text-slate-900">Site help</div>
          </button>
        </div>

        <!-- Login View -->
        <WorkerLogin 
          v-if="!isAuthenticated" 
          @login-success="handleLoginSuccess"
        />

        <!-- Dashboard -->
        <WorkerDashboard 
          v-else-if="currentView === 'dashboard'"
          :worker-account="workerAccount"
          :cached-data="cachedDashboard"
          @update-cache="updateDashboardCache"
        />

        <!-- My Assignments -->
        <WorkerAssignments 
          v-else-if="currentView === 'assignments'"
        />

        <!-- Availability -->
        <WorkerAvailability 
          v-else-if="currentView === 'availability'"
        />

        <!-- Service Requests -->
        <WorkerServiceRequests 
          v-else-if="currentView === 'requests'"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { workerFetch } from './api'
import WorkerLogin from './components/WorkerLogin.vue'
import WorkerDashboard from './components/WorkerDashboard.vue'
import WorkerAssignments from './components/WorkerAssignments.vue'
import WorkerAvailability from './components/WorkerAvailability.vue'
import WorkerServiceRequests from './components/WorkerServiceRequests.vue'

const isAuthenticated = ref(false)
const workerAccount = ref<any>(null)
const currentView = ref('dashboard')
const cachedDashboard = ref<any>(null)

const navItems = [
  { id: 'dashboard', label: 'Home', icon: '🏠' },
  { id: 'assignments', label: 'Work', icon: '📋' },
  { id: 'availability', label: 'Schedule', icon: '📅' },
  { id: 'requests', label: 'Help', icon: '🔧' }
]

const workerName = computed(() => {
  return workerAccount.value?.client_name || 'Worker'
})

function handleLoginSuccess(data: any) {
  isAuthenticated.value = true
  workerAccount.value = data.worker_account
  localStorage.setItem('worker_token', data.token)
  localStorage.setItem('worker_account', JSON.stringify(data.worker_account))
  
  // Pre-fetch dashboard data after login
  fetchDashboardData()
}

async function fetchDashboardData() {
  try {
    const resp = await workerFetch('/api/worker/dashboard/')
    if (resp.ok) {
      const data = await resp.json()
      cachedDashboard.value = data
      localStorage.setItem('worker_dashboard', JSON.stringify(data))
    }
  } catch (err) {
    console.error('Failed to fetch dashboard:', err)
  }
}

function updateDashboardCache(data: any) {
  cachedDashboard.value = data
  localStorage.setItem('worker_dashboard', JSON.stringify(data))
}

function resetToLogin() {
  localStorage.removeItem('worker_token')
  localStorage.removeItem('worker_account')
  localStorage.removeItem('worker_dashboard')
  isAuthenticated.value = false
  workerAccount.value = null
  cachedDashboard.value = null
  currentView.value = 'dashboard'
}

function logout() {
  // Call logout API
  const token = localStorage.getItem('worker_token')
  if (token) {
    workerFetch('/api/worker/logout/', {
      method: 'POST',
    })
  }
  
  resetToLogin()
}

async function validateExistingSession() {
  const token = localStorage.getItem('worker_token')
  const savedAccount = localStorage.getItem('worker_account')
  if (!token || !savedAccount) return

  // Load cached data immediately
  const cachedDash = localStorage.getItem('worker_dashboard')
  if (cachedDash) {
    try {
      cachedDashboard.value = JSON.parse(cachedDash)
    } catch {
      // Invalid cache, ignore
    }
  }

  // Optimistically show the logged-in UI, but verify with backend.
  isAuthenticated.value = true
  workerAccount.value = JSON.parse(savedAccount)

  try {
    const resp = await workerFetch('/api/worker/profile/')
    if (!resp.ok) {
      resetToLogin()
      return
    }
    const profile = await resp.json()
    workerAccount.value = profile
    localStorage.setItem('worker_account', JSON.stringify(profile))
    
    // Refresh dashboard in background
    fetchDashboardData()
  } catch {
    // If network is down, leave UI as-is; user can refresh
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

<style scoped>
/* Mobile-first responsive styles */
</style>
