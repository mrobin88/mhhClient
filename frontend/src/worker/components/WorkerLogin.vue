<template>
  <div class="worker-login-shell">
    <div class="max-w-xs w-full">
      <div class="text-center mb-3">
        <div class="worker-login-brand">
          <BriefcaseIcon aria-hidden="true" />
        </div>
        <h1 class="text-lg font-semibold text-slate-900 tracking-tight">PitStop Worker</h1>
        <p class="text-[11px] text-slate-600 mt-0.5">Sign in with your phone and PIN.</p>
      </div>

      <div class="worker-card p-3">
        <form @submit.prevent="handleLogin" class="space-y-2.5">
          <div>
            <label for="phone" class="block text-[11px] font-semibold text-slate-800 mb-1">Mobile number</label>
            <div class="worker-input-wrap">
              <DevicePhoneMobileIcon class="worker-input-icon" aria-hidden="true" />
              <input
                id="phone"
                v-model="phone"
                type="tel"
                inputmode="numeric"
                pattern="[0-9]*"
                placeholder="4155551234"
                required
                autocomplete="tel"
                class="worker-login-input"
              />
            </div>
          </div>

          <div>
            <label for="pin" class="block text-[11px] font-semibold text-slate-800 mb-1">PIN (4 digits)</label>
            <div class="worker-input-wrap">
              <LockClosedIcon class="worker-input-icon" aria-hidden="true" />
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
                class="worker-login-input tracking-[0.14em]"
              />
            </div>
            <button
              type="button"
              @click="useLast4()"
              class="worker-btn worker-btn-secondary mt-1.5 text-[11px]"
            >
              Use last 4 of my number
            </button>
          </div>

          <div v-if="error" class="text-[11px] text-red-700 bg-red-50 border border-red-100 rounded-lg px-2.5 py-1.5">
            {{ error }}
          </div>

          <button type="submit" :disabled="loading" class="worker-btn worker-btn-primary">
            <span v-if="loading" class="worker-spinner" aria-hidden="true"></span>
            <span v-if="loading">Signing in</span>
            <span v-else>Sign in</span>
          </button>
        </form>

        <p class="text-[10px] text-slate-500 text-center mt-2.5">
          PitStop workers only. Ask your supervisor for PIN reset.
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
