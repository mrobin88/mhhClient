<template>
  <section class="worker-card p-3 space-y-3">
    <div>
      <h2 class="worker-card-title">Incident report</h2>
      <p class="text-xs text-slate-300">Use this to replace the paper incident form. Your worker account is recorded as the reporting person.</p>
    </div>

    <label class="block space-y-1">
      <span class="worker-label">When it happened</span>
      <input
        v-model="occurredAt"
        type="datetime-local"
        class="worker-field"
      />
    </label>

    <label class="block space-y-1">
      <span class="worker-label">Who was involved</span>
      <textarea
        v-model.trim="involvedPeople"
        rows="3"
        class="worker-field worker-textarea"
        maxlength="1000"
        placeholder="Names, roles, or descriptions if names are unknown"
      />
    </label>

    <label class="block space-y-1">
      <span class="worker-label">Brief description</span>
      <textarea
        v-model.trim="briefDescription"
        rows="3"
        class="worker-field worker-textarea"
        maxlength="1000"
        placeholder="Short summary of what happened"
      />
    </label>

    <label class="block space-y-1">
      <span class="worker-label">What happened</span>
      <textarea
        v-model.trim="whatHappened"
        rows="5"
        class="worker-field worker-textarea"
        maxlength="2000"
        placeholder="Write the incident details"
      />
    </label>

    <label class="block space-y-1">
      <span class="worker-label">Where it happened</span>
      <input
        v-model.trim="whereHappened"
        type="text"
        class="worker-field"
        maxlength="300"
        placeholder="Pit Stop site, restroom, block, or nearby landmark"
      />
    </label>

    <label class="block space-y-1">
      <span class="worker-label">Why it happened</span>
      <textarea
        v-model.trim="whyHappened"
        rows="3"
        class="worker-field worker-textarea"
        maxlength="1000"
        placeholder="If unknown, write unknown"
      />
    </label>

    <label class="block space-y-1">
      <span class="worker-label">Actions taken</span>
      <textarea
        v-model.trim="actionsTaken"
        rows="4"
        class="worker-field worker-textarea"
        maxlength="1500"
        placeholder="Who was notified, cleanup done, 911 called, report made, etc."
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

function currentLocalDateTime() {
  const now = new Date()
  now.setMinutes(now.getMinutes() - now.getTimezoneOffset())
  return now.toISOString().slice(0, 16)
}

const occurredAt = ref(currentLocalDateTime())
const involvedPeople = ref('')
const briefDescription = ref('')
const whatHappened = ref('')
const whereHappened = ref('')
const whyHappened = ref('')
const actionsTaken = ref('')
const busy = ref(false)
const message = ref('')
const error = ref('')

async function submitIncident() {
  if (busy.value) return
  error.value = ''
  message.value = ''

  if (!occurredAt.value) {
    error.value = 'Enter when it happened.'
    return
  }
  if (!involvedPeople.value) {
    error.value = 'Enter who was involved.'
    return
  }
  if (!briefDescription.value) {
    error.value = 'Enter a brief description.'
    return
  }
  if (!whatHappened.value) {
    error.value = 'Describe what happened.'
    return
  }
  if (!whereHappened.value) {
    error.value = 'Enter where it happened.'
    return
  }
  if (!whyHappened.value) {
    error.value = 'Enter why it happened, or write unknown.'
    return
  }
  if (!actionsTaken.value) {
    error.value = 'Enter actions taken, or write none.'
    return
  }

  busy.value = true
  try {
    const resp = await workerFetch('/api/worker/incident-report/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        occurred_at: occurredAt.value,
        involved_people: involvedPeople.value,
        brief_description: briefDescription.value,
        what_happened: whatHappened.value,
        where_happened: whereHappened.value,
        why_happened: whyHappened.value,
        actions_taken: actionsTaken.value,
      }),
    })
    const body = await resp.json().catch(() => null)
    if (!resp.ok || !body) {
      error.value =
        body?.occurred_at?.[0] ||
        body?.involved_people?.[0] ||
        body?.brief_description?.[0] ||
        body?.what_happened?.[0] ||
        body?.where_happened?.[0] ||
        body?.why_happened?.[0] ||
        body?.actions_taken?.[0] ||
        body?.error ||
        'Could not submit incident report.'
      return
    }
    message.value = body.message || 'Incident report submitted.'
    occurredAt.value = currentLocalDateTime()
    involvedPeople.value = ''
    briefDescription.value = ''
    whatHappened.value = ''
    whereHappened.value = ''
    whyHappened.value = ''
    actionsTaken.value = ''
  } catch {
    error.value = 'No connection. Try again.'
  } finally {
    busy.value = false
  }
}
</script>
