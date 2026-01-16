<template>
  <div class="space-y-4">
    <div class="flex justify-between items-center mb-2">
      <h1 class="text-2xl font-bold text-slate-900">Dashboard</h1>
      <button 
        @click="loadDashboard"
        class="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm font-bold transition-all"
      >
        🔄
      </button>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="text-center py-16">
      <div class="text-2xl text-slate-400 animate-pulse">Loading...</div>
    </div>

    <!-- Dashboard Content -->
    <div v-else class="space-y-6">
      <!-- Stats Cards -->
      <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div class="bg-white rounded-xl shadow-md p-6 border-2 border-slate-200">
          <div class="flex items-center justify-between">
            <div>
              <p class="text-sm text-slate-600 font-semibold">This Month</p>
              <p class="text-4xl font-bold text-slate-900">{{ stats.total_assignments_this_month }}</p>
              <p class="text-xs text-slate-500 mt-1 font-medium">Total Assignments</p>
            </div>
            <div class="text-5xl">📋</div>
          </div>
        </div>

        <div class="bg-white rounded-xl shadow-md p-6 border-2 border-slate-200">
          <div class="flex items-center justify-between">
            <div>
              <p class="text-sm text-slate-600 font-semibold">Completed</p>
              <p class="text-4xl font-bold text-green-600">{{ stats.completed_assignments }}</p>
              <p class="text-xs text-slate-500 mt-1 font-medium">This Month</p>
            </div>
            <div class="text-5xl">✅</div>
          </div>
        </div>

        <div class="bg-white rounded-xl shadow-md p-6 border-2 border-slate-200">
          <div class="flex items-center justify-between">
            <div>
              <p class="text-sm text-slate-600 font-semibold">Pending</p>
              <p class="text-4xl font-bold text-orange-600">{{ stats.pending_service_requests }}</p>
              <p class="text-xs text-slate-500 mt-1 font-medium">Service Requests</p>
            </div>
            <div class="text-5xl">🔧</div>
          </div>
        </div>
      </div>

      <!-- Today's Assignments -->
      <div class="bg-white rounded-xl shadow-lg border-2 border-slate-200">
        <div class="px-6 py-4 border-b-2 border-slate-200 bg-slate-50">
          <h2 class="text-2xl font-bold text-slate-900">📋 Today's Work</h2>
        </div>
        <div class="p-6">
          <div v-if="todayAssignments.length === 0" class="text-center py-12 text-slate-500 text-lg">
            No work scheduled for today — enjoy your day off!
          </div>
          <div v-else class="space-y-4">
            <div
              v-for="assignment in todayAssignments"
              :key="assignment.id"
              class="border-2 border-slate-200 rounded-xl p-5 hover:border-blue-400 hover:shadow-md transition-all"
            >
              <div class="flex justify-between items-start">
                <div class="flex-1">
                  <h3 class="font-bold text-xl text-slate-900">{{ assignment.work_site_name }}</h3>
                  <p class="text-base text-slate-700 mt-1">{{ assignment.work_site_address }}</p>
                  <div class="mt-3 flex flex-wrap gap-2">
                    <span class="inline-flex items-center px-3 py-1 bg-blue-100 text-blue-800 text-sm font-bold rounded-lg">
                      🕐 {{ formatTime(assignment.start_time) }} - {{ formatTime(assignment.end_time) }}
                    </span>
                    <span :class="getStatusClass(assignment.status)">
                      {{ assignment.status_display }}
                    </span>
                  </div>
                  <div v-if="assignment.work_site_supervisor" class="mt-3 text-base text-slate-700">
                    <strong>Supervisor:</strong> {{ assignment.work_site_supervisor }}
                    <span v-if="assignment.work_site_supervisor_phone">
                      - <a :href="`tel:${assignment.work_site_supervisor_phone}`" class="text-blue-600 font-bold underline">{{ assignment.work_site_supervisor_phone }}</a>
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Upcoming Assignments -->
      <div class="bg-white rounded-xl shadow-lg border-2 border-slate-200">
        <div class="px-6 py-4 border-b-2 border-slate-200 bg-slate-50">
          <h2 class="text-2xl font-bold text-slate-900">📅 Next Week</h2>
        </div>
        <div class="p-6">
          <div v-if="upcomingAssignments.length === 0" class="text-center py-12 text-slate-500 text-lg">
            No upcoming work scheduled
          </div>
          <div v-else class="space-y-3">
            <div
              v-for="assignment in upcomingAssignments"
              :key="assignment.id"
              class="border-2 border-slate-200 rounded-xl p-4 hover:border-blue-400 hover:shadow-md transition-all"
            >
              <div class="flex justify-between items-start">
                <div class="flex-1">
                  <div class="flex items-center gap-3">
                    <h3 class="font-bold text-lg text-slate-900">{{ assignment.work_site_name }}</h3>
                    <span class="text-sm text-slate-700 font-semibold bg-slate-100 px-2 py-1 rounded-lg">{{ formatDate(assignment.assignment_date) }}</span>
                  </div>
                  <p class="text-sm text-slate-700 mt-1">{{ assignment.work_site_address }}</p>
                  <div class="mt-2 flex flex-wrap gap-2">
                    <span class="inline-flex items-center px-3 py-1 bg-blue-100 text-blue-800 text-sm font-bold rounded-lg">
                      🕐 {{ formatTime(assignment.start_time) }} - {{ formatTime(assignment.end_time) }}
                    </span>
                    <span :class="getStatusClass(assignment.status)">
                      {{ assignment.status_display }}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Recent Service Requests -->
      <div class="bg-white rounded-xl shadow-lg border-2 border-slate-200">
        <div class="px-6 py-4 border-b-2 border-slate-200 bg-slate-50">
          <h2 class="text-2xl font-bold text-slate-900">🔧 My Requests</h2>
        </div>
        <div class="p-6">
          <div v-if="recentServiceRequests.length === 0" class="text-center py-12 text-slate-500 text-lg">
            No service requests
          </div>
          <div v-else class="space-y-3">
            <div
              v-for="request in recentServiceRequests"
              :key="request.id"
              class="border-l-4 pl-4 py-3 rounded-lg bg-slate-50"
              :class="{
                'border-red-500': request.priority === 'urgent',
                'border-orange-500': request.priority === 'high',
                'border-yellow-500': request.priority === 'medium',
                'border-slate-300': request.priority === 'low'
              }"
            >
              <div class="flex justify-between items-start">
                <div>
                  <h4 class="font-bold text-lg text-slate-900">{{ request.title }}</h4>
                  <p class="text-base text-slate-700 mt-1">{{ request.work_site_name }}</p>
                </div>
                <span :class="getRequestStatusClass(request.status)">
                  {{ request.status_display }}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { workerFetch } from '../api'

const props = defineProps<{
  workerAccount: any
  cachedData?: any
}>()

const emit = defineEmits(['update-cache'])

const loading = ref(false)
const todayAssignments = ref<any[]>([])
const upcomingAssignments = ref<any[]>([])
const recentServiceRequests = ref<any[]>([])
const stats = ref({
  total_assignments_this_month: 0,
  completed_assignments: 0,
  pending_service_requests: 0
})

// Load cached data immediately if available
if (props.cachedData) {
  todayAssignments.value = props.cachedData.today_assignments || []
  upcomingAssignments.value = props.cachedData.upcoming_assignments || []
  recentServiceRequests.value = props.cachedData.recent_service_requests || []
  stats.value = props.cachedData.stats || stats.value
}

async function loadDashboard() {
  loading.value = true
  const token = localStorage.getItem('worker_token')
  if (!token) {
    loading.value = false
    return
  }

  try {
    const response = await workerFetch('/api/worker/dashboard/')

    if (response.ok) {
      const data = await response.json()
      todayAssignments.value = data.today_assignments || []
      upcomingAssignments.value = data.upcoming_assignments || []
      recentServiceRequests.value = data.recent_service_requests || []
      stats.value = data.stats || stats.value
      
      // Update cache in parent
      emit('update-cache', data)
    }
  } catch (err) {
    console.error('Failed to load dashboard:', err)
  } finally {
    loading.value = false
  }
}

// Watch for cached data changes
watch(() => props.cachedData, (newData) => {
  if (newData) {
    todayAssignments.value = newData.today_assignments || []
    upcomingAssignments.value = newData.upcoming_assignments || []
    recentServiceRequests.value = newData.recent_service_requests || []
    stats.value = newData.stats || stats.value
  }
})

function formatTime(time: string) {
  if (!time) return ''
  const [hours, minutes] = time.split(':')
  const hour = parseInt(hours)
  const ampm = hour >= 12 ? 'PM' : 'AM'
  const displayHour = hour % 12 || 12
  return `${displayHour}:${minutes} ${ampm}`
}

function formatDate(date: string) {
  if (!date) return ''
  const d = new Date(date)
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}

function getStatusClass(status: string) {
  const classes = {
    'pending': 'inline-flex items-center px-2 py-1 bg-yellow-100 text-yellow-800 text-xs font-medium rounded',
    'confirmed': 'inline-flex items-center px-2 py-1 bg-green-100 text-green-800 text-xs font-medium rounded',
    'in_progress': 'inline-flex items-center px-2 py-1 bg-blue-100 text-blue-800 text-xs font-medium rounded',
    'completed': 'inline-flex items-center px-2 py-1 bg-gray-100 text-gray-800 text-xs font-medium rounded',
    'called_out': 'inline-flex items-center px-2 py-1 bg-red-100 text-red-800 text-xs font-medium rounded',
    'cancelled': 'inline-flex items-center px-2 py-1 bg-gray-100 text-gray-600 text-xs font-medium rounded'
  }
  return classes[status as keyof typeof classes] || classes.pending
}

function getRequestStatusClass(status: string) {
  const classes = {
    'open': 'inline-flex items-center px-2 py-1 bg-red-100 text-red-800 text-xs font-medium rounded',
    'acknowledged': 'inline-flex items-center px-2 py-1 bg-yellow-100 text-yellow-800 text-xs font-medium rounded',
    'in_progress': 'inline-flex items-center px-2 py-1 bg-blue-100 text-blue-800 text-xs font-medium rounded',
    'resolved': 'inline-flex items-center px-2 py-1 bg-green-100 text-green-800 text-xs font-medium rounded',
    'closed': 'inline-flex items-center px-2 py-1 bg-gray-100 text-gray-800 text-xs font-medium rounded'
  }
  return classes[status as keyof typeof classes] || classes.open
}

onMounted(() => {
  loadDashboard()
})
</script>
