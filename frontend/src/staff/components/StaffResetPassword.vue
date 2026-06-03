<template>
  <div class="min-h-screen flex flex-col justify-center px-4 py-10 max-w-md mx-auto">
    <div class="text-center mb-6">
      <h1 class="text-xl font-bold">Choose a new password</h1>
      <p class="text-stone-600 mt-2 text-sm">Use at least 8 characters.</p>
    </div>

    <form v-if="!done" class="staff-card p-6 space-y-4" @submit.prevent="submit">
      <div>
        <label class="block text-sm font-semibold mb-2">New password</label>
        <input
          v-model="password"
          :type="showPw ? 'text' : 'password'"
          class="staff-input"
          minlength="8"
          required
        />
      </div>
      <div>
        <label class="block text-sm font-semibold mb-2">Confirm password</label>
        <input
          v-model="confirm"
          :type="showPw ? 'text' : 'password'"
          class="staff-input"
          required
        />
      </div>
      <button type="button" class="text-sm font-semibold text-orange-600" @click="showPw = !showPw">
        {{ showPw ? 'Hide passwords' : 'Show passwords' }}
      </button>
      <p v-if="error" class="text-sm text-red-700">{{ error }}</p>
      <button type="submit" class="staff-btn staff-btn-primary w-full" :disabled="busy || !validToken">
        {{ busy ? 'Saving…' : 'Update password' }}
      </button>
    </form>

    <div v-else class="staff-card p-6 text-center space-y-3">
      <p class="font-semibold text-green-800">Password updated</p>
      <RouterLink to="/login" class="staff-btn staff-btn-primary w-full inline-flex">Sign in</RouterLink>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute } from 'vue-router'
import { staffFetch } from '../api'
import { friendlyError, networkErrorMessage } from '../utils/errors'

const route = useRoute()
const password = ref('')
const confirm = ref('')
const showPw = ref(false)
const busy = ref(false)
const error = ref('')
const done = ref(false)

const validToken = computed(() => Boolean(route.params.uid && route.params.token))

async function submit() {
  error.value = ''
  if (password.value.length < 8) {
    error.value = 'Password must be at least 8 characters.'
    return
  }
  if (password.value !== confirm.value) {
    error.value = 'Passwords do not match.'
    return
  }
  busy.value = true
  try {
    const resp = await staffFetch('/api/staff/password-reset/confirm/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        uid: route.params.uid,
        token: route.params.token,
        new_password: password.value,
      }),
    })
    const body = await resp.json().catch(() => null)
    if (!resp.ok) {
      error.value = friendlyError(body, 'This reset link is invalid or expired. Request a new one.')
      return
    }
    done.value = true
  } catch (e) {
    error.value = networkErrorMessage(e)
  } finally {
    busy.value = false
  }
}
</script>
