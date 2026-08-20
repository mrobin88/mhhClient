<template>
  <div class="min-h-screen flex flex-col justify-center px-4 py-10 max-w-md mx-auto">
    <div class="text-center mb-8">
      <p class="text-5xl mb-3" aria-hidden="true">⛑️</p>
      <h1 class="text-2xl font-bold text-stone-900">Staff sign in</h1>
      <p class="text-stone-600 mt-2 text-base">Find clients and add notes — simpler than Admin.</p>
    </div>

    <p
      v-if="sessionExpired"
      class="text-sm text-amber-800 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2 mb-4"
    >
      Your sign-in ran out, so that last action did not save. Sign in again and we will put you
      back where you were.
    </p>

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
        <div class="staff-password-field">
          <input
            v-model="password"
            :type="showPassword ? 'text' : 'password'"
            autocomplete="current-password"
            class="staff-input"
            :class="{ 'staff-input-error': fieldErrors.password }"
            required
          />
          <button
            type="button"
            class="staff-password-toggle"
            :aria-label="showPassword ? 'Hide password' : 'Show password'"
            :aria-pressed="showPassword"
            @click="showPassword = !showPassword"
          >
            <span class="material-symbols-outlined" aria-hidden="true">
              {{ showPassword ? 'visibility_off' : 'visibility' }}
            </span>
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

      <div class="text-center space-y-2">
        <RouterLink to="/forgot-password" class="text-sm font-semibold staff-link hover:underline">
          Forgot password?
        </RouterLink>
        <p class="text-xs text-stone-500">
          Need help?
          <a
            href="mailto:mrobin@missionhiringhall.org"
            class="font-semibold text-stone-700 hover:underline"
          >mrobin@missionhiringhall.org</a>
        </p>
      </div>
    </form>

    <BulldozerLoader v-if="busy" label="Signing you in…" class="staff-card p-8" />
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { setCsrfToken, staffFetch } from '../api'
import { friendlyError, networkErrorMessage } from '../utils/errors'
import BulldozerLoader from './BulldozerLoader.vue'

import type { StaffUser } from '../types'

const emit = defineEmits<{ (e: 'logged-in', user: StaffUser): void }>()
const router = useRouter()

const username = ref('')
const password = ref('')
const showPassword = ref(false)
const busy = ref(false)
const error = ref('')
const fieldErrors = reactive({ username: '', password: '' })
const sessionExpired = computed(() => router.currentRoute.value.query.expired === '1')

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
    if (!body?.user) {
      error.value = 'Signed in but session did not start. Try again.'
      return
    }
    if (body.csrfToken) setCsrfToken(body.csrfToken)
    emit('logged-in', body.user)
    const redirect = typeof router.currentRoute.value.query.redirect === 'string'
      ? router.currentRoute.value.query.redirect
      : '/dashboard'
    // Only honor in-app paths; never bounce back to login/auth screens.
    const safe =
      redirect.startsWith('/') &&
      !redirect.startsWith('//') &&
      !['/login', '/forgot-password'].some((p) => redirect === p || redirect.startsWith(`${p}/`))
    router.replace(safe ? redirect : '/dashboard')
  } catch (e) {
    error.value = networkErrorMessage(e)
  } finally {
    busy.value = false
  }
}
</script>
