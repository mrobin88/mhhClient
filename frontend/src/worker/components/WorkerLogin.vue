<template>
  <div class="min-h-screen flex items-center justify-center bg-gradient-to-b from-slate-100 via-slate-50 to-white px-4 py-10">
    <div class="max-w-md w-full">
      <div class="text-center mb-8">
        <div
          class="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-teal-600 text-white mb-4 shadow-md"
        >
          <BriefcaseIcon class="w-9 h-9" aria-hidden="true" />
        </div>
        <h1 class="text-3xl font-semibold text-slate-900 tracking-tight">PitStop Worker Portal</h1>
        <p class="text-sm text-slate-700 mt-2 max-w-sm mx-auto leading-relaxed">
          Sign in with your phone and PIN to view open shifts, respond faster, and keep your work record current.
        </p>
      </div>

      <div class="worker-card p-6 sm:p-8">
        <div class="mb-5 rounded-xl border border-teal-100 bg-teal-50 px-4 py-3 text-sm text-teal-900">
          <p class="font-semibold mb-1">Why this helps you</p>
          <p>Get open shifts quickly and keep your requests visible to supervisors.</p>
        </div>
        <form @submit.prevent="handleLogin" class="space-y-5">
          <div>
            <label for="phone" class="block text-sm font-semibold text-slate-800 mb-2">Mobile number</label>
            <div
              class="relative rounded-xl border border-slate-300 bg-white focus-within:ring-2 focus-within:ring-teal-500 focus-within:border-teal-500 transition"
            >
              <DevicePhoneMobileIcon
                class="w-5 h-5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2"
                aria-hidden="true"
              />
              <input
                id="phone"
                v-model="phone"
                type="tel"
                inputmode="numeric"
                pattern="[0-9]*"
                placeholder="4155551234"
                required
                autocomplete="tel"
                class="w-full pl-11 pr-4 py-3 text-lg text-slate-900 bg-transparent rounded-xl outline-none"
              />
            </div>
          </div>

          <div>
            <label for="pin" class="block text-sm font-semibold text-slate-800 mb-2">PIN (4 digits)</label>
            <div
              class="relative rounded-xl border border-slate-300 bg-white focus-within:ring-2 focus-within:ring-teal-500 focus-within:border-teal-500 transition"
            >
              <LockClosedIcon
                class="w-5 h-5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2"
                aria-hidden="true"
              />
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
                class="w-full pl-11 pr-4 py-3 text-xl tracking-[0.14em] text-slate-900 bg-transparent rounded-xl outline-none"
              />
            </div>
            <button
              type="button"
              @click="useLast4()"
              class="worker-btn worker-btn-secondary mt-2 min-h-[44px] text-sm"
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
            class="worker-btn worker-btn-primary"
          >
            <span v-if="loading">Signing in…</span>
            <span v-else>Sign in</span>
          </button>
        </form>

        <p class="text-xs text-slate-600 text-center mt-6">
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
