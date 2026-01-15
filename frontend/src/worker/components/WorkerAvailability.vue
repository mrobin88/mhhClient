<template>
  <div class="space-y-6">
    <div class="flex justify-between items-center">
      <h1 class="text-3xl font-bold text-gray-900">My Availability</h1>
      <button
        @click="saveAvailability"
        :disabled="saving"
        class="bg-blue-600 hover:bg-blue-700 text-white px-6 py-2 rounded-lg font-medium disabled:opacity-50"
      >
        {{ saving ? 'Saving...' : '💾 Save Changes' }}
      </button>
    </div>

    <div v-if="successMessage" class="bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded-lg">
      {{ successMessage }}
    </div>

    <div v-if="errorMessage" class="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
      {{ errorMessage }}
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="text-center py-12">
      <div class="text-gray-500">Loading availability...</div>
    </div>

    <!-- Availability Grid -->
    <div v-else class="bg-white rounded-lg shadow overflow-hidden">
      <div class="p-6">
        <p class="text-gray-600 mb-6">
          Set your weekly availability. Select the days you're available and your preferred time slots.
        </p>

        <div class="space-y-4">
          <div
            v-for="day in daysOfWeek"
            :key="day.value"
            class="border border-gray-200 rounded-lg p-4"
          >
            <div class="flex items-start gap-4">
              <!-- Available Toggle -->
              <div class="flex items-center h-10">
                <input
                  :id="`available-${day.value}`"
                  v-model="availability[day.value].available"
                  type="checkbox"
                  class="w-5 h-5 text-blue-600 rounded focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <!-- Day Info -->
              <div class="flex-1">
                <label :for="`available-${day.value}`" class="block font-semibold text-lg text-gray-900 cursor-pointer">
                  {{ day.label }}
                </label>

                <!-- Time Slots (shown only if available) -->
                <div v-if="availability[day.value].available" class="mt-3 space-y-2">
                  <p class="text-sm text-gray-600 font-medium">Preferred Time Slots:</p>
                  <div class="grid grid-cols-1 sm:grid-cols-3 gap-2">
                    <label
                      v-for="slot in timeSlots"
                      :key="slot.value"
                      class="flex items-center gap-2 cursor-pointer"
                    >
                      <input
                        v-model="availability[day.value].preferred_time_slots"
                        :value="slot.value"
                        type="checkbox"
                        class="w-4 h-4 text-blue-600 rounded focus:ring-2 focus:ring-blue-500"
                      />
                      <span class="text-sm text-gray-700">{{ slot.label }}</span>
                    </label>
                  </div>

                  <!-- Notes -->
                  <div class="mt-3">
                    <label class="block text-sm text-gray-600 font-medium mb-1">
                      Notes (optional):
                    </label>
                    <input
                      v-model="availability[day.value].notes"
                      type="text"
                      placeholder="e.g., 'Available after 2pm'"
                      class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500"
                    />
                  </div>
                </div>

                <div v-else class="mt-2 text-sm text-gray-500 italic">
                  Not available on {{ day.label }}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Help Text -->
    <div class="bg-blue-50 border border-blue-200 rounded-lg p-4">
      <h3 class="font-semibold text-blue-900 mb-2">💡 Tips:</h3>
      <ul class="text-sm text-blue-800 space-y-1">
        <li>• Check the days you're available to work</li>
        <li>• Select your preferred time slots for each day</li>
        <li>• Add notes if you have specific time restrictions</li>
        <li>• Click "Save Changes" when you're done</li>
        <li>• Your supervisor will use this to schedule assignments</li>
      </ul>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, reactive } from 'vue'
import { workerFetch } from '../api'

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
  { value: '6-12', label: '6am-12pm' },
  { value: '13-21', label: '1pm-9pm' },
  { value: '22-5', label: '10pm-5am' }
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
