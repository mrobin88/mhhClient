<template>
  <section class="worker-card p-3 space-y-3">
    <div>
      <h2 class="worker-card-title">Incident report</h2>
      <p class="text-xs text-slate-300">Share the supervisor name and what happened.</p>
    </div>

    <label class="block space-y-1">
      <span class="worker-label">Supervisor name</span>
      <input
        v-model.trim="supervisorName"
        type="text"
        class="worker-field"
        maxlength="100"
        autocomplete="name"
      />
    </label>

    <label class="block space-y-1">
      <span class="worker-label">What happened</span>
      <textarea
        v-model.trim="details"
        rows="5"
        class="worker-field worker-textarea"
        maxlength="2000"
      />
    </label>

    <button
      type="button"
      class="worker-btn worker-btn-card worker-btn-primary"
      :disabled="busy"
      @click="submitIncident"
    >
      <span v-if="busy">Submitting…</span>
      <span v-else>Submit report</span>
    </button>

    <p v-if="message" class="worker-status-note worker-status-note--ok">{{ message }}</p>
    <p v-if="error" class="worker-status-note worker-status-note--error">{{ error }}</p>
  </section>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { workerFetch } from '../api'

const supervisorName = ref('')
const details = ref('')
const busy = ref(false)
const message = ref('')
const error = ref('')

async function submitIncident() {
  if (busy.value) return
  error.value = ''
  message.value = ''

  if (!supervisorName.value) {
    error.value = 'Enter the supervisor name.'
    return
  }
  if (!details.value) {
    error.value = 'Describe what happened.'
    return
  }

  busy.value = true
  try {
    const resp = await workerFetch('/api/worker/incident-report/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        supervisor_name: supervisorName.value,
        details: details.value,
      }),
    })
    const body = await resp.json().catch(() => null)
    if (!resp.ok || !body) {
      error.value =
        body?.supervisor_name?.[0] ||
        body?.details?.[0] ||
        body?.error ||
        'Could not submit incident report.'
      return
    }
    message.value = body.message || 'Incident report submitted.'
    details.value = ''
  } catch {
    error.value = 'No connection. Try again.'
  } finally {
    busy.value = false
  }
}
</script>
