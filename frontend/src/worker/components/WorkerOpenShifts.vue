<template>
  <div class="space-y-4">
    <p class="text-sm text-slate-600 leading-relaxed">
      These shifts need someone to cover. Tap <strong class="text-slate-800">I’m interested</strong> if you can help.
      A supervisor may call or message you — it is not a guarantee until they confirm.
    </p>

    <div v-if="loading" class="text-center py-16 text-slate-500 text-base">Loading…</div>

    <div v-else-if="error" class="rounded-xl bg-red-50 text-red-800 text-sm px-4 py-3 border border-red-100">
      {{ error }}
    </div>

    <div v-else-if="shifts.length === 0" class="text-center py-14 px-4 rounded-2xl bg-white border border-slate-200">
      <InboxIcon class="w-12 h-12 text-slate-300 mx-auto mb-3" aria-hidden="true" />
      <p class="text-slate-600 font-medium">No open shifts right now.</p>
      <p class="text-sm text-slate-500 mt-1">Check back later.</p>
    </div>

    <ul v-else class="space-y-4">
      <li
        v-for="shift in shifts"
        :key="shift.id"
        class="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden"
      >
        <div class="p-4 space-y-3">
          <h2 class="text-lg font-semibold text-slate-900 leading-snug">
            {{ shift.role_title }}
          </h2>

          <div class="space-y-2 text-sm text-slate-600">
            <div class="flex gap-2 items-start">
              <MapPinIcon class="w-5 h-5 text-teal-600 shrink-0 mt-0.5" aria-hidden="true" />
              <span>{{ shift.location_display }}</span>
            </div>
            <div class="flex gap-2 items-center">
              <CalendarDaysIcon class="w-5 h-5 text-teal-600 shrink-0" aria-hidden="true" />
              <span>{{ formatDate(shift.shift_date) }}</span>
            </div>
            <div class="flex gap-2 items-center">
              <ClockIcon class="w-5 h-5 text-teal-600 shrink-0" aria-hidden="true" />
              <span>{{ formatTime(shift.start_time) }} – {{ formatTime(shift.end_time) }}</span>
            </div>
          </div>

          <p v-if="shift.notes" class="text-sm text-slate-500 border-t border-slate-100 pt-3">
            {{ shift.notes }}
          </p>

          <button
            type="button"
            :disabled="submittingId === shift.id || requestedIds.has(shift.id)"
            @click="submitInterest(shift.id)"
            class="w-full min-h-[52px] rounded-xl bg-teal-600 hover:bg-teal-700 disabled:bg-slate-300 disabled:cursor-not-allowed text-white text-base font-semibold shadow-sm transition-colors"
          >
            <span v-if="submittingId === shift.id">Sending…</span>
            <span v-else-if="requestedIds.has(shift.id)">Interest sent</span>
            <span v-else>I’m interested</span>
          </button>
        </div>
      </li>
    </ul>

    <div
      v-if="toast"
      class="fixed bottom-24 left-4 right-4 max-w-lg mx-auto rounded-xl bg-slate-900 text-white text-sm px-4 py-3 shadow-lg z-30"
      role="status"
    >
      {{ toast }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import {
  MapPinIcon,
  CalendarDaysIcon,
  ClockIcon,
  InboxIcon,
} from '@heroicons/vue/24/outline'
import { workerFetch } from '../api'

const emit = defineEmits<{
  'interest-recorded': []
}>()

interface OpenShiftRow {
  id: number
  role_title: string
  location_display: string
  shift_date: string
  start_time: string
  end_time: string
  notes?: string
}

const shifts = ref<OpenShiftRow[]>([])
const loading = ref(true)
const error = ref('')
const submittingId = ref<number | null>(null)
const requestedIds = ref<Set<number>>(new Set())
const toast = ref('')

function formatDate(iso: string) {
  if (!iso) return ''
  const d = new Date(iso + 'T12:00:00')
  return d.toLocaleDateString(undefined, {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })
}

function formatTime(t: string) {
  if (!t) return ''
  const [h, m] = t.split(':').map(Number)
  const d = new Date()
  d.setHours(h, m || 0, 0, 0)
  return d.toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' })
}

async function loadOpenShifts() {
  loading.value = true
  error.value = ''
  try {
    const resp = await workerFetch('/api/worker/open-shifts/')
    const ct = resp.headers.get('content-type') || ''
    if (!resp.ok) {
      if (ct.includes('application/json')) {
        const j = await resp.json()
        error.value = j.error || j.detail || 'Could not load shifts.'
      } else {
        error.value = 'Could not load shifts. Try again.'
      }
      return
    }
    shifts.value = await resp.json()
  } catch {
    error.value = 'No connection. Try again.'
  } finally {
    loading.value = false
  }
}

async function submitInterest(openShiftId: number) {
  submittingId.value = openShiftId
  toast.value = ''
  try {
    const resp = await workerFetch('/api/worker/shift-interests/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ open_shift_id: openShiftId }),
    })
    const ct = resp.headers.get('content-type') || ''
    const data = ct.includes('application/json') ? await resp.json() : null

    if (resp.status === 201) {
      requestedIds.value = new Set(requestedIds.value).add(openShiftId)
      toast.value =
        'Thanks — we noted your interest. A supervisor may reach out if you are picked.'
      window.setTimeout(() => {
        toast.value = ''
        emit('interest-recorded')
      }, 2200)
    } else if (data?.interest) {
      requestedIds.value = new Set(requestedIds.value).add(openShiftId)
      toast.value = data.error || 'You already signed up for this one.'
      window.setTimeout(() => (toast.value = ''), 3000)
    } else {
      toast.value = data?.error || 'Something went wrong. Try again.'
      window.setTimeout(() => (toast.value = ''), 3000)
    }
  } catch {
    toast.value = 'No connection. Try again.'
    window.setTimeout(() => (toast.value = ''), 3000)
  } finally {
    submittingId.value = null
  }
}

onMounted(() => {
  loadOpenShifts()
})
</script>
