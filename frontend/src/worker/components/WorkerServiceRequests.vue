<template>
  <div class="space-y-6">
    <div class="flex justify-between items-center">
      <h1 class="text-3xl font-bold text-gray-900">Service Requests</h1>
      <button
        @click="showNewRequestForm = !showNewRequestForm"
        class="bg-blue-600 hover:bg-blue-700 text-white px-6 py-2 rounded-lg font-medium"
      >
        {{ showNewRequestForm ? '✕ Cancel' : '+ New Request' }}
      </button>
    </div>

    <!-- New Request Form -->
    <div v-if="showNewRequestForm" class="bg-white rounded-lg shadow p-6">
      <h2 class="text-xl font-bold mb-4">Submit New Service Request</h2>
      
      <form @submit.prevent="submitRequest" class="space-y-4">
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-2">
            Work Site *
          </label>
          <select
            v-model="newRequest.work_site"
            required
            class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
          >
            <option value="">Select a work site...</option>
            <option v-for="site in workSites" :key="site.id" :value="site.id">
              {{ site.name }}
            </option>
          </select>
        </div>

        <div>
          <label class="block text-sm font-medium text-gray-700 mb-2">
            Issue Type *
          </label>
          <select
            v-model="newRequest.issue_type"
            required
            class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
          >
            <option value="">Select issue type...</option>
            <option value="bathroom">Bathroom Issue</option>
            <option value="supplies">Supplies Needed</option>
            <option value="safety">Safety Concern</option>
            <option value="equipment">Equipment Problem</option>
            <option value="cleaning">Cleaning Issue</option>
            <option value="other">Other</option>
          </select>
        </div>

        <div>
          <label class="block text-sm font-medium text-gray-700 mb-2">
            Title *
          </label>
          <input
            v-model="newRequest.title"
            type="text"
            required
            placeholder="Brief description of the issue"
            class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
          />
        </div>

        <div>
          <label class="block text-sm font-medium text-gray-700 mb-2">
            Description *
          </label>
          <textarea
            v-model="newRequest.description"
            rows="4"
            required
            placeholder="Detailed description of the problem..."
            class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
          ></textarea>
        </div>

        <div>
          <label class="block text-sm font-medium text-gray-700 mb-2">
            Specific Location
          </label>
          <input
            v-model="newRequest.location_detail"
            type="text"
            placeholder="e.g., 'North bathroom', 'Storage closet'"
            class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
          />
        </div>

        <div>
          <label class="block text-sm font-medium text-gray-700 mb-2">
            Priority *
          </label>
          <select
            v-model="newRequest.priority"
            required
            class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
          >
            <option value="low">Low - Can wait a week</option>
            <option value="medium">Medium - Within a few days</option>
            <option value="high">High - Within 24 hours</option>
            <option value="urgent">Urgent - Needs immediate attention</option>
          </select>
        </div>

        <div>
          <label class="block text-sm font-medium text-gray-700 mb-2">
            Photo (Optional)
          </label>
          <input
            @change="handlePhotoUpload"
            type="file"
            accept="image/*"
            class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
          />
        </div>

        <div v-if="submitError" class="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
          {{ submitError }}
        </div>

        <div class="flex gap-2">
          <button
            type="submit"
            :disabled="submitting"
            class="flex-1 bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 px-4 rounded-lg disabled:opacity-50"
          >
            {{ submitting ? 'Submitting...' : 'Submit Request' }}
          </button>
          <button
            type="button"
            @click="showNewRequestForm = false"
            class="bg-gray-300 hover:bg-gray-400 text-gray-700 font-bold py-3 px-4 rounded-lg"
          >
            Cancel
          </button>
        </div>
      </form>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="text-center py-12">
      <div class="text-gray-500">Loading requests...</div>
    </div>

    <!-- Service Requests List -->
    <div v-else class="space-y-4">
      <div v-if="serviceRequests.length === 0" class="bg-white rounded-lg shadow p-8 text-center text-gray-500">
        No service requests yet. Click "New Request" to submit one.
      </div>

      <div
        v-for="request in serviceRequests"
        :key="request.id"
        class="bg-white rounded-lg shadow p-6"
        :class="{
          'border-l-4 border-red-500': request.priority === 'urgent',
          'border-l-4 border-orange-500': request.priority === 'high',
          'border-l-4 border-yellow-500': request.priority === 'medium',
          'border-l-4 border-gray-300': request.priority === 'low'
        }"
      >
        <div class="flex justify-between items-start mb-4">
          <div class="flex-1">
            <h3 class="font-bold text-xl text-gray-900">{{ request.title }}</h3>
            <p class="text-gray-600 mt-1">{{ request.work_site_name }}</p>
          </div>
          <div class="flex flex-col items-end gap-2">
            <span :class="getStatusClass(request.status)">
              {{ request.status_display }}
            </span>
            <span :class="getPriorityClass(request.priority)">
              {{ request.priority_display }}
            </span>
          </div>
        </div>

        <div class="space-y-2 mb-4">
          <div>
            <span class="text-sm font-medium text-gray-600">Issue Type:</span>
            <span class="text-sm text-gray-900 ml-2">{{ request.issue_type_display }}</span>
          </div>
          <div v-if="request.location_detail">
            <span class="text-sm font-medium text-gray-600">Location:</span>
            <span class="text-sm text-gray-900 ml-2">{{ request.location_detail }}</span>
          </div>
          <div>
            <span class="text-sm font-medium text-gray-600">Submitted:</span>
            <span class="text-sm text-gray-900 ml-2">{{ formatDate(request.created_at) }}</span>
          </div>
        </div>

        <div class="p-3 bg-gray-50 rounded-lg mb-4">
          <p class="text-sm text-gray-700">{{ request.description }}</p>
        </div>

        <div v-if="request.photo" class="mb-4">
          <img :src="request.photo" alt="Issue photo" class="max-w-full h-auto rounded-lg" />
        </div>

        <div v-if="request.resolution_notes" class="p-3 bg-green-50 border border-green-200 rounded-lg">
          <p class="text-sm font-medium text-green-900 mb-1">✅ Resolution:</p>
          <p class="text-sm text-green-800">{{ request.resolution_notes }}</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { getApiUrl } from '../../config/api'

const loading = ref(false)
const submitting = ref(false)
const showNewRequestForm = ref(false)
const submitError = ref('')

const serviceRequests = ref<any[]>([])
const workSites = ref<any[]>([])

const newRequest = ref({
  work_site: '',
  issue_type: '',
  title: '',
  description: '',
  location_detail: '',
  priority: 'medium',
  photo: null as File | null
})

async function loadServiceRequests() {
  loading.value = true
  const token = localStorage.getItem('worker_token')

  try {
    const response = await fetch(getApiUrl('/api/worker/service-requests/'), {
      headers: {
        'Authorization': `Token ${token}`
      }
    })

    if (response.ok) {
      serviceRequests.value = await response.json()
    }
  } catch (err) {
    console.error('Failed to load service requests:', err)
  } finally {
    loading.value = false
  }
}

async function loadWorkSites() {
  const token = localStorage.getItem('worker_token')

  try {
    const response = await fetch(getApiUrl('/api/worker/work-sites/'), {
      headers: {
        'Authorization': `Token ${token}`
      }
    })

    if (response.ok) {
      workSites.value = await response.json()
    }
  } catch (err) {
    console.error('Failed to load work sites:', err)
  }
}

function handlePhotoUpload(event: Event) {
  const target = event.target as HTMLInputElement
  if (target.files && target.files[0]) {
    newRequest.value.photo = target.files[0]
  }
}

async function submitRequest() {
  submitting.value = true
  submitError.value = ''
  const token = localStorage.getItem('worker_token')

  try {
    // Create FormData for file upload
    const formData = new FormData()
    formData.append('work_site', newRequest.value.work_site)
    formData.append('issue_type', newRequest.value.issue_type)
    formData.append('title', newRequest.value.title)
    formData.append('description', newRequest.value.description)
    formData.append('location_detail', newRequest.value.location_detail)
    formData.append('priority', newRequest.value.priority)
    
    if (newRequest.value.photo) {
      formData.append('photo', newRequest.value.photo)
    }

    const response = await fetch(getApiUrl('/api/worker/service-requests/'), {
      method: 'POST',
      headers: {
        'Authorization': `Token ${token}`
      },
      body: formData
    })

    if (response.ok) {
      // Reset form
      newRequest.value = {
        work_site: '',
        issue_type: '',
        title: '',
        description: '',
        location_detail: '',
        priority: 'medium',
        photo: null
      }
      showNewRequestForm.value = false
      
      // Reload requests
      await loadServiceRequests()
    } else {
      const data = await response.json()
      submitError.value = data.error || 'Failed to submit request'
    }
  } catch (err) {
    console.error('Failed to submit request:', err)
    submitError.value = 'Network error. Please try again.'
  } finally {
    submitting.value = false
  }
}

function formatDate(date: string) {
  if (!date) return ''
  const d = new Date(date)
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric', hour: 'numeric', minute: '2-digit' })
}

function getStatusClass(status: string) {
  const classes = {
    'open': 'inline-flex items-center px-3 py-1 bg-red-100 text-red-800 text-sm font-medium rounded-full',
    'acknowledged': 'inline-flex items-center px-3 py-1 bg-yellow-100 text-yellow-800 text-sm font-medium rounded-full',
    'in_progress': 'inline-flex items-center px-3 py-1 bg-blue-100 text-blue-800 text-sm font-medium rounded-full',
    'resolved': 'inline-flex items-center px-3 py-1 bg-green-100 text-green-800 text-sm font-medium rounded-full',
    'closed': 'inline-flex items-center px-3 py-1 bg-gray-100 text-gray-800 text-sm font-medium rounded-full'
  }
  return classes[status as keyof typeof classes] || classes.open
}

function getPriorityClass(priority: string) {
  const classes = {
    'urgent': 'inline-flex items-center px-2 py-1 bg-red-500 text-white text-xs font-bold rounded',
    'high': 'inline-flex items-center px-2 py-1 bg-orange-500 text-white text-xs font-bold rounded',
    'medium': 'inline-flex items-center px-2 py-1 bg-yellow-500 text-white text-xs font-bold rounded',
    'low': 'inline-flex items-center px-2 py-1 bg-gray-400 text-white text-xs font-bold rounded'
  }
  return classes[priority as keyof typeof classes] || classes.medium
}

onMounted(() => {
  loadServiceRequests()
  loadWorkSites()
})
</script>
