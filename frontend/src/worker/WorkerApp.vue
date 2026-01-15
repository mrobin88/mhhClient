<template>
  <div class="min-h-screen bg-gray-100">
    <!-- Navigation Bar -->
    <nav v-if="isAuthenticated" class="bg-blue-600 text-white shadow-lg">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="flex justify-between items-center h-16">
          <div class="flex items-center">
            <h1 class="text-xl font-bold">🏢 Worker Portal</h1>
          </div>
          <div class="flex items-center space-x-4">
            <span class="text-sm">{{ workerName }}</span>
            <button 
              @click="logout"
              class="bg-blue-700 hover:bg-blue-800 px-4 py-2 rounded text-sm font-medium"
            >
              Logout
            </button>
          </div>
        </div>
      </div>
    </nav>

    <!-- Bottom Navigation (Mobile) -->
    <div v-if="isAuthenticated" class="fixed bottom-0 left-0 right-0 bg-white border-t border-gray-200 md:hidden z-50">
      <div class="flex justify-around">
        <button
          v-for="item in navItems"
          :key="item.id"
          @click="currentView = item.id"
          :class="[
            'flex-1 py-3 text-center',
            currentView === item.id ? 'text-blue-600 bg-blue-50' : 'text-gray-600'
          ]"
        >
          <div class="text-2xl">{{ item.icon }}</div>
          <div class="text-xs mt-1">{{ item.label }}</div>
        </button>
      </div>
    </div>

    <!-- Side Navigation (Desktop) -->
    <div v-if="isAuthenticated" class="hidden md:flex">
      <div class="w-64 bg-white shadow-lg h-screen fixed">
        <nav class="mt-8">
          <button
            v-for="item in navItems"
            :key="item.id"
            @click="currentView = item.id"
            :class="[
              'w-full flex items-center px-6 py-3 text-left',
              currentView === item.id 
                ? 'bg-blue-50 text-blue-600 border-l-4 border-blue-600' 
                : 'text-gray-700 hover:bg-gray-50'
            ]"
          >
            <span class="text-2xl mr-3">{{ item.icon }}</span>
            <span class="font-medium">{{ item.label }}</span>
          </button>
        </nav>
      </div>
    </div>

    <!-- Main Content Area -->
    <div :class="[
      'pb-20 md:pb-0',
      isAuthenticated ? 'md:ml-64' : ''
    ]">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <!-- Login View -->
        <WorkerLogin 
          v-if="!isAuthenticated" 
          @login-success="handleLoginSuccess"
        />

        <!-- Dashboard -->
        <WorkerDashboard 
          v-else-if="currentView === 'dashboard'"
          :worker-account="workerAccount"
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

const navItems = [
  { id: 'dashboard', label: 'Dashboard', icon: '🏠' },
  { id: 'assignments', label: 'Assignments', icon: '📋' },
  { id: 'availability', label: 'Availability', icon: '📅' },
  { id: 'requests', label: 'Service Requests', icon: '🔧' }
]

const workerName = computed(() => {
  return workerAccount.value?.client_name || 'Worker'
})

function handleLoginSuccess(data: any) {
  isAuthenticated.value = true
  workerAccount.value = data.worker_account
  localStorage.setItem('worker_token', data.token)
  localStorage.setItem('worker_account', JSON.stringify(data.worker_account))
}

function resetToLogin() {
  localStorage.removeItem('worker_token')
  localStorage.removeItem('worker_account')
  isAuthenticated.value = false
  workerAccount.value = null
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
