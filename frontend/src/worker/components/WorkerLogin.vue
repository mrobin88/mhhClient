<template>
  <div class="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-blue-100 px-4">
    <div class="max-w-md w-full bg-white rounded-2xl shadow-2xl p-8 sm:p-10">
      <div class="text-center mb-8">
        <div class="text-6xl mb-4">🏢</div>
        <h1 class="text-4xl font-bold text-gray-900 mb-3">Worker Portal</h1>
        <p class="text-lg text-gray-600">Login to view your work schedule</p>
      </div>

      <form @submit.prevent="handleLogin" class="space-y-6">
        <!-- Phone Number -->
        <div>
          <label for="phone" class="block text-lg font-semibold text-gray-800 mb-3">
            📱 Phone (numbers only)
          </label>
          <input
            id="phone"
            v-model="phone"
            type="tel"
            inputmode="numeric"
            pattern="[0-9]*"
            placeholder="Example: 4155551234"
            required
            autocomplete="tel"
            class="w-full px-5 py-4 text-lg border-2 border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition"
          />
          <p class="text-sm text-gray-500 mt-2">
            Type the same phone number you gave your supervisor
          </p>
        </div>

        <!-- PIN -->
        <div>
          <label for="pin" class="block text-lg font-semibold text-gray-800 mb-3">
            🔒 PIN (4 digits)
          </label>
          <input
            id="pin"
            v-model="pin"
            type="password"
            inputmode="numeric"
            pattern="[0-9]*"
            maxlength="4"
            placeholder="••••"
            required
            autocomplete="off"
            class="w-full px-5 py-4 text-2xl tracking-widest text-center border-2 border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition"
          />
          <div class="mt-3">
            <button
              type="button"
              @click="useLast4()"
              class="w-full bg-gray-100 hover:bg-gray-200 text-gray-900 font-semibold py-3 px-4 rounded-xl border border-gray-200"
            >
              Use last 4 digits of my phone
            </button>
            <p class="text-sm text-gray-500 mt-2">
              If you don’t know your PIN, ask your supervisor.
            </p>
          </div>
        </div>

        <!-- Error Message -->
        <div v-if="error" class="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
          <p class="text-sm">{{ error }}</p>
        </div>

        <!-- Submit Button -->
        <button
          type="submit"
          :disabled="loading"
          class="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold text-xl py-5 px-6 rounded-xl shadow-lg hover:shadow-xl transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed transform hover:scale-105 active:scale-95"
        >
          <span v-if="loading" class="flex items-center justify-center">
            <svg class="animate-spin h-6 w-6 mr-3" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" fill="none"></circle>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            Logging in...
          </span>
          <span v-else>✨ Login to My Schedule</span>
        </button>
      </form>

      <div class="mt-8 text-center space-y-3">
        <div class="bg-blue-50 rounded-xl p-4 border border-blue-200">
          <p class="text-sm font-semibold text-blue-900 mb-2">🆘 Need Help?</p>
          <p class="text-sm text-blue-800">
            <strong>Forgot your PIN?</strong><br>
            Contact your supervisor to reset it
          </p>
        </div>
        <p class="text-xs text-gray-500">
          This portal is for PitStop workers only
        </p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { getApiUrl } from '../../config/api'

const emit = defineEmits(['login-success'])

const phone = ref('')
const pin = ref('')
const loading = ref(false)
const error = ref('')

function digitsOnly(value: string) {
  return (value || '').replace(/\D/g, '')
}

function useLast4() {
  const d = digitsOnly(phone.value)
  if (d.length >= 4) pin.value = d.slice(-4)
}

async function handleLogin() {
  loading.value = true
  error.value = ''

  try {
    // Normalize inputs so staff can paste formatted phone numbers
    const normalizedPhone = digitsOnly(phone.value)
    const normalizedPin = digitsOnly(pin.value).slice(0, 4)

    const response = await fetch(getApiUrl('/api/worker/login/'), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        phone: normalizedPhone,
        pin: normalizedPin
      })
    })

    const contentType = response.headers.get('content-type') || ''
    let data: any = null
    if (contentType.includes('application/json')) {
      data = await response.json()
    } else {
      // Backend returned HTML (usually a 500 or maintenance). Keep message simple.
      const text = await response.text()
      console.error('Login error (non-JSON response):', response.status, text.slice(0, 200))
      error.value = 'System is updating. Please try again in 1 minute.'
      return
    }

    if (response.ok) {
      emit('login-success', data)
    } else {
      // Handle error responses
      if (data.phone) {
        error.value = data.phone[0]
      } else if (data.pin) {
        error.value = data.pin[0]
      } else if (data.non_field_errors) {
        error.value = data.non_field_errors[0]
      } else {
        error.value = 'Login failed. Please check your credentials.'
      }
    }
  } catch (err) {
    console.error('Login error:', err)
    error.value = 'Could not connect. Try again.'
  } finally {
    loading.value = false
  }
}
</script>
