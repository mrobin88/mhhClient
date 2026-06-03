<template>
  <div class="min-h-screen flex flex-col justify-center px-4 py-10 max-w-md mx-auto">
    <div class="text-center mb-8">
      <p class="text-5xl mb-3" aria-hidden="true">⛑️</p>
      <h1 class="text-2xl font-bold text-stone-900">Staff workspace</h1>
      <p class="text-stone-600 mt-2 text-base">Mission Hiring Hall — case management on the go</p>
    </div>

    <form v-show="!busy" class="staff-card p-6 sm:p-8 space-y-5" @submit.prevent="submit">
      <div>
        <label class="block text-sm font-semibold text-stone-700 mb-2">Username</label>
        <input
          v-model="username"
          type="text"
          autocomplete="username"
          class="staff-input"
          :class="{ 'staff-input-error': fieldErrors.username }"
          required
        />
        <p v-if="fieldErrors.username" class="text-sm text-red-700 mt-1">{{ fieldErrors.username }}</p>
      </div>

      <div>
        <label class="block text-sm font-semibold text-stone-700 mb-2">Password</label>
        <div class="relative">
          <input
            v-model="password"
            :type="showPassword ? 'text' : 'password'"
            autocomplete="current-password"
            class="staff-input pr-24"
            :class="{ 'staff-input-error': fieldErrors.password }"
            required
          />
          <button
            type="button"
            class="absolute right-3 top-1/2 -translate-y-1/2 text-sm font-semibold text-orange-600"
            @click="showPassword = !showPassword"
          >
            {{ showPassword ? 'Hide' : 'Show' }}
          </button>
        </div>
        <p v-if="fieldErrors.password" class="text-sm text-red-700 mt-1">{{ fieldErrors.password }}</p>
      </div>

      <p v-if="error" class="text-sm text-red-700 bg-red-50 border border-red-100 rounded-lg px-3 py-2">
        {{ error }}
      </p>

      <button type="submit" class="staff-btn staff-btn-primary w-full text-lg py-3.5" :disabled="busy">
        <span v-if="busy">Signing in…</span>
        <span v-else>Sign in</span>
      </button>

      <p class="text-center">
        <RouterLink to="/forgot-password" class="text-sm font-semibold text-orange-600 hover:underline">
          Forgot password?
        </RouterLink>
      </p>
    </form>

    <BulldozerLoader v-if="busy" label="Signing you in…" class="staff-card p-8" />
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { staffFetch } from '../api'
import { friendlyError, networkErrorMessage } from '../utils/errors'
import BulldozerLoader from './BulldozerLoader.vue'

const emit = defineEmits<{ (e: 'logged-in'): void }>()
const router = useRouter()

const username = ref('')
const password = ref('')
const showPassword = ref(false)
const busy = ref(false)
const error = ref('')
const fieldErrors = reactive({ username: '', password: '' })

async function submit() {
  fieldErrors.username = ''
  fieldErrors.password = ''
  error.value = ''

  if (!username.value.trim()) {
    fieldErrors.username = 'Enter your username.'
    return
  }
  if (!password.value) {
    fieldErrors.password = 'Enter your password.'
    return
  }

  busy.value = true
  try {
    const resp = await staffFetch('/api/staff/login/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        username: username.value.trim(),
        password: password.value,
      }),
    })
    const body = await resp.json().catch(() => null)
    if (!resp.ok) {
      error.value = friendlyError(body, 'Invalid username or password. Please try again.')
      return
    }
    emit('logged-in')
    const redirect = typeof router.currentRoute.value.query.redirect === 'string'
      ? router.currentRoute.value.query.redirect
      : '/clients'
    router.replace(redirect.startsWith('/') ? redirect : '/clients')
  } catch (e) {
    error.value = networkErrorMessage(e)
  } finally {
    busy.value = false
  }
}
</script>
