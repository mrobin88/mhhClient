<template>
  <div class="space-y-4">
    <div class="flex justify-between items-center mb-2">
      <h1 class="text-2xl font-bold text-slate-900">My Schedule</h1>
      <button
        @click="saveAvailability"
        :disabled="saving"
        class="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg font-bold transition-all disabled:opacity-50"
      >
        {{ saving ? '...' : '💾 Save' }}
      </button>
    </div>

    <div v-if="successMessage" class="bg-green-50 border-2 border-green-300 text-green-800 px-5 py-4 rounded-xl font-medium shadow-sm">
      ✅ {{ successMessage }}
    </div>

    <div v-if="errorMessage" class="bg-red-50 border-2 border-red-300 text-red-800 px-5 py-4 rounded-xl font-medium shadow-sm">
      ❌ {{ errorMessage }}
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="text-center py-16">
      <div class="text-2xl text-slate-400 animate-pulse">Loading...</div>
    </div>

    <!-- Quick Actions -->
    <div v-else class="flex gap-3 mb-6">
      <button
        @click="selectAllDays"
        class="flex-1 bg-green-50 hover:bg-green-100 border-2 border-green-300 text-green-800 px-4 py-3 rounded-xl font-bold transition-all"
      >
        ✅ All Days
      </button>
      <button
        @click="selectWeekdays"
        class="flex-1 bg-blue-50 hover:bg-blue-100 border-2 border-blue-300 text-blue-800 px-4 py-3 rounded-xl font-bold transition-all"
      >
        📅 Weekdays
      </button>
      <button
        @click="clearAll"
        class="flex-1 bg-slate-50 hover:bg-slate-100 border-2 border-slate-300 text-slate-700 px-4 py-3 rounded-xl font-bold transition-all"
      >
        ⬜ Clear All
      </button>
    </div>

    <!-- Availability Grid -->
    <div v-else class="space-y-3">
      <div
        v-for="day in daysOfWeek"
        :key="day.value"
        :class="[
          'bg-white rounded-xl border-2 transition-all overflow-hidden',
          availability[day.value].available 
            ? 'border-blue-400 shadow-md' 
            : 'border-slate-200'
        ]"
      >
        <!-- Day Header -->
        <div class="p-5">
          <label :for="`available-${day.value}`" class="flex items-center gap-4 cursor-pointer">
            <input
              :id="`available-${day.value}`"
              v-model="availability[day.value].available"
              type="checkbox"
              class="w-7 h-7 text-blue-600 rounded-lg focus:ring-2 focus:ring-blue-500 cursor-pointer"
            />
            <div class="flex-1">
              <div class="text-2xl font-bold text-slate-900">{{ day.label }}</div>
              <div v-if="!availability[day.value].available" class="text-sm text-slate-500">
                Not available
              </div>
            </div>
            <div v-if="availability[day.value].available" class="text-3xl">✅</div>
          </label>

          <!-- Time Slots (shown only if available) -->
          <div v-if="availability[day.value].available" class="mt-5 pl-11 space-y-4">
            <div>
              <div class="flex items-center gap-2 mb-3">
                <span class="text-sm font-bold text-slate-700">Pick Time Slots:</span>
                <Tooltip text="Select when you prefer to work this day. You can pick multiple.">
                  <span></span>
                </Tooltip>
              </div>
              <div class="grid grid-cols-1 gap-2">
                <label
                  v-for="slot in timeSlots"
                  :key="slot.value"
                  :class="[
                    'flex items-center gap-3 p-3 rounded-lg border-2 cursor-pointer transition-all',
                    availability[day.value].preferred_time_slots.includes(slot.value)
                      ? 'border-blue-500 bg-blue-50'
                      : 'border-slate-200 hover:border-slate-300'
                  ]"
                >
                  <input
                    v-model="availability[day.value].preferred_time_slots"
                    :value="slot.value"
                    type="checkbox"
                    class="w-5 h-5 text-blue-600 rounded focus:ring-2 focus:ring-blue-500 cursor-pointer"
                  />
                  <span class="text-lg font-semibold text-slate-800">{{ slot.label }}</span>
                </label>
              </div>
            </div>

            <!-- Notes -->
            <details class="group">
              <summary class="text-sm font-bold text-slate-700 cursor-pointer hover:text-blue-600 transition">
                + Add Note (optional)
              </summary>
              <div class="mt-2">
                <input
                  v-model="availability[day.value].notes"
                  type="text"
                  placeholder="e.g., 'Can start at 2pm'"
                  class="w-full px-4 py-3 border-2 border-slate-300 rounded-lg text-base focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                />
              </div>
            </details>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, reactive } from 'vue'
import { workerFetch } from '../api'
import Tooltip from './Tooltip.vue'

const loading = ref(false)
const saving = ref(false)
const successMessage = ref('')
const errorMessage = ref('')

const daysOfWeek = [
  { value: 'monday', label: 'Monday' },
  { value: 'tuesday', label: 'Tuesday' },
  { value: 'wednesday', label: 'Wednesday' },
  { value: 'thursday', label: 'Thursday' },
  { value: 'friday', label: 'Friday' },
  { value: 'saturday', label: 'Saturday' },
  { value: 'sunday', label: 'Sunday' }
]

const timeSlots = [
  { value: '6-12', label: 'Morning (6am-12pm)' },
  { value: '13-21', label: 'Afternoon (1pm-9pm)' },
  { value: '22-5', label: 'Night (10pm-5am)' }
]

const availability = reactive<any>({
  monday: { available: false, preferred_time_slots: [], notes: '' },
  tuesday: { available: false, preferred_time_slots: [], notes: '' },
  wednesday: { available: false, preferred_time_slots: [], notes: '' },
  thursday: { available: false, preferred_time_slots: [], notes: '' },
  friday: { available: false, preferred_time_slots: [], notes: '' },
  saturday: { available: false, preferred_time_slots: [], notes: '' },
  sunday: { available: false, preferred_time_slots: [], notes: '' }
})

function selectAllDays() {
  daysOfWeek.forEach(day => {
    availability[day.value].available = true
  })
}

function selectWeekdays() {
  const weekdays = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday']
  daysOfWeek.forEach(day => {
    availability[day.value].available = weekdays.includes(day.value)
  })
}

function clearAll() {
  daysOfWeek.forEach(day => {
    availability[day.value].available = false
    availability[day.value].preferred_time_slots = []
    availability[day.value].notes = ''
  })
}

async function loadAvailability() {
  loading.value = true
  const token = localStorage.getItem('worker_token')
  if (!token) {
    loading.value = false
    return
  }

  try {
    const response = await workerFetch('/api/worker/availability/')

    if (response.ok) {
      const data = await response.json()
      
      // Populate availability from API response
      data.forEach((item: any) => {
        const day = item.day_of_week
        if (availability[day]) {
          availability[day].available = item.available
          availability[day].preferred_time_slots = item.preferred_time_slots || []
          availability[day].notes = item.notes || ''
        }
      })
    }
  } catch (err) {
    console.error('Failed to load availability:', err)
    errorMessage.value = 'Failed to load availability'
  } finally {
    loading.value = false
  }
}

async function saveAvailability() {
  saving.value = true
  successMessage.value = ''
  errorMessage.value = ''
  const token = localStorage.getItem('worker_token')
  if (!token) {
    saving.value = false
    errorMessage.value = 'Please log in again.'
    return
  }

  // Convert availability object to array
  const availabilityArray = Object.keys(availability).map(day => ({
    day_of_week: day,
    available: availability[day].available,
    preferred_time_slots: availability[day].preferred_time_slots,
    notes: availability[day].notes
  }))

  try {
    const response = await workerFetch('/api/worker/availability/', {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(availabilityArray)
    })

    if (response.ok) {
      successMessage.value = 'Availability saved successfully!'
      setTimeout(() => {
        successMessage.value = ''
      }, 3000)
    } else {
      errorMessage.value = 'Failed to save availability'
    }
  } catch (err) {
    console.error('Failed to save availability:', err)
    errorMessage.value = 'Network error. Please try again.'
  } finally {
    saving.value = false
  }
}

onMounted(() => {
  loadAvailability()
})
</script>
