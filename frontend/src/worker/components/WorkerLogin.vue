<template>
  <div class="min-h-screen flex items-center justify-center">
    <div class="max-w-md w-full bg-white rounded-lg shadow-xl p-8">
      <div class="text-center mb-8">
        <h1 class="text-3xl font-bold text-gray-900 mb-2">🏢 Worker Portal</h1>
        <p class="text-gray-600">Login to access your assignments</p>
      </div>

      <form @submit.prevent="handleLogin" class="space-y-6">
        <!-- Phone Number -->
        <div>
          <label for="phone" class="block text-sm font-medium text-gray-700 mb-2">
            Phone Number
          </label>
          <input
            id="phone"
            v-model="phone"
            type="tel"
            placeholder="415-555-1234"
            required
            class="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>

        <!-- PIN -->
        <div>
          <label for="pin" class="block text-sm font-medium text-gray-700 mb-2">
            PIN
          </label>
          <input
            id="pin"
            v-model="pin"
            type="password"
            inputmode="numeric"
            maxlength="6"
            placeholder="Enter your PIN"
            required
            class="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
          <p class="text-xs text-gray-500 mt-1">
            Enter your 4-6 digit PIN
          </p>
        </div>

        <!-- Error Message -->
        <div v-if="error" class="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
          <p class="text-sm">{{ error }}</p>
        </div>

        <!-- Submit Button -->
        <button
          type="submit"
          :disabled="loading"
          class="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 px-4 rounded-lg transition duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <span v-if="loading">Logging in...</span>
          <span v-else>Login</span>
        </button>
      </form>

      <div class="mt-6 text-center">
        <p class="text-sm text-gray-600">
          Need help? Contact your supervisor
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

async function handleLogin() {
  loading.value = true
  error.value = ''

  try {
    const response = await fetch(getApiUrl('/api/worker/login/'), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        phone: phone.value,
        pin: pin.value
      })
    })

    const data = await response.json()

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
    error.value = 'Network error. Please check your connection and try again.'
  } finally {
    loading.value = false
  }
}
</script>
