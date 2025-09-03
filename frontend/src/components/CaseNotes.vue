<template>
  <div class="max-w-4xl mx-auto p-6">
    <!-- Header -->
    <div class="mb-8">
      <h1 class="text-3xl font-bold text-slate-900 mb-2">Case Notes</h1>
      <p class="text-slate-600">Track client interactions and progress</p>
    </div>

    <!-- Client Search -->
    <div class="bg-white rounded-xl shadow-lg p-6 mb-6">
      <h2 class="text-xl font-semibold text-slate-800 mb-4">Find Client</h2>
      <div class="flex gap-4">
        <input 
          v-model="searchQuery" 
          type="text" 
          placeholder="Search by name, phone, or SSN..."
          class="flex-1 px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-mission-500 focus:border-transparent"
        />
        <button 
          @click="searchClients"
          class="px-6 py-2 bg-mission-600 text-white rounded-lg hover:bg-mission-700 transition-colors"
        >
          Search
        </button>
      </div>
    </div>

    <!-- Client Results -->
    <div v-if="searchResults.length > 0" class="bg-white rounded-xl shadow-lg p-6 mb-6">
      <h3 class="text-lg font-semibold text-slate-800 mb-4">Search Results</h3>
      <div class="space-y-3">
        <div 
          v-for="client in searchResults" 
          :key="client.id"
          class="border border-slate-200 rounded-lg p-4 hover:bg-slate-50 cursor-pointer"
          @click="selectClient(client)"
        >
          <div class="flex justify-between items-start">
            <div>
              <h4 class="font-semibold text-slate-900">{{ client.first_name }} {{ client.last_name }}</h4>
              <p class="text-slate-600 text-sm">{{ client.phone }}</p>
              <p class="text-slate-500 text-xs">{{ client.neighborhood }} • {{ client.training_interest }}</p>
            </div>
            <div class="text-right">
              <span class="inline-flex px-2 py-1 text-xs font-medium rounded-full" 
                    :class="getStatusClass(client.status)">
                {{ client.status }}
              </span>
              <p class="text-xs text-slate-500 mt-1">{{ client.case_notes_count || 0 }} notes</p>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Selected Client Case Notes -->
    <div v-if="selectedClient" class="bg-white rounded-xl shadow-lg p-6 mb-6">
      <div class="flex justify-between items-start mb-6">
        <div>
          <h2 class="text-2xl font-bold text-slate-900">{{ selectedClient.first_name }} {{ selectedClient.last_name }}</h2>
          <p class="text-slate-600">{{ selectedClient.phone }} • {{ selectedClient.neighborhood }}</p>
          <p class="text-slate-500 text-sm">Training Interest: {{ selectedClient.training_interest }}</p>
        </div>
        <button 
          @click="selectedClient = null"
          class="text-slate-400 hover:text-slate-600"
        >
          <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
          </svg>
        </button>
      </div>

      <!-- Add New Case Note -->
      <div class="border border-slate-200 rounded-lg p-4 mb-6">
        <h3 class="text-lg font-semibold text-slate-800 mb-4">Add New Case Note</h3>
        <form @submit.prevent="addCaseNote" class="space-y-4">
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label class="block text-sm font-medium text-slate-700 mb-2">Note Type</label>
              <select v-model="newNote.note_type" class="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-mission-500 focus:border-transparent">
                <option value="intake">Intake Meeting</option>
                <option value="follow_up">Follow-up Call/Visit</option>
                <option value="training">Training Progress</option>
                <option value="job_search">Job Search Support</option>
                <option value="placement">Job Placement</option>
                <option value="barrier">Barrier Assessment</option>
                <option value="referral">Referral to Service</option>
                <option value="general">General Note</option>
              </select>
            </div>
            <div>
              <label class="block text-sm font-medium text-slate-700 mb-2">Staff Member</label>
              <input 
                v-model="newNote.staff_member" 
                type="text" 
                placeholder="Your name"
                class="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-mission-500 focus:border-transparent"
                required
              />
            </div>
          </div>
          
          <div>
            <label class="block text-sm font-medium text-slate-700 mb-2">Note Content</label>
            <textarea 
              v-model="newNote.content" 
              rows="4"
              placeholder="Describe the interaction, progress, or next steps..."
              class="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-mission-500 focus:border-transparent"
              required
            ></textarea>
          </div>
          
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label class="block text-sm font-medium text-slate-700 mb-2">Next Steps</label>
              <textarea 
                v-model="newNote.next_steps" 
                rows="2"
                placeholder="What needs to happen next?"
                class="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-mission-500 focus:border-transparent"
              ></textarea>
            </div>
            <div>
              <label class="block text-sm font-medium text-slate-700 mb-2">Follow-up Date</label>
              <input 
                v-model="newNote.follow_up_date" 
                type="date"
                class="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-mission-500 focus:border-transparent"
              />
            </div>
          </div>
          
          <div class="flex justify-end">
            <button 
              type="submit"
              class="px-6 py-2 bg-mission-600 text-white rounded-lg hover:bg-mission-700 transition-colors"
              :disabled="isSubmitting"
            >
              {{ isSubmitting ? 'Adding...' : 'Add Case Note' }}
            </button>
          </div>
        </form>
      </div>

      <!-- Existing Case Notes -->
      <div>
        <h3 class="text-lg font-semibold text-slate-800 mb-4">Case History</h3>
        <div v-if="caseNotes.length === 0" class="text-center py-8 text-slate-500">
          No case notes yet. Add your first note above.
        </div>
        <div v-else class="space-y-4">
          <div 
            v-for="note in caseNotes" 
            :key="note.id"
            class="border border-slate-200 rounded-lg p-4"
          >
            <div class="flex justify-between items-start mb-2">
              <div class="flex items-center gap-2">
                <span class="inline-flex px-2 py-1 text-xs font-medium rounded-full bg-mission-100 text-mission-800">
                  {{ note.note_type.replace('_', ' ').toUpperCase() }}
                </span>
                <span class="text-sm text-slate-500">{{ note.staff_member }}</span>
              </div>
              <div class="text-right">
                <p class="text-sm text-slate-600">{{ formatDate(note.created_at) }}</p>
                <p v-if="note.follow_up_date" class="text-xs text-slate-500">
                  Follow-up: {{ formatDate(note.follow_up_date) }}
                </p>
              </div>
            </div>
            
            <div class="prose prose-sm max-w-none">
              <p class="text-slate-800 mb-2">{{ note.content }}</p>
              <p v-if="note.next_steps" class="text-slate-700 text-sm">
                <strong>Next Steps:</strong> {{ note.next_steps }}
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'
import { getApiUrl } from '../config/api'

const searchQuery = ref('')
const searchResults = ref([])
const selectedClient = ref(null)
const caseNotes = ref([])
const isSubmitting = ref(false)

const newNote = ref({
  note_type: 'general',
  staff_member: '',
  content: '',
  next_steps: '',
  follow_up_date: ''
})

const searchClients = async () => {
  if (!searchQuery.value.trim()) return
  
  try {
            const response = await axios.get(getApiUrl(`/api/clients/?search=${searchQuery.value}`))
    searchResults.value = response.data.results || response.data
  } catch (error) {
    console.error('Error searching clients:', error)
    searchResults.value = []
  }
}

const selectClient = async (client) => {
  selectedClient.value = client
  await loadCaseNotes(client.id)
}

const loadCaseNotes = async (clientId) => {
  try {
            const response = await axios.get(getApiUrl(`/api/clients/${clientId}/case-notes/`))
    caseNotes.value = response.data
  } catch (error) {
    console.error('Error loading case notes:', error)
    caseNotes.value = []
  }
}

const addCaseNote = async () => {
  if (!selectedClient.value) return
  
  isSubmitting.value = true
  
  try {
    const noteData = {
      ...newNote.value,
      client: selectedClient.value.id
    }
    
            const response = await axios.post(getApiUrl('/api/case-notes/'), noteData)
    
    // Add to local list
    caseNotes.value.unshift(response.data)
    
    // Reset form
    newNote.value = {
      note_type: 'general',
      staff_member: newNote.value.staff_member, // Keep staff member
      content: '',
      next_steps: '',
      follow_up_date: ''
    }
    
    // Update client case notes count
    selectedClient.value.case_notes_count = (selectedClient.value.case_notes_count || 0) + 1
    
  } catch (error) {
    console.error('Error adding case note:', error)
    alert('Error adding case note. Please try again.')
  } finally {
    isSubmitting.value = false
  }
}

const formatDate = (dateString) => {
  return new Date(dateString).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

const getStatusClass = (status) => {
  const classes = {
    'pending': 'bg-yellow-100 text-yellow-800',
    'active': 'bg-green-100 text-green-800',
    'completed': 'bg-blue-100 text-blue-800',
    'inactive': 'bg-gray-100 text-gray-800'
  }
  return classes[status] || 'bg-gray-100 text-gray-800'
}

// Load staff member name from localStorage if available
onMounted(() => {
  const savedStaffMember = localStorage.getItem('staff_member')
  if (savedStaffMember) {
    newNote.value.staff_member = savedStaffMember
  }
})
</script>
