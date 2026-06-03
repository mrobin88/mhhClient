<template>
  <section class="bg-white rounded-xl shadow-sm border border-slate-200 p-5 space-y-4">
    <div>
      <h1 class="text-xl font-bold">Staff workspace</h1>
      <p class="text-sm text-slate-600 mt-1">Same login as Django Admin.</p>
    </div>

    <form class="space-y-3" @submit.prevent="submit">
      <div>
        <label class="block text-sm font-medium text-slate-700 mb-1">Username</label>
        <input
          v-model="username"
          type="text"
          autocomplete="username"
          class="w-full rounded-lg border border-slate-300 px-3 py-2 text-base"
          required
        />
      </div>
      <div>
        <label class="block text-sm font-medium text-slate-700 mb-1">Password</label>
        <input
          v-model="password"
          type="password"
          autocomplete="current-password"
          class="w-full rounded-lg border border-slate-300 px-3 py-2 text-base"
          required
        />
      </div>
      <p v-if="error" class="text-sm text-red-700">{{ error }}</p>
      <button
        type="submit"
        class="w-full rounded-lg bg-slate-900 text-white font-semibold py-2.5 disabled:opacity-60"
        :disabled="busy"
      >
        {{ busy ? 'Signing in…' : 'Sign in' }}
      </button>
    </form>
  </section>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { staffFetch } from '../api'

const emit = defineEmits<{ (e: 'logged-in'): void }>()

const username = ref('')
const password = ref('')
const busy = ref(false)
const error = ref('')

async function submit() {
  busy.value = true
  error.value = ''
  try {
    const resp = await staffFetch('/api/staff/login/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        username: username.value.trim(),
        password: password.value,
      }),
    })
    if (!resp.ok) {
      const body = await resp.json().catch(() => null)
      error.value = body?.error || 'Could not sign in.'
      return
    }
    emit('logged-in')
  } catch {
    error.value = 'No connection. Try again.'
  } finally {
    busy.value = false
  }
}
</script>
