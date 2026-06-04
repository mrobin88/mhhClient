<template>
  <div class="min-h-screen flex flex-col justify-center px-4 py-10 max-w-md mx-auto">
    <div class="text-center mb-6">
      <p class="text-4xl mb-2" aria-hidden="true">🔑</p>
      <h1 class="text-xl font-bold">Reset your password</h1>
      <p class="text-stone-600 mt-2 text-sm">
        Enter the email on your staff account. We will email reset steps if it matches.
      </p>
    </div>

    <form v-if="!sent" class="staff-card p-6 space-y-4" @submit.prevent="submit">
      <div>
        <label class="block text-sm font-semibold text-stone-700 mb-2">Work email</label>
        <input
          v-model="email"
          type="email"
          autocomplete="email"
          class="staff-input"
          :class="{ 'staff-input-error': fieldError }"
          required
        />
        <p v-if="fieldError" class="text-sm text-red-700 mt-1">{{ fieldError }}</p>
      </div>
      <p v-if="error" class="text-sm text-red-700">{{ error }}</p>
      <button type="submit" class="staff-btn staff-btn-primary w-full" :disabled="busy">
        {{ busy ? 'Sending…' : 'Send reset link' }}
      </button>
      <RouterLink to="/login" class="block text-center text-sm font-semibold text-orange-600">
        Back to sign in
      </RouterLink>
    </form>

    <div v-else class="staff-card p-6 space-y-3 text-center">
      <p class="text-green-800 font-semibold">Check your inbox</p>
      <p class="text-sm text-stone-600">
        If that email is registered, you will receive a link shortly. Check spam if needed.
      </p>
      <RouterLink to="/login" class="staff-btn staff-btn-primary w-full inline-flex mt-2">
        Return to sign in
      </RouterLink>
    </div>

    <BulldozerLoader v-if="busy" label="Sending email…" />
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { staffFetch } from '../api'
import { friendlyError, networkErrorMessage } from '../utils/errors'
import BulldozerLoader from './BulldozerLoader.vue'

const email = ref('')
const busy = ref(false)
const error = ref('')
const fieldError = ref('')
const sent = ref(false)

async function submit() {
  fieldError.value = ''
  error.value = ''
  if (!email.value.trim()) {
    fieldError.value = 'Enter your work email.'
    return
  }
  busy.value = true
  try {
    const resp = await staffFetch('/api/staff/password-reset/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: email.value.trim() }),
    })
    const body = await resp.json().catch(() => null)
    if (!resp.ok) {
      error.value = friendlyError(body)
      return
    }
    sent.value = true
  } catch (e) {
    error.value = networkErrorMessage(e)
  } finally {
    busy.value = false
  }
}
</script>
