<template>
  <div class="space-y-4">
    <p class="text-sm text-slate-600">
      Here is what you asked to cover. Status updates when a supervisor has time to update the list.
    </p>

    <div v-if="loading" class="text-center py-16 text-slate-500">Loading…</div>

    <div v-else-if="error" class="rounded-xl bg-red-50 text-red-800 text-sm px-4 py-3 border border-red-100">
      {{ error }}
    </div>

    <div v-else-if="items.length === 0" class="text-center py-14 px-4 rounded-2xl bg-white border border-slate-200">
      <ClipboardDocumentIcon class="w-12 h-12 text-slate-300 mx-auto mb-3" aria-hidden="true" />
      <p class="text-slate-600 font-medium">No requests yet.</p>
      <p class="text-sm text-slate-500 mt-1">Use <strong>Shifts open</strong> to show interest.</p>
    </div>

    <ul v-else class="space-y-3">
      <li
        v-for="row in items"
        :key="row.id"
        class="bg-white rounded-2xl border border-slate-200 p-4 shadow-sm"
      >
        <div class="flex items-start justify-between gap-2 mb-2">
          <h3 class="font-semibold text-slate-900 text-base leading-snug">
            {{ row.open_shift?.role_title }}
          </h3>
          <span :class="badgeClass(row.status)" class="shrink-0 text-xs font-semibold px-2.5 py-1 rounded-full">
            {{ statusLabel(row.status) }}
          </span>
        </div>
        <p class="text-sm text-slate-500 mb-2">
          {{ row.open_shift?.location_display }} · {{ formatDate(row.open_shift?.shift_date) }}
          <span v-if="row.open_shift?.start_time">
            · {{ formatTime(row.open_shift.start_time) }} – {{ formatTime(row.open_shift.end_time) }}
          </span>
        </p>
        <p class="text-sm text-slate-600 leading-relaxed border-t border-slate-100 pt-3">
          {{ row.message_for_worker }}
        </p>
      </li>
    </ul>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ClipboardDocumentIcon } from '@heroicons/vue/24/outline'
import { workerFetch } from '../api'

interface OpenShiftNested {
  role_title: string
  location_display: string
  shift_date: string
  start_time?: string
  end_time?: string
}

interface InterestRow {
  id: number
  status: string
  message_for_worker: string
  open_shift: OpenShiftNested
}

const items = ref<InterestRow[]>([])
const loading = ref(true)
const error = ref('')

function formatDate(iso: string | undefined) {
  if (!iso) return ''
  const d = new Date(iso + 'T12:00:00')
  return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
}

function formatTime(t: string | undefined) {
  if (!t) return ''
  const [h, m] = t.split(':').map(Number)
  const d = new Date()
  d.setHours(h, m || 0, 0, 0)
  return d.toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' })
}

function statusLabel(s: string) {
  if (s === 'pending') return 'Noted'
  if (s === 'selected') return 'Picked'
  if (s === 'not_selected') return 'Filled other way'
  if (s === 'cancelled') return 'Closed'
  return s
}

function badgeClass(s: string) {
  if (s === 'selected') return 'bg-teal-100 text-teal-800'
  if (s === 'pending') return 'bg-amber-50 text-amber-900'
  if (s === 'not_selected') return 'bg-slate-100 text-slate-700'
  return 'bg-slate-100 text-slate-600'
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const resp = await workerFetch('/api/worker/shift-interests/')
    if (!resp.ok) {
      const j = await resp.json().catch(() => ({}))
      error.value = j.error || 'Could not load your requests.'
      return
    }
    items.value = await resp.json()
  } catch {
    error.value = 'No connection.'
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  load()
})
</script>
