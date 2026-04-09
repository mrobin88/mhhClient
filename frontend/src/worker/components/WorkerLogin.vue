<template>
  <div class="min-h-screen flex items-center justify-center bg-slate-100 px-4 py-10">
    <div class="max-w-md w-full">
      <div class="text-center mb-8">
        <div
          class="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-teal-600 text-white mb-4 shadow-sm"
        >
          <BriefcaseIcon class="w-8 h-8" aria-hidden="true" />
        </div>
        <h1 class="text-2xl font-semibold text-slate-900 tracking-tight">Open shifts</h1>
        <p class="text-sm text-slate-500 mt-2 max-w-sm mx-auto leading-relaxed">
          Sign in with the phone number on file to see shifts that need coverage and say if you can help.
        </p>
      </div>

      <div class="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 sm:p-8">
        <form @submit.prevent="handleLogin" class="space-y-5">
          <div>
            <label for="phone" class="flex items-center gap-2 text-sm font-medium text-slate-700 mb-2">
              <DevicePhoneMobileIcon class="w-5 h-5 text-teal-600" aria-hidden="true" />
              Mobile number (digits only)
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
              class="w-full px-4 py-3.5 text-lg text-slate-900 border border-slate-200 rounded-xl focus:ring-2 focus:ring-teal-500 focus:border-teal-500 outline-none transition"
            />
          </div>

          <div>
            <label for="pin" class="flex items-center gap-2 text-sm font-medium text-slate-700 mb-2">
              <LockClosedIcon class="w-5 h-5 text-teal-600" aria-hidden="true" />
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
              class="w-full px-4 py-3.5 text-2xl tracking-[0.2em] text-center text-slate-900 border border-slate-200 rounded-xl focus:ring-2 focus:ring-teal-500 focus:border-teal-500 outline-none transition"
            />
            <button
              type="button"
              @click="useLast4()"
              class="mt-2 w-full py-2.5 text-sm font-medium text-teal-700 bg-teal-50 hover:bg-teal-100 rounded-xl border border-teal-100 transition"
            >
              Use last 4 digits of my number as PIN
            </button>
          </div>

          <div v-if="error" class="text-sm text-red-700 bg-red-50 border border-red-100 rounded-xl px-4 py-3">
            {{ error }}
          </div>

          <button
            type="submit"
            :disabled="loading"
            class="w-full min-h-[52px] rounded-xl bg-teal-600 hover:bg-teal-700 disabled:bg-slate-300 text-white text-base font-semibold shadow-sm transition-colors"
          >
            <span v-if="loading">Signing in…</span>
            <span v-else>Sign in</span>
          </button>
        </form>

        <p class="text-xs text-slate-400 text-center mt-6">
          PitStop workers only. Ask your supervisor if you need a PIN reset.
        </p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import {
  BriefcaseIcon,
  DevicePhoneMobileIcon,
  LockClosedIcon,
} from '@heroicons/vue/24/outline'
import { getApiUrl } from '../../config/api'

const emit = defineEmits<{
  'login-success': [data: { token: string; worker_account: Record<string, unknown> }]
}>()

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
    const normalizedPhone = digitsOnly(phone.value)
    const normalizedPin = digitsOnly(pin.value).slice(0, 6)

    const response = await fetch(getApiUrl('/api/worker/login/'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        phone: normalizedPhone,
        pin: normalizedPin,
      }),
    })

    const contentType = response.headers.get('content-type') || ''
    let data: Record<string, unknown> | null = null
    if (contentType.includes('application/json')) {
      data = await response.json()
    } else {
      error.value = 'System is updating. Please try again in a minute.'
      return
    }

    if (response.ok && data) {
      emit('login-success', data as { token: string; worker_account: Record<string, unknown> })
    } else if (data) {
      const p = data.phone as string[] | undefined
      const pi = data.pin as string[] | undefined
      const nf = data.non_field_errors as string[] | undefined
      error.value = p?.[0] || pi?.[0] || nf?.[0] || 'Sign-in failed. Check your number and PIN.'
    }
  } catch {
    error.value = 'Could not connect. Try again.'
  } finally {
    loading.value = false
  }
}
</script>
