<template>
  <section class="space-y-4">
    <p class="worker-section-intro">
      Request days off so supervisors can plan coverage.
    </p>

    <form @submit.prevent="submitRequest" class="worker-card p-4 space-y-4">
      <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <div>
          <label for="start-date" class="worker-label">Start date</label>
          <input
            id="start-date"
            v-model="startDate"
            type="date"
            required
            class="worker-field"
          />
        </div>
        <div>
          <label for="end-date" class="worker-label">End date</label>
          <input
            id="end-date"
            v-model="endDate"
            type="date"
            required
            class="worker-field"
          />
        </div>
      </div>
      <div>
        <label for="reason" class="worker-label">Reason</label>
        <textarea
          id="reason"
          v-model="reason"
          rows="4"
          maxlength="4000"
          required
          placeholder="Example: Doctor appointment and family care."
          class="worker-field worker-textarea"
        />
      </div>
      <button
        type="submit"
        :disabled="submitting"
        class="worker-btn worker-btn-primary"
      >
        <span v-if="submitting">Sending request…</span>
        <span v-else>Send time-off request</span>
      </button>
      <p v-if="error" class="worker-status-note bg-red-50 text-red-800 border border-red-200">{{ error }}</p>
      <p v-if="success" class="worker-status-note bg-emerald-50 text-emerald-800 border border-emerald-200">{{ success }}</p>
    </form>

    <div class="space-y-3">
      <h3 class="text-sm font-semibold text-slate-800">Recent requests</h3>
      <div v-if="loading" class="text-sm text-slate-600 py-3">Loading…</div>
      <div v-else-if="items.length === 0" class="text-sm text-slate-600 py-3">No time-off requests yet.</div>
      <ul v-else class="space-y-3">
        <li v-for="item in items" :key="item.id" class="worker-card p-4">
          <div class="flex items-center justify-between gap-2 mb-2">
            <span :class="statusClass(item.status)" class="text-xs font-semibold px-2 py-1 rounded-full">
              {{ item.status_label }}
            </span>
            <span class="text-xs text-slate-600">{{ formatDate(item.created_at) }}</span>
          </div>
          <p class="text-sm text-slate-700">
            {{ item.start_date }} to {{ item.end_date }}
          </p>
          <p class="text-sm text-slate-700 mt-2 whitespace-pre-wrap">{{ item.reason }}</p>
          <p v-if="item.staff_note" class="mt-3 text-xs text-slate-600 bg-slate-50 border border-slate-200 rounded-lg p-2">
            Staff note: {{ item.staff_note }}
          </p>
        </li>
      </ul>
    </div>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { workerFetch } from '../api'

interface TimeOffRow {
  id: number
  start_date: string
  end_date: string
  reason: string
  status: string
  status_label: string
  staff_note: string
  created_at: string
}

const loading = ref(true)
const submitting = ref(false)
const items = ref<TimeOffRow[]>([])
const startDate = ref('')
const endDate = ref('')
const reason = ref('')
const error = ref('')
const success = ref('')

function statusClass(status: string) {
  if (status === 'approved') return 'bg-emerald-100 text-emerald-800'
  if (status === 'denied') return 'bg-rose-100 text-rose-700'
  if (status === 'cancelled') return 'bg-slate-200 text-slate-700'
  return 'bg-amber-100 text-amber-800'
}

function formatDate(value: string) {
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return '—'
  return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const resp = await workerFetch('/api/worker/time-off-requests/')
    const body = await resp.json().catch(() => null)
    if (!resp.ok || !Array.isArray(body)) {
      error.value = body?.error || 'Could not load requests.'
      return
    }
    items.value = body as TimeOffRow[]
  } catch {
    error.value = 'No connection. Try again.'
  } finally {
    loading.value = false
  }
}

async function submitRequest() {
  if (!startDate.value || !endDate.value) {
    error.value = 'Start and end dates are required.'
    return
  }
  if (!reason.value.trim()) {
    error.value = 'Reason is required.'
    return
  }

  submitting.value = true
  error.value = ''
  success.value = ''
  try {
    const resp = await workerFetch('/api/worker/time-off-requests/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        start_date: startDate.value,
        end_date: endDate.value,
        reason: reason.value.trim(),
      }),
    })
    const body = await resp.json().catch(() => null)
    if (!resp.ok || !body) {
      error.value = body?.end_date?.[0] || body?.reason?.[0] || body?.error || 'Could not send request.'
      return
    }
    success.value = 'Time-off request sent.'
    startDate.value = ''
    endDate.value = ''
    reason.value = ''
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
