<template>
  <div class="space-y-2">
    <section class="worker-card p-3 space-y-1.5">
      <h2 class="worker-card-title">Profile</h2>
      <div class="text-xs text-slate-200 space-y-0.5">
        <p><strong>Name:</strong> {{ profile?.client_name || 'Worker' }}</p>
        <p><strong>Phone:</strong> {{ profile?.phone || profile?.client_phone || '-' }}</p>
        <p><strong>Status:</strong> {{ profile?.worker_status_label || '-' }}</p>
      </div>
      <p class="text-[10px] text-slate-400">Ask staff to update your name or phone.</p>
    </section>

    <section class="worker-card p-3 space-y-2">
      <div class="flex items-start justify-between gap-2">
        <div>
          <h2 class="worker-card-title">Availability</h2>
          <p class="text-[11px] text-slate-300">Can you take work right now?</p>
        </div>
        <span
          class="worker-pill shrink-0"
          :class="isAvailable ? 'worker-pill-green' : 'worker-pill-slate'"
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
        <span v-if="busy" class="worker-spinner" aria-hidden="true"></span>
        <span v-if="busy">Saving</span>
        <span v-else>{{ isAvailable ? 'Set not available' : 'Set available' }}</span>
      </button>

      <p v-if="message" class="worker-status-note worker-status-note--ok">{{ message }}</p>
      <p v-if="error" class="worker-status-note worker-status-note--error">{{ error }}</p>
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
