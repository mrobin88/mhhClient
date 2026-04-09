<template>
  <div class="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-900 via-blue-900 to-indigo-900 px-4 py-10">
    <div class="max-w-md w-full bg-white rounded-2xl shadow-2xl overflow-hidden">
      <div class="bg-gradient-to-r from-blue-600 to-indigo-600 px-8 py-6 text-white text-center">
        <div class="text-4xl mb-2">🏢</div>
        <p class="text-xs font-semibold uppercase tracking-widest text-blue-100">Mission Hiring Hall</p>
        <h1 class="text-2xl sm:text-3xl font-bold mt-1">PitStop worker portal</h1>
        <p class="text-sm text-blue-100 mt-2 leading-relaxed">
          Sign in to see shifts, confirm work, and send site requests.
        </p>
      </div>

      <div class="p-8 sm:p-10">
      <form @submit.prevent="handleLogin" class="space-y-6">
        <!-- Phone Number -->
        <div>
          <label for="phone" class="block text-sm font-bold text-gray-800 mb-2">
            Mobile number
          </label>
          <input
            id="phone"
            v-model="phone"
            type="tel"
            inputmode="numeric"
            pattern="[0-9]*"
            placeholder="4155551234"
            required
            autocomplete="tel"
            class="w-full px-5 py-4 text-lg border-2 border-gray-200 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition"
          />
          <p class="text-sm text-gray-500 mt-2">
            Enter digits only — dashes or parentheses are optional; we match the number on file.
          </p>
        </div>

        <!-- PIN -->
        <div>
          <label for="pin" class="block text-sm font-bold text-gray-800 mb-2">
            PIN (4 digits)
          </label>
          <input
            id="pin"
            v-model="pin"
            type="password"
            inputmode="numeric"
            pattern="[0-9]*"
            maxlength="6"
            placeholder="••••"
            required
            autocomplete="off"
            class="w-full px-5 py-4 text-2xl tracking-widest text-center border-2 border-gray-200 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition"
          />
          <div class="mt-3">
            <button
              type="button"
              @click="useLast4()"
              class="w-full bg-blue-50 hover:bg-blue-100 text-blue-900 font-semibold py-3 px-4 rounded-xl border border-blue-200"
            >
              Fill PIN = last 4 digits of my number
            </button>
            <p class="text-sm text-gray-500 mt-2">
              Default PIN is usually the <strong>last four digits</strong> of your mobile number. Ask your supervisor if it was reset.
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
          class="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold text-lg py-4 px-6 rounded-xl shadow-md hover:shadow-lg transition disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <span v-if="loading" class="flex items-center justify-center">
            <svg class="animate-spin h-6 w-6 mr-3" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" fill="none"></circle>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            Signing in…
          </span>
          <span v-else>Sign in</span>
        </button>
      </form>

      <div class="mt-8 text-center space-y-3">
        <div class="bg-slate-50 rounded-xl p-4 border border-slate-200">
          <p class="text-sm font-semibold text-slate-800 mb-1">Need help?</p>
          <p class="text-sm text-slate-600">
            Forgot your PIN or can’t sign in — ask your PitStop supervisor or admin to reset your portal access.
          </p>
        </div>
        <p class="text-xs text-gray-400">
          PitStop team members only
        </p>
      </div>
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
    const normalizedPin = digitsOnly(pin.value).slice(0, 6)

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
