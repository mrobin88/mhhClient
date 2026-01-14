<template>
  <div class="space-y-6">
    <div class="flex justify-between items-center">
      <h1 class="text-3xl font-bold text-gray-900">Dashboard</h1>
      <button 
        @click="loadDashboard"
        class="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm"
      >
        🔄 Refresh
      </button>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="text-center py-12">
      <div class="text-gray-500">Loading your dashboard...</div>
    </div>

    <!-- Dashboard Content -->
    <div v-else class="space-y-6">
      <!-- Stats Cards -->
      <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div class="bg-white rounded-lg shadow p-6">
          <div class="flex items-center justify-between">
            <div>
              <p class="text-sm text-gray-600">This Month</p>
              <p class="text-3xl font-bold text-gray-900">{{ stats.total_assignments_this_month }}</p>
              <p class="text-xs text-gray-500 mt-1">Total Assignments</p>
            </div>
            <div class="text-4xl">📋</div>
          </div>
        </div>

        <div class="bg-white rounded-lg shadow p-6">
          <div class="flex items-center justify-between">
            <div>
              <p class="text-sm text-gray-600">Completed</p>
              <p class="text-3xl font-bold text-green-600">{{ stats.completed_assignments }}</p>
              <p class="text-xs text-gray-500 mt-1">This Month</p>
            </div>
            <div class="text-4xl">✅</div>
          </div>
        </div>

        <div class="bg-white rounded-lg shadow p-6">
          <div class="flex items-center justify-between">
            <div>
              <p class="text-sm text-gray-600">Pending Requests</p>
              <p class="text-3xl font-bold text-orange-600">{{ stats.pending_service_requests }}</p>
              <p class="text-xs text-gray-500 mt-1">Service Requests</p>
            </div>
            <div class="text-4xl">🔧</div>
          </div>
        </div>
      </div>

      <!-- Today's Assignments -->
      <div class="bg-white rounded-lg shadow">
        <div class="px-6 py-4 border-b border-gray-200">
          <h2 class="text-xl font-bold text-gray-900">Today's Assignments</h2>
        </div>
        <div class="p-6">
          <div v-if="todayAssignments.length === 0" class="text-center py-8 text-gray-500">
            No assignments scheduled for today
          </div>
          <div v-else class="space-y-4">
            <div
              v-for="assignment in todayAssignments"
              :key="assignment.id"
              class="border border-gray-200 rounded-lg p-4 hover:bg-gray-50 transition"
            >
              <div class="flex justify-between items-start">
                <div class="flex-1">
                  <h3 class="font-bold text-lg text-gray-900">{{ assignment.work_site_name }}</h3>
                  <p class="text-sm text-gray-600 mt-1">{{ assignment.work_site_address }}</p>
                  <div class="mt-2 flex flex-wrap gap-2">
                    <span class="inline-flex items-center px-2 py-1 bg-blue-100 text-blue-800 text-xs font-medium rounded">
                      🕐 {{ formatTime(assignment.start_time) }} - {{ formatTime(assignment.end_time) }}
                    </span>
                    <span :class="getStatusClass(assignment.status)">
                      {{ assignment.status_display }}
                    </span>
                  </div>
                  <div v-if="assignment.work_site_supervisor" class="mt-2 text-sm text-gray-600">
                    <strong>Supervisor:</strong> {{ assignment.work_site_supervisor }}
                    <span v-if="assignment.work_site_supervisor_phone">
                      - <a :href="`tel:${assignment.work_site_supervisor_phone}`" class="text-blue-600">{{ assignment.work_site_supervisor_phone }}</a>
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Upcoming Assignments -->
      <div class="bg-white rounded-lg shadow">
        <div class="px-6 py-4 border-b border-gray-200">
          <h2 class="text-xl font-bold text-gray-900">Upcoming Assignments (Next 7 Days)</h2>
        </div>
        <div class="p-6">
          <div v-if="upcomingAssignments.length === 0" class="text-center py-8 text-gray-500">
            No upcoming assignments
          </div>
          <div v-else class="space-y-4">
            <div
              v-for="assignment in upcomingAssignments"
              :key="assignment.id"
              class="border border-gray-200 rounded-lg p-4 hover:bg-gray-50 transition"
            >
              <div class="flex justify-between items-start">
                <div class="flex-1">
                  <div class="flex items-center gap-2">
                    <h3 class="font-bold text-lg text-gray-900">{{ assignment.work_site_name }}</h3>
                    <span class="text-sm text-gray-600">{{ formatDate(assignment.assignment_date) }}</span>
                  </div>
                  <p class="text-sm text-gray-600 mt-1">{{ assignment.work_site_address }}</p>
                  <div class="mt-2 flex flex-wrap gap-2">
                    <span class="inline-flex items-center px-2 py-1 bg-blue-100 text-blue-800 text-xs font-medium rounded">
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
      <div class="bg-white rounded-lg shadow">
        <div class="px-6 py-4 border-b border-gray-200">
          <h2 class="text-xl font-bold text-gray-900">Recent Service Requests</h2>
        </div>
        <div class="p-6">
          <div v-if="recentServiceRequests.length === 0" class="text-center py-8 text-gray-500">
            No service requests yet
          </div>
          <div v-else class="space-y-3">
            <div
              v-for="request in recentServiceRequests"
              :key="request.id"
              class="border-l-4 border-gray-300 pl-4 py-2"
              :class="{
                'border-red-500': request.priority === 'urgent',
                'border-orange-500': request.priority === 'high',
                'border-yellow-500': request.priority === 'medium',
                'border-gray-300': request.priority === 'low'
              }"
            >
              <div class="flex justify-between items-start">
                <div>
                  <h4 class="font-semibold text-gray-900">{{ request.title }}</h4>
                  <p class="text-sm text-gray-600">{{ request.work_site_name }}</p>
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
import { ref, onMounted } from 'vue'
import { getApiUrl } from '../../config/api'

const loading = ref(false)
const todayAssignments = ref<any[]>([])
const upcomingAssignments = ref<any[]>([])
const recentServiceRequests = ref<any[]>([])
const stats = ref({
  total_assignments_this_month: 0,
  completed_assignments: 0,
  pending_service_requests: 0
})

async function loadDashboard() {
  loading.value = true
  const token = localStorage.getItem('worker_token')

  try {
    const response = await fetch(getApiUrl('/api/worker/dashboard/'), {
      headers: {
        'Authorization': `Token ${token}`
      }
    })

    if (response.ok) {
      const data = await response.json()
      todayAssignments.value = data.today_assignments || []
      upcomingAssignments.value = data.upcoming_assignments || []
      recentServiceRequests.value = data.recent_service_requests || []
      stats.value = data.stats || stats.value
    }
  } catch (err) {
    console.error('Failed to load dashboard:', err)
  } finally {
    loading.value = false
  }
}

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
