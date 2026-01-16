<template>
  <div class="min-h-screen bg-slate-50">
    <!-- Navigation Bar -->
    <nav v-if="isAuthenticated" class="bg-blue-600 text-white shadow-lg">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="flex justify-between items-center h-16">
          <div class="flex items-center">
            <button @click="currentView = 'dashboard'" class="text-xl font-bold hover:text-blue-100 transition">
              🏢 Worker Portal
            </button>
          </div>
          <div class="flex items-center space-x-4">
            <span class="text-sm font-medium">{{ workerName }}</span>
            <button 
              @click="logout"
              class="bg-blue-700 hover:bg-blue-800 px-4 py-2 rounded-lg text-sm font-medium transition"
            >
              Logout
            </button>
          </div>
        </div>
      </div>
    </nav>

    <!-- Bottom Navigation (All screens) -->
    <div v-if="isAuthenticated" class="fixed bottom-0 left-0 right-0 bg-white border-t-2 border-slate-200 z-50 shadow-xl">
      <div class="flex justify-around">
        <button
          v-for="item in navItems"
          :key="item.id"
          @click="currentView = item.id"
          :class="[
            'flex-1 py-4 text-center transition-all max-w-[200px]',
            currentView === item.id 
              ? 'text-blue-600 bg-blue-50 border-t-4 border-blue-600' 
              : 'text-slate-700 hover:bg-slate-50'
          ]"
        >
          <div class="text-3xl mb-1">{{ item.icon }}</div>
          <div class="text-xs font-semibold">{{ item.label }}</div>
        </button>
      </div>
    </div>

    <!-- Main Content Area -->
    <div class="pb-20">
      <div class="max-w-3xl mx-auto px-4 py-4">
        <!-- Quick actions (ONLY on dashboard) -->
        <div v-if="isAuthenticated && currentView === 'dashboard'" class="mb-6 grid grid-cols-3 gap-3">
          <button
            @click="currentView = 'assignments'"
            class="bg-white border-2 border-slate-200 hover:border-blue-400 rounded-xl p-4 transition-all text-center"
          >
            <div class="text-3xl mb-1">📋</div>
            <div class="text-sm font-bold text-slate-900">My Work</div>
          </button>
          <button
            @click="currentView = 'availability'"
            class="bg-white border-2 border-slate-200 hover:border-blue-400 rounded-xl p-4 transition-all text-center"
          >
            <div class="text-3xl mb-1">📅</div>
            <div class="text-sm font-bold text-slate-900">Schedule</div>
          </button>
          <button
            @click="currentView = 'requests'"
            class="bg-white border-2 border-slate-200 hover:border-blue-400 rounded-xl p-4 transition-all text-center"
          >
            <div class="text-3xl mb-1">🔧</div>
            <div class="text-sm font-bold text-slate-900">Help</div>
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
