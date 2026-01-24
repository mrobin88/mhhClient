<template>
  <div class="space-y-4">
    <div class="flex justify-between items-center mb-2">
      <h1 class="text-2xl font-bold text-slate-900">Report Issue</h1>
      <button
        @click="showNewRequestForm = !showNewRequestForm"
        :class="[
          'px-5 py-3 rounded-xl font-bold transition-all text-base shadow-lg',
          showNewRequestForm 
            ? 'bg-slate-200 hover:bg-slate-300 text-slate-800' 
            : 'bg-blue-600 hover:bg-blue-700 text-white'
        ]"
      >
        {{ showNewRequestForm ? '✕ Cancel' : '+ Report Problem' }}
      </button>
    </div>

    <!-- New Request Form -->
    <div v-if="showNewRequestForm" class="bg-white rounded-xl shadow-xl p-8 border-2 border-slate-200">
      <h2 class="text-2xl font-bold mb-6 text-slate-900">What's the problem?</h2>
      
      <form @submit.prevent="submitRequest" class="space-y-5">
        <div>
          <label class="block text-base font-bold text-slate-800 mb-2">
            Where is the problem?
          </label>
          <select
            v-model="newRequest.work_site"
            required
            class="w-full px-4 py-3 text-lg border-2 border-slate-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          >
            <option value="">Pick a location...</option>
            <option v-for="site in workSites" :key="site.id" :value="site.id">
              {{ site.name }}
            </option>
          </select>
        </div>

        <div>
          <label class="block text-base font-bold text-slate-800 mb-2">
            What type of problem?
          </label>
          <select
            v-model="newRequest.issue_type"
            required
            class="w-full px-4 py-3 text-lg border-2 border-slate-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          >
            <option value="">Pick one...</option>
            <option value="bathroom">🚽 Bathroom</option>
            <option value="supplies">📦 Need Supplies</option>
            <option value="safety">⚠️ Safety Issue</option>
            <option value="equipment">🔧 Broken Equipment</option>
            <option value="cleaning">🧹 Cleaning Needed</option>
            <option value="other">❓ Other</option>
          </select>
        </div>

        <div>
          <label class="block text-base font-bold text-slate-800 mb-2">
            Short description
          </label>
          <input
            v-model="newRequest.title"
            type="text"
            required
            placeholder="Example: Toilet is broken"
            class="w-full px-4 py-3 text-lg border-2 border-slate-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          />
        </div>

        <div>
          <label class="block text-base font-bold text-slate-800 mb-2">
            Tell us more
          </label>
          <textarea
            v-model="newRequest.description"
            rows="4"
            required
            placeholder="What exactly is wrong?"
            class="w-full px-4 py-3 text-lg border-2 border-slate-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          ></textarea>
        </div>

        <div>
          <label class="block text-base font-bold text-slate-800 mb-2">
            Where exactly? (optional)
          </label>
          <input
            v-model="newRequest.location_detail"
            type="text"
            placeholder="Example: North side bathroom"
            class="w-full px-4 py-3 text-lg border-2 border-slate-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          />
        </div>

        <div>
          <label class="block text-base font-bold text-slate-800 mb-2">
            How urgent?
          </label>
          <select
            v-model="newRequest.priority"
            required
            class="w-full px-4 py-3 text-lg border-2 border-slate-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          >
            <option value="low">⏸️ Can wait a week</option>
            <option value="medium">📅 Within a few days</option>
            <option value="high">🔴 Within 24 hours</option>
            <option value="urgent">🚨 Right now!</option>
          </select>
        </div>

        <div>
          <label class="block text-base font-bold text-slate-800 mb-2">
            Take a photo (optional)
          </label>
          <input
            @change="handlePhotoUpload"
            type="file"
            accept="image/*"
            class="w-full px-4 py-3 text-base border-2 border-slate-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:bg-blue-100 file:text-blue-700 file:font-bold hover:file:bg-blue-200"
          />
        </div>

        <div v-if="submitError" class="bg-red-50 border-2 border-red-300 text-red-800 px-5 py-4 rounded-xl font-medium">
          {{ submitError }}
        </div>

        <button
          type="submit"
          :disabled="submitting"
          class="w-full bg-green-600 hover:bg-green-700 text-white font-bold py-5 px-6 text-xl rounded-xl shadow-xl disabled:opacity-50 disabled:cursor-not-allowed transition-all"
        >
          {{ submitting ? 'Sending...' : '📤 Send Report' }}
        </button>
      </form>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="text-center py-16">
      <div class="text-2xl text-slate-400 animate-pulse">Loading...</div>
    </div>

    <!-- Service Requests List -->
    <div v-else class="space-y-4">
      <div v-if="serviceRequests.length === 0" class="bg-white rounded-xl shadow-lg p-12 text-center text-slate-500 text-lg border-2 border-slate-200">
        No reports yet — you're good to go!
      </div>

      <div
        v-for="request in serviceRequests"
        :key="request.id"
        class="bg-white rounded-xl shadow-lg p-6 border-2 transition-all"
        :class="{
          'border-red-500 bg-red-50': request.priority === 'urgent',
          'border-orange-500 bg-orange-50': request.priority === 'high',
          'border-yellow-500 bg-yellow-50': request.priority === 'medium',
          'border-slate-200': request.priority === 'low'
        }"
      >
        <div class="flex justify-between items-start mb-4">
          <div class="flex-1">
            <h3 class="font-bold text-2xl text-slate-900">{{ request.title }}</h3>
            <p class="text-slate-700 mt-1 text-base font-medium">{{ request.work_site_name }}</p>
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

        <div class="space-y-2 mb-4 text-base">
          <div>
            <span class="font-bold text-slate-700">Type:</span>
            <span class="text-slate-900 ml-2">{{ request.issue_type_display }}</span>
          </div>
          <div v-if="request.location_detail">
            <span class="font-bold text-slate-700">Where:</span>
            <span class="text-slate-900 ml-2">{{ request.location_detail }}</span>
          </div>
          <div>
            <span class="font-bold text-slate-700">Sent:</span>
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
import { workerFetch } from '../api'

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
  if (!token) {
    loading.value = false
    return
  }

  try {
    const response = await workerFetch('/api/worker/service-requests/')

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
  if (!token) return

  try {
    const response = await workerFetch('/api/worker/work-sites/')

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
  if (!token) {
    submitError.value = 'Please log in again.'
    submitting.value = false
    return
  }

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

    const response = await workerFetch('/api/worker/service-requests/', {
      method: 'POST',
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
