<template>
  <div class="min-h-screen bg-gradient py-8 px-4">
    <!-- Header -->
    <div class="max-w-7xl mx-auto mb-8">
      <div class="text-center">
        <h1 class="text-4xl font-bold text-slate-800 mb-2">
          <span class="text-mission-600">Mission Hiring Hall</span> Staff Dashboard
        </h1>
        <p class="text-xl text-slate-600">Client Management & Reporting System</p>
      </div>
    </div>

    <!-- Main Dashboard -->
    <div class="max-w-7xl mx-auto">
      <!-- Search & Filters Bar -->
      <div class="bg-white rounded-2xl shadow-lg p-6 mb-8">
        <div class="grid grid-cols-1 lg:grid-cols-4 gap-4">
          <!-- Search Input -->
          <div class="lg:col-span-2">
            <label class="block text-sm font-semibold text-slate-700 mb-2">Search Clients</label>
            <div class="relative">
              <input 
                v-model="searchQuery" 
                type="text" 
                placeholder="Search by name, phone, SSN, or staff..."
                class="form-input w-full pl-10"
                @input="handleSearch"
              />
              <svg class="absolute left-3 top-3 w-5 h-5 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/>
              </svg>
            </div>
          </div>

          <!-- Status Filter -->
          <div>
            <label class="block text-sm font-semibold text-slate-700 mb-2">Status</label>
            <select v-model="statusFilter" class="form-select" @change="handleFilter">
              <option value="">All Statuses</option>
              <option value="active">Active</option>
              <option value="completed">Completed</option>
              <option value="pending">Pending</option>
            </select>
          </div>

          <!-- Program Filter -->
          <div>
            <label class="block text-sm font-semibold text-slate-700 mb-2">Program</label>
            <select v-model="programFilter" class="form-select" @change="handleFilter">
              <option value="">All Programs</option>
              <option value="citybuild">CityBuild Academy</option>
              <option value="citybuild_pro">CityBuild Pro | CAPSA</option>
              <option value="security">Security Guard Card</option>
              <option value="construction">Construction On Ramp</option>
              <option value="pit_stop">Pit Stop Program</option>
              <option value="general">General Job Readiness</option>
            </select>
          </div>
        </div>

        <!-- Advanced Filters -->
        <div class="mt-4 pt-4 border-t border-slate-200">
          <button 
            @click="showAdvancedFilters = !showAdvancedFilters"
            class="text-mission-600 hover:text-mission-700 font-medium flex items-center"
          >
            <svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/>
            </svg>
            Advanced Filters
          </button>
          
          <div v-if="showAdvancedFilters" class="mt-4 grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label class="block text-sm font-semibold text-slate-700 mb-2">Neighborhood</label>
              <select v-model="neighborhoodFilter" class="form-select" @change="handleFilter">
                <option value="">All Areas</option>
                <option value="mission">Mission District</option>
                <option value="soma">South of Market</option>
                <option value="bayview">Bayview-Hunters Point</option>
                <option value="tenderloin">Tenderloin</option>
                <option value="western">Western Addition</option>
              </select>
            </div>
            
            <div>
              <label class="block text-sm font-semibold text-slate-700 mb-2">Date Range</label>
              <select v-model="dateFilter" class="form-select" @change="handleFilter">
                <option value="">All Time</option>
                <option value="today">Today</option>
                <option value="week">This Week</option>
                <option value="month">This Month</option>
                <option value="quarter">This Quarter</option>
                <option value="year">This Year</option>
              </select>
            </div>
            
            <div>
              <label class="block text-sm font-semibold text-slate-700 mb-2">Staff Member</label>
              <select v-model="staffFilter" class="form-select" @change="handleFilter">
                <option value="">All Staff</option>
                <option v-for="staff in staffMembers" :key="staff" :value="staff">{{ staff }}</option>
              </select>
            </div>
          </div>
        </div>
      </div>

      <!-- Statistics Cards -->
      <div class="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
        <div class="bg-white rounded-2xl shadow-lg p-6">
          <div class="flex items-center">
            <div class="p-3 bg-mission-100 rounded-full">
              <svg class="w-6 h-6 text-mission-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"/>
              </svg>
            </div>
            <div class="ml-4">
              <p class="text-sm font-medium text-slate-600">Total Clients</p>
              <p class="text-2xl font-bold text-slate-900">{{ statistics.totalClients }}</p>
            </div>
          </div>
        </div>

        <div class="bg-white rounded-2xl shadow-lg p-6">
          <div class="flex items-center">
            <div class="p-3 bg-green-100 rounded-full">
              <svg class="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
              </svg>
            </div>
            <div class="ml-4">
              <p class="text-sm font-medium text-slate-600">Active Programs</p>
              <p class="text-2xl font-bold text-slate-900">{{ statistics.activePrograms }}</p>
            </div>
          </div>
        </div>

        <div class="bg-white rounded-2xl shadow-lg p-6">
          <div class="flex items-center">
            <div class="p-3 bg-blue-100 rounded-full">
              <svg class="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/>
              </svg>
            </div>
            <div class="ml-4">
              <p class="text-sm font-medium text-slate-600">This Month</p>
              <p class="text-2xl font-bold text-slate-900">{{ statistics.thisMonth }}</p>
            </div>
          </div>
        </div>

        <div class="bg-white rounded-2xl shadow-lg p-6">
          <div class="flex items-center">
            <div class="p-3 bg-purple-100 rounded-full">
              <svg class="w-6 h-6 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"/>
              </svg>
            </div>
            <div class="ml-4">
              <p class="text-sm font-medium text-slate-600">Success Rate</p>
              <p class="text-2xl font-bold text-slate-900">{{ statistics.successRate }}%</p>
            </div>
          </div>
        </div>
      </div>

      <!-- Clients Table -->
      <div class="bg-white rounded-2xl shadow-lg overflow-hidden">
        <div class="px-6 py-4 border-b border-slate-200">
          <div class="flex items-center justify-between">
            <h3 class="text-lg font-semibold text-slate-800">Client Records</h3>
            <div class="flex items-center space-x-4">
              <span class="text-sm text-slate-600">{{ filteredClients.length }} of {{ clients.length }} clients</span>
              <button 
                @click="exportData"
                class="bg-mission-600 hover:bg-mission-700 text-white px-4 py-2 rounded-lg font-medium transition-colors"
              >
                Export Data
              </button>
            </div>
          </div>
        </div>

        <div class="overflow-x-auto">
          <table class="min-w-full divide-y divide-slate-200">
            <thead class="bg-slate-50">
              <tr>
                <th class="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Client</th>
                <th class="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Contact</th>
                <th class="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Program</th>
                <th class="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Status</th>
                <th class="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Staff</th>
                <th class="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Date</th>
                <th class="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Actions</th>
              </tr>
            </thead>
            <tbody class="bg-white divide-y divide-slate-200">
              <tr v-for="client in paginatedClients" :key="client.id" class="hover:bg-slate-50">
                <td class="px-6 py-4 whitespace-nowrap">
                  <div class="flex items-center">
                    <div class="flex-shrink-0 h-10 w-10">
                      <div class="h-10 w-10 rounded-full bg-mission-100 flex items-center justify-center">
                        <span class="text-sm font-medium text-mission-600">
                          {{ client.first_name.charAt(0) }}{{ client.last_name.charAt(0) }}
                        </span>
                      </div>
                    </div>
                    <div class="ml-4">
                      <div class="text-sm font-medium text-slate-900">
                        {{ client.first_name }} {{ client.last_name }}
                      </div>
                      <div class="text-sm text-slate-500">
                        {{ client.neighborhood || 'N/A' }}
                      </div>
                    </div>
                  </div>
                </td>
                <td class="px-6 py-4 whitespace-nowrap">
                  <div class="text-sm text-slate-900">{{ client.phone || 'N/A' }}</div>
                  <div class="text-sm text-slate-500">{{ client.language || 'N/A' }}</div>
                </td>
                <td class="px-6 py-4 whitespace-nowrap">
                  <span class="inline-flex px-2 py-1 text-xs font-semibold rounded-full" 
                        :class="getProgramBadgeClass(client.training_interest)">
                    {{ getProgramLabel(client.training_interest) }}
                  </span>
                </td>
                <td class="px-6 py-4 whitespace-nowrap">
                  <span class="inline-flex px-2 py-1 text-xs font-semibold rounded-full" 
                        :class="getStatusBadgeClass(client.status)">
                    {{ getStatusLabel(client.status) }}
                  </span>
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-slate-900">
                  {{ client.staff_name || 'Unassigned' }}
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-slate-500">
                  {{ formatDate(client.created_at) }}
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm font-medium">
                  <button 
                    @click="viewClient(client)"
                    class="text-mission-600 hover:text-mission-900 mr-3"
                  >
                    View
                  </button>
                  <button 
                    @click="editClient(client)"
                    class="text-slate-600 hover:text-slate-900 mr-3"
                  >
                    Edit
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- Pagination -->
        <div class="bg-white px-6 py-3 border-t border-slate-200">
          <div class="flex items-center justify-between">
            <div class="flex items-center">
              <span class="text-sm text-slate-700">
                Showing {{ startIndex + 1 }} to {{ endIndex }} of {{ filteredClients.length }} results
              </span>
            </div>
            <div class="flex items-center space-x-2">
              <button 
                @click="previousPage"
                :disabled="currentPage === 1"
                class="px-3 py-1 text-sm font-medium text-slate-500 bg-white border border-slate-300 rounded-md hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Previous
              </button>
              <span class="text-sm text-slate-700">
                Page {{ currentPage }} of {{ totalPages }}
              </span>
              <button 
                @click="nextPage"
                :disabled="currentPage === totalPages"
                class="px-3 py-1 text-sm font-medium text-slate-500 bg-white border border-slate-300 rounded-md hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Next
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Client Detail Modal -->
    <div v-if="selectedClient" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div class="bg-white rounded-2xl max-w-4xl w-full max-h-[90vh] overflow-y-auto">
        <div class="p-6 border-b border-slate-200">
          <div class="flex items-center justify-between">
            <h3 class="text-xl font-semibold text-slate-800">
              Client Details: {{ selectedClient.first_name }} {{ selectedClient.last_name }}
            </h3>
            <button @click="selectedClient = null" class="text-slate-400 hover:text-slate-600">
              <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
              </svg>
            </button>
          </div>
        </div>
        
        <div class="p-6">
          <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <h4 class="font-semibold text-slate-800 mb-3">Personal Information</h4>
              <div class="space-y-2 text-sm">
                <div><span class="font-medium">Name:</span> {{ selectedClient.first_name }} {{ selectedClient.last_name }}</div>
                <div><span class="font-medium">DOB:</span> {{ formatDate(selectedClient.dob) }}</div>
                <div><span class="font-medium">Phone:</span> {{ selectedClient.phone || 'N/A' }}</div>
                <div><span class="font-medium">SSN:</span> {{ selectedClient.ssn || 'N/A' }}</div>
                <div><span class="font-medium">Gender:</span> {{ selectedClient.gender || 'N/A' }}</div>
              </div>
            </div>
            
            <div>
              <h4 class="font-semibold text-slate-800 mb-3">Program Information</h4>
              <div class="space-y-2 text-sm">
                <div><span class="font-medium">Program:</span> {{ getProgramLabel(selectedClient.training_interest) }}</div>
                <div><span class="font-medium">Status:</span> {{ getStatusLabel(selectedClient.status) }}</div>
                <div><span class="font-medium">Staff:</span> {{ selectedClient.staff_name || 'Unassigned' }}</div>
                <div><span class="font-medium">Neighborhood:</span> {{ selectedClient.neighborhood || 'N/A' }}</div>
                <div><span class="font-medium">Language:</span> {{ selectedClient.language || 'N/A' }}</div>
              </div>
            </div>
          </div>
          
          <div class="mt-6 pt-6 border-t border-slate-200">
            <h4 class="font-semibold text-slate-800 mb-3">Additional Notes</h4>
            <p class="text-sm text-slate-600">{{ selectedClient.additional_notes || 'No additional notes' }}</p>
          </div>
        </div>
        
        <div class="p-6 border-t border-slate-200 bg-slate-50">
          <div class="flex justify-end space-x-3">
            <button 
              @click="editClient(selectedClient)"
              class="bg-mission-600 hover:bg-mission-700 text-white px-4 py-2 rounded-lg font-medium"
            >
              Edit Client
            </button>
            <button 
              @click="selectedClient = null"
              class="bg-slate-300 hover:bg-slate-400 text-slate-700 px-4 py-2 rounded-lg font-medium"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import axios from 'axios'

// Reactive data
const clients = ref([])
const searchQuery = ref('')
const statusFilter = ref('')
const programFilter = ref('')
const neighborhoodFilter = ref('')
const dateFilter = ref('')
const staffFilter = ref('')
const showAdvancedFilters = ref(false)
const selectedClient = ref(null)
const currentPage = ref(1)
const itemsPerPage = 20

// Computed properties
const filteredClients = computed(() => {
  let filtered = clients.value

  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    filtered = filtered.filter(client => 
      client.first_name?.toLowerCase().includes(query) ||
      client.last_name?.toLowerCase().includes(query) ||
      client.phone?.includes(query) ||
      client.ssn?.includes(query) ||
      client.staff_name?.toLowerCase().includes(query)
    )
  }

  if (statusFilter.value) {
    filtered = filtered.filter(client => client.status === statusFilter.value)
  }

  if (programFilter.value) {
    filtered = filtered.filter(client => client.training_interest === programFilter.value)
  }

  if (neighborhoodFilter.value) {
    filtered = filtered.filter(client => client.neighborhood === neighborhoodFilter.value)
  }

  if (staffFilter.value) {
    filtered = filtered.filter(client => client.staff_name === staffFilter.value)
  }

  return filtered
})

const paginatedClients = computed(() => {
  const start = (currentPage.value - 1) * itemsPerPage
  const end = start + itemsPerPage
  return filteredClients.value.slice(start, end)
})

const totalPages = computed(() => Math.ceil(filteredClients.value.length / itemsPerPage))
const startIndex = computed(() => (currentPage.value - 1) * itemsPerPage)
const endIndex = computed(() => Math.min(startIndex.value + itemsPerPage, filteredClients.value.length))

const statistics = computed(() => ({
  totalClients: clients.value.length,
  activePrograms: new Set(clients.value.map(c => c.training_interest)).size,
  thisMonth: clients.value.filter(c => {
    const clientDate = new Date(c.created_at)
    const now = new Date()
    return clientDate.getMonth() === now.getMonth() && clientDate.getFullYear() === now.getFullYear()
  }).length,
  successRate: Math.round((clients.value.filter(c => c.status === 'completed').length / clients.value.length) * 100) || 0
}))

const staffMembers = computed(() => {
  const staff = new Set(clients.value.map(c => c.staff_name).filter(Boolean))
  return Array.from(staff).sort()
})

// Methods
const fetchClients = async () => {
  try {
    const response = await axios.get('http://localhost:8000/api/clients/')
    clients.value = response.data
  } catch (error) {
    console.error('Error fetching clients:', error)
  }
}

const handleSearch = () => {
  currentPage.value = 1
}

const handleFilter = () => {
  currentPage.value = 1
}

const previousPage = () => {
  if (currentPage.value > 1) {
    currentPage.value--
  }
}

const nextPage = () => {
  if (currentPage.value < totalPages.value) {
    currentPage.value++
  }
}

const viewClient = (client) => {
  selectedClient.value = client
}

const editClient = (client) => {
  // TODO: Implement edit functionality
  console.log('Edit client:', client)
}

const exportData = () => {
  // TODO: Implement export functionality
  console.log('Export data')
}

const getProgramLabel = (program) => {
  const labels = {
    'citybuild': 'CityBuild Academy',
    'citybuild_pro': 'CityBuild Pro | CAPSA',
    'security': 'Security Guard Card',
    'construction': 'Construction On Ramp',
    'pit_stop': 'Pit Stop Program',
    'general': 'General Job Readiness'
  }
  return labels[program] || program || 'N/A'
}

const getProgramBadgeClass = (program) => {
  const classes = {
    'citybuild': 'bg-blue-100 text-blue-800',
    'citybuild_pro': 'bg-purple-100 text-purple-800',
    'security': 'bg-green-100 text-green-800',
    'construction': 'bg-orange-100 text-orange-800',
    'pit_stop': 'bg-red-100 text-red-800',
    'general': 'bg-gray-100 text-gray-800'
  }
  return classes[program] || 'bg-gray-100 text-gray-800'
}

const getStatusLabel = (status) => {
  const labels = {
    'active': 'Active',
    'completed': 'Completed',
    'pending': 'Pending'
  }
  return labels[status] || 'Unknown'
}

const getStatusBadgeClass = (status) => {
  const classes = {
    'active': 'bg-green-100 text-green-800',
    'completed': 'bg-blue-100 text-blue-800',
    'pending': 'bg-yellow-100 text-yellow-800'
  }
  return classes[status] || 'bg-gray-100 text-gray-800'
}

const formatDate = (dateString) => {
  if (!dateString) return 'N/A'
  return new Date(dateString).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric'
  })
}

// Lifecycle
onMounted(() => {
  fetchClients()
})
</script>

<style scoped>
/* All styles are handled by Tailwind CSS classes in style.css */
</style>
