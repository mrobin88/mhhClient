<template>
  <section class="space-y-4">
    <p class="worker-section-intro">
      Send quick updates to staff about restroom checks, incidents, or supply needs.
    </p>

    <form @submit.prevent="submitNote" class="worker-card p-4 space-y-4">
      <div>
        <label for="note-type" class="worker-label">Type</label>
        <select
          id="note-type"
          v-model="noteType"
          class="worker-field"
        >
          <option value="general">General update</option>
          <option value="restroom_check">Restroom check update</option>
          <option value="incident">Incident report</option>
          <option value="supply">Supply request</option>
        </select>
      </div>
      <div>
        <label for="note-content" class="worker-label">Note</label>
        <textarea
          id="note-content"
          v-model="content"
          rows="4"
          maxlength="4000"
          placeholder="Example: Restroom at Mission & 16th checked at 9:15am, all clean, low paper towels."
          class="worker-field worker-textarea"
        />
      </div>
      <button
        type="submit"
        :disabled="submitting"
        class="worker-btn worker-btn-primary"
      >
        <span v-if="submitting">Sending note…</span>
        <span v-else>Send note to staff</span>
      </button>
      <p v-if="error" class="worker-status-note bg-red-50 text-red-800 border border-red-200">{{ error }}</p>
      <p v-if="success" class="worker-status-note bg-emerald-50 text-emerald-800 border border-emerald-200">{{ success }}</p>
    </form>

    <div class="space-y-3">
      <h3 class="text-sm font-semibold text-slate-800">Recent notes</h3>
      <div v-if="loading" class="text-sm text-slate-600 py-3">Loading…</div>
      <div v-else-if="items.length === 0" class="text-sm text-slate-600 py-3">No notes yet.</div>
      <ul v-else class="space-y-3">
        <li v-for="item in items" :key="item.id" class="worker-card p-4">
          <div class="flex items-center justify-between gap-2 mb-2">
            <span class="text-xs font-semibold px-2 py-1 rounded-full bg-slate-100 text-slate-700">
              {{ item.note_type_label }}
            </span>
            <span class="text-xs text-slate-600">{{ formatDateTime(item.created_at) }}</span>
          </div>
          <p class="text-sm text-slate-700 whitespace-pre-wrap">{{ item.content }}</p>
          <p v-if="item.staff_response" class="mt-3 text-xs text-slate-600 bg-slate-50 border border-slate-200 rounded-lg p-2">
            Staff note: {{ item.staff_response }}
          </p>
        </li>
      </ul>
    </div>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { workerFetch } from '../api'

interface WorkerNote {
  id: number
  note_type_label: string
  content: string
  staff_response: string
  created_at: string
}

const loading = ref(true)
const submitting = ref(false)
const items = ref<WorkerNote[]>([])
const noteType = ref('general')
const content = ref('')
const error = ref('')
const success = ref('')

function formatDateTime(value: string) {
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return '—'
  return d.toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  })
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const resp = await workerFetch('/api/worker/notes/')
    const body = await resp.json().catch(() => null)
    if (!resp.ok || !Array.isArray(body)) {
      error.value = body?.error || 'Could not load notes.'
      return
    }
    items.value = body as WorkerNote[]
  } catch {
    error.value = 'No connection. Try again.'
  } finally {
    loading.value = false
  }
}

async function submitNote() {
  const trimmed = content.value.trim()
  if (!trimmed) {
    error.value = 'Please enter a note before sending.'
    return
  }

  submitting.value = true
  error.value = ''
  success.value = ''
  try {
    const resp = await workerFetch('/api/worker/notes/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ note_type: noteType.value, content: trimmed }),
    })
    const body = await resp.json().catch(() => null)
    if (!resp.ok || !body) {
      error.value = body?.content?.[0] || body?.error || 'Could not send note.'
      return
    }
    success.value = 'Note sent.'
    content.value = ''
    await load()
  } catch {
    error.value = 'No connection. Try again.'
  } finally {
    submitting.value = false
  }
}

onMounted(() => {
  load()
})
</script>
