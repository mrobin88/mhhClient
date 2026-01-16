<template>
  <div class="space-y-4">
    <h1 class="text-2xl font-bold text-slate-900 mb-2">My Work</h1>

    <!-- Filter Tabs -->
    <div class="bg-white rounded-xl shadow-lg p-2 border-2 border-slate-200">
      <div class="flex space-x-2">
        <button
          v-for="filter in filters"
          :key="filter.value"
          @click="activeFilter = filter.value; loadAssignments()"
          :class="[
            'flex-1 px-4 py-3 rounded-xl font-bold transition-all text-base',
            activeFilter === filter.value
              ? 'bg-blue-600 text-white shadow-lg'
              : 'text-slate-700 hover:bg-slate-100'
          ]"
        >
          {{ filter.label }}
        </button>
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="text-center py-16">
      <div class="text-2xl text-slate-400 animate-pulse">Loading...</div>
    </div>

    <!-- Assignments List -->
    <div v-else class="space-y-4">
      <div v-if="assignments.length === 0" class="bg-white rounded-xl shadow-lg p-12 text-center text-slate-500 text-lg border-2 border-slate-200">
        No {{ activeFilter }} work found
      </div>

      <div
        v-for="assignment in assignments"
        :key="assignment.id"
        class="bg-white rounded-xl shadow-lg p-6 border-2 border-slate-200 hover:border-blue-400 hover:shadow-xl transition-all"
      >
        <div class="flex justify-between items-start mb-4">
          <div class="flex-1">
            <h3 class="font-bold text-2xl text-slate-900">{{ assignment.work_site_name }}</h3>
            <p class="text-slate-700 mt-1 text-base">{{ assignment.work_site_address }}</p>
          </div>
          <span :class="getStatusClass(assignment.status)">
            {{ assignment.status_display }}
          </span>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
          <div class="bg-slate-50 rounded-lg p-3">
            <p class="text-sm text-slate-600 font-semibold">📅 Date</p>
            <p class="font-bold text-lg text-slate-900">{{ formatDate(assignment.assignment_date) }}</p>
          </div>
          <div class="bg-slate-50 rounded-lg p-3">
            <p class="text-sm text-slate-600 font-semibold">🕐 Time</p>
            <p class="font-bold text-lg text-slate-900">{{ formatTime(assignment.start_time) }} - {{ formatTime(assignment.end_time) }}</p>
          </div>
          <div v-if="assignment.work_site_supervisor" class="bg-slate-50 rounded-lg p-3">
            <p class="text-sm text-slate-600 font-semibold">👤 Supervisor</p>
            <p class="font-bold text-lg text-slate-900">{{ assignment.work_site_supervisor }}</p>
          </div>
          <div v-if="assignment.work_site_supervisor_phone" class="bg-blue-50 rounded-lg p-3">
            <p class="text-sm text-slate-600 font-semibold">📞 Call</p>
            <p class="font-bold text-lg">
              <a :href="`tel:${assignment.work_site_supervisor_phone}`" class="text-blue-600 underline">
                {{ assignment.work_site_supervisor_phone }}
              </a>
            </p>
          </div>
        </div>

        <div v-if="assignment.assignment_notes" class="mb-4 p-4 bg-yellow-50 rounded-lg border-2 border-yellow-300">
          <p class="text-sm text-slate-700 font-bold">📝 Important:</p>
          <p class="text-base text-slate-800 mt-1 font-medium">{{ assignment.assignment_notes }}</p>
        </div>

        <!-- Action Buttons -->
        <div class="flex flex-wrap gap-3">
          <button
            v-if="assignment.status === 'pending' && !assignment.confirmed_by_client"
            @click="confirmAssignment(assignment.id)"
            class="bg-green-600 hover:bg-green-700 text-white px-6 py-3 rounded-xl text-base font-bold shadow-lg transition-all"
          >
            ✅ I'll Be There
          </button>

          <button
            v-if="canCallOut(assignment)"
            @click="showCallOutModal(assignment)"
            class="bg-red-600 hover:bg-red-700 text-white px-6 py-3 rounded-xl text-base font-bold shadow-lg transition-all"
          >
            ⚠️ Can't Make It
          </button>
        </div>
      </div>
    </div>

    <!-- Call Out Modal -->
    <div v-if="callOutModalOpen" class="fixed inset-0 bg-black bg-opacity-70 flex items-center justify-center z-50 p-4">
      <div class="bg-white rounded-2xl max-w-md w-full p-8 shadow-2xl border-2 border-slate-200">
        <h2 class="text-3xl font-bold mb-6 text-slate-900">⚠️ Can't Make It?</h2>
        
        <div class="mb-6 p-4 bg-slate-50 rounded-xl border-2 border-slate-200">
          <p class="text-sm text-slate-600 font-semibold">Work Assignment:</p>
          <p class="font-bold text-xl text-slate-900 mt-1">{{ selectedAssignment?.work_site_name }}</p>
          <p class="text-base text-slate-700 mt-1">{{ formatDate(selectedAssignment?.assignment_date) }}</p>
        </div>

        <form @submit.prevent="submitCallOut" class="space-y-5">
          <div>
            <label class="block text-base font-bold text-slate-800 mb-2">
              How much notice can you give? (hours)
            </label>
            <input
              v-model.number="callOutForm.advance_notice_hours"
              type="number"
              min="0"
              max="72"
              required
              class="w-full px-4 py-3 text-lg border-2 border-slate-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>

          <div>
            <label class="block text-base font-bold text-slate-800 mb-2">
              Why can't you make it?
            </label>
            <textarea
              v-model="callOutForm.reason"
              rows="4"
              required
              placeholder="Tell us what happened..."
              class="w-full px-4 py-3 text-lg border-2 border-slate-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            ></textarea>
          </div>

          <div v-if="callOutError" class="bg-red-50 border-2 border-red-300 text-red-800 px-5 py-4 rounded-xl font-medium">
            {{ callOutError }}
          </div>

          <div class="flex gap-3 pt-2">
            <button
              type="submit"
              :disabled="submittingCallOut"
              class="flex-1 bg-red-600 hover:bg-red-700 text-white font-bold py-4 px-6 text-lg rounded-xl shadow-lg disabled:opacity-50 transition-all"
            >
              {{ submittingCallOut ? 'Sending...' : 'Send Notice' }}
            </button>
            <button
              type="button"
              @click="closeCallOutModal"
              class="flex-1 bg-slate-200 hover:bg-slate-300 text-slate-800 font-bold py-4 px-6 text-lg rounded-xl transition-all"
            >
              Cancel
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { workerFetch } from '../api'

const loading = ref(false)
const assignments = ref<any[]>([])
const activeFilter = ref('upcoming')

const filters = [
  { value: 'today', label: 'Today' },
  { value: 'upcoming', label: 'Upcoming' },
  { value: 'past', label: 'Past' }
]

// Call-out modal
const callOutModalOpen = ref(false)
const selectedAssignment = ref<any>(null)
const callOutForm = ref({
  reason: '',
  advance_notice_hours: 4
})
const submittingCallOut = ref(false)
const callOutError = ref('')

async function loadAssignments() {
  loading.value = true
  const token = localStorage.getItem('worker_token')
  if (!token) {
    assignments.value = []
    loading.value = false
    return
  }

  try {
    const response = await workerFetch(`/api/worker/assignments/?filter=${activeFilter.value}`)

    if (response.ok) {
      assignments.value = await response.json()
    }
  } catch (err) {
    console.error('Failed to load assignments:', err)
  } finally {
    loading.value = false
  }
}

async function confirmAssignment(assignmentId: number) {
  const token = localStorage.getItem('worker_token')
  if (!token) return

  try {
    const response = await workerFetch(`/api/worker/assignments/${assignmentId}/confirm/`, { method: 'POST' })

    if (response.ok) {
      await loadAssignments()
    }
  } catch (err) {
    console.error('Failed to confirm assignment:', err)
  }
}

function canCallOut(assignment: any) {
  const assignmentDate = new Date(assignment.assignment_date)
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  
  return assignmentDate >= today && assignment.status !== 'called_out' && assignment.status !== 'cancelled'
}

function showCallOutModal(assignment: any) {
  selectedAssignment.value = assignment
  callOutForm.value = {
    reason: '',
    advance_notice_hours: 4
  }
  callOutError.value = ''
  callOutModalOpen.value = true
}

function closeCallOutModal() {
  callOutModalOpen.value = false
  selectedAssignment.value = null
}

async function submitCallOut() {
  if (!selectedAssignment.value) return

  submittingCallOut.value = true
  callOutError.value = ''
  const token = localStorage.getItem('worker_token')
  if (!token) {
    callOutError.value = 'Please log in again.'
    submittingCallOut.value = false
    return
  }

  try {
    const response = await workerFetch('/api/worker/call-out/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        assignment_id: selectedAssignment.value.id,
        reason: callOutForm.value.reason,
        advance_notice_hours: callOutForm.value.advance_notice_hours
      })
    })

    if (response.ok) {
      closeCallOutModal()
      await loadAssignments()
    } else {
      const data = await response.json()
      callOutError.value = data.error || 'Failed to submit call-out'
    }
  } catch (err) {
    console.error('Failed to submit call-out:', err)
    callOutError.value = 'Network error. Please try again.'
  } finally {
    submittingCallOut.value = false
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
  return d.toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' })
}

function getStatusClass(status: string) {
  const classes = {
    'pending': 'inline-flex items-center px-3 py-1 bg-yellow-100 text-yellow-800 text-sm font-medium rounded-full',
    'confirmed': 'inline-flex items-center px-3 py-1 bg-green-100 text-green-800 text-sm font-medium rounded-full',
    'in_progress': 'inline-flex items-center px-3 py-1 bg-blue-100 text-blue-800 text-sm font-medium rounded-full',
    'completed': 'inline-flex items-center px-3 py-1 bg-gray-100 text-gray-800 text-sm font-medium rounded-full',
    'called_out': 'inline-flex items-center px-3 py-1 bg-red-100 text-red-800 text-sm font-medium rounded-full',
    'cancelled': 'inline-flex items-center px-3 py-1 bg-gray-100 text-gray-600 text-sm font-medium rounded-full'
  }
  return classes[status as keyof typeof classes] || classes.pending
}

onMounted(() => {
  loadAssignments()
})
</script>
