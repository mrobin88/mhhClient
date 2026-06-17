<template>
  <section class="worker-card p-3 space-y-3">
    <div class="flex items-center justify-between gap-2">
      <div>
        <h2 class="worker-card-title">Daily feedback</h2>
        <p class="text-xs text-slate-300">Share how the shift went today.</p>
      </div>
      <span class="worker-pill worker-pill-green">Daily</span>
    </div>

    <label class="block space-y-1">
      <span class="worker-label">Today's feedback</span>
      <textarea
        v-model.trim="feedbackText"
        rows="5"
        class="worker-field worker-textarea"
        maxlength="2000"
        placeholder="What went well? Any blockers? What support do you need?"
      />
    </label>

    <button type="button" class="worker-btn worker-btn-primary" :disabled="busy" @click="saveFeedback">
      <span v-if="busy">Saving…</span>
      <span v-else>Save daily feedback</span>
    </button>

    <p v-if="message" class="worker-status-note worker-status-note--ok">{{ message }}</p>
    <p v-if="error" class="worker-status-note worker-status-note--error">{{ error }}</p>

    <div v-if="recentFeedback.length" class="space-y-1">
      <h3 class="worker-label">Recent entries</h3>
      <div
        v-for="item in recentFeedback"
        :key="item.id"
        class="worker-metric space-y-1"
      >
        <p class="worker-metric-label">{{ formatDate(item.feedback_date) }}</p>
        <p class="text-xs text-slate-200 leading-relaxed whitespace-pre-wrap">{{ item.feedback_text }}</p>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { workerFetch } from '../api'

interface DailyFeedbackEntry {
  id: number
  feedback_date: string
  feedback_text: string
}

const feedbackText = ref('')
const recentFeedback = ref<DailyFeedbackEntry[]>([])
const busy = ref(false)
const message = ref('')
const error = ref('')

function formatDate(value: string) {
  if (!value) return 'Today'
  const parsed = new Date(`${value}T00:00:00`)
  if (Number.isNaN(parsed.getTime())) return value
  return parsed.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
}

async function loadFeedback() {
  error.value = ''
  try {
    const resp = await workerFetch('/api/worker/daily-feedback/')
    const body = await resp.json().catch(() => null)
    if (!resp.ok || !body) {
      error.value = body?.error || 'Could not load feedback.'
      return
    }
    feedbackText.value = String(body.today_feedback?.feedback_text || '')
    recentFeedback.value = Array.isArray(body.recent_feedback) ? body.recent_feedback : []
  } catch {
    error.value = 'No connection. Try again.'
  }
}

async function saveFeedback() {
  if (busy.value) return
  if (!feedbackText.value) {
    error.value = 'Tell us how your day went.'
    message.value = ''
    return
  }
  busy.value = true
  error.value = ''
  message.value = ''
  try {
    const resp = await workerFetch('/api/worker/daily-feedback/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ feedback_text: feedbackText.value }),
    })
    const body = await resp.json().catch(() => null)
    if (!resp.ok || !body) {
      error.value = body?.feedback_text?.[0] || body?.error || 'Could not save feedback.'
      return
    }
    message.value = body.message || 'Daily feedback saved.'
    await loadFeedback()
  } catch {
    error.value = 'No connection. Try again.'
  } finally {
    busy.value = false
  }
}

onMounted(() => {
  loadFeedback()
})
</script>
