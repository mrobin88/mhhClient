<template>
  <div class="space-y-4">
    <section class="worker-card p-4 space-y-3">
      <h2 class="text-lg font-semibold text-slate-900">Profile</h2>
      <div class="text-sm text-slate-700 space-y-2">
        <p><strong>Name:</strong> {{ profile?.client_name || 'Worker' }}</p>
        <p><strong>Phone:</strong> {{ profile?.phone || profile?.client_phone || '-' }}</p>
        <p><strong>Status:</strong> {{ profile?.worker_status_label || '-' }}</p>
      </div>
      <p class="text-xs text-slate-500">Ask staff to update your name or phone number.</p>
    </section>

    <section class="worker-card p-4 space-y-3">
      <div class="flex items-start justify-between gap-3">
        <div>
          <h2 class="text-lg font-semibold text-slate-900">Availability</h2>
          <p class="text-sm text-slate-700">Tell staff if you can take work right now.</p>
        </div>
        <span
          class="shrink-0 text-xs font-semibold px-2.5 py-1 rounded-full"
          :class="isAvailable ? 'bg-emerald-100 text-emerald-700' : 'bg-slate-100 text-slate-700'"
        >
          {{ isAvailable ? 'Available' : 'Not available' }}
        </span>
      </div>

      <button
        type="button"
        class="worker-btn"
        :class="isAvailable ? 'worker-btn-secondary' : 'worker-btn-primary'"
        :disabled="busy"
        @click="toggleAvailability"
      >
        <span v-if="busy">Saving...</span>
        <span v-else>{{ isAvailable ? 'Set not available' : 'Set available' }}</span>
      </button>

      <p v-if="message" class="worker-status-note bg-slate-50 text-slate-800 border border-slate-200">{{ message }}</p>
      <p v-if="error" class="worker-status-note bg-red-50 text-red-800 border border-red-200">{{ error }}</p>
    </section>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { workerFetch } from '../api'

interface WorkerProfile {
  client_name?: string
  client_phone?: string
  phone?: string
  worker_status_label?: string
  is_available?: boolean
}

const profile = ref<WorkerProfile | null>(null)
const isAvailable = ref(false)
const busy = ref(false)
const error = ref('')
const message = ref('')

async function loadProfile() {
  error.value = ''
  try {
    const resp = await workerFetch('/api/worker/profile/')
    const body = await resp.json().catch(() => null)
    if (!resp.ok || !body) {
      error.value = body?.error || 'Could not load profile.'
      return
    }
    profile.value = body
    isAvailable.value = Boolean(body.is_available)
  } catch {
    error.value = 'No connection. Try again.'
  }
}

async function toggleAvailability() {
  busy.value = true
  error.value = ''
  message.value = ''
  try {
    const nextValue = !isAvailable.value
    const resp = await workerFetch('/api/worker/availability/', {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ is_available: nextValue }),
    })
    const body = await resp.json().catch(() => null)
    if (!resp.ok || !body) {
      error.value = body?.error || 'Could not update availability.'
      return
    }
    isAvailable.value = Boolean(body.is_available)
    if (profile.value) profile.value.is_available = isAvailable.value
    message.value = 'Availability updated.'
  } catch {
    error.value = 'No connection. Try again.'
  } finally {
    busy.value = false
  }
}

onMounted(() => {
  loadProfile()
})
</script>
