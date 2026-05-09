<template>
  <section class="bg-white border border-slate-200 rounded-2xl p-4 shadow-sm space-y-3">
    <div class="flex items-start justify-between gap-3">
      <div>
        <h2 class="text-sm font-semibold text-slate-900">Shift clock</h2>
        <p class="text-xs text-slate-700">
          Time entries are verified by the system clock on the server.
        </p>
      </div>
      <span
        :class="isClockedIn ? 'bg-emerald-100 text-emerald-700' : 'bg-slate-100 text-slate-700'"
        class="text-xs font-semibold px-2.5 py-1 rounded-full"
      >
        {{ isClockedIn ? 'Clocked in' : 'Clocked out' }}
      </span>
    </div>

    <p class="text-xs text-slate-700">
      Server time:
      <strong class="text-slate-700 font-semibold">{{ formatDateTime(serverTime) }}</strong>
    </p>

    <button
      type="button"
      :disabled="busy"
      @click="submitPunch"
      class="w-full min-h-[48px] rounded-xl text-sm font-semibold text-white transition-colors disabled:cursor-not-allowed disabled:bg-slate-300"
      :class="isClockedIn ? 'bg-rose-600 hover:bg-rose-700' : 'bg-teal-600 hover:bg-teal-700'"
    >
      <span v-if="busy">{{ isClockedIn ? 'Clocking out…' : 'Clocking in…' }}</span>
      <span v-else>{{ isClockedIn ? 'Clock out' : 'Clock in' }}</span>
    </button>

    <p v-if="message" class="text-xs text-slate-600">{{ message }}</p>
    <p v-if="error" class="text-xs text-red-700">{{ error }}</p>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { workerFetch } from '../api'

type GeoStatus = 'captured' | 'denied' | 'unavailable' | 'timeout' | 'error' | 'skipped'

interface GeoPayload {
  status: GeoStatus
  latitude?: number
  longitude?: number
  accuracy?: number
  error?: string
  timestamp?: string
}

interface PunchStatusResponse {
  server_time: string
  is_clocked_in: boolean
}

const busy = ref(false)
const isClockedIn = ref(false)
const serverTime = ref('')
const error = ref('')
const message = ref('')

function formatDateTime(value: string) {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '—'
  return date.toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  })
}

function geoErrorPayload(geolocationError: GeolocationPositionError): GeoPayload {
  if (geolocationError.code === geolocationError.PERMISSION_DENIED) {
    return { status: 'denied', error: 'Permission denied by browser' }
  }
  if (geolocationError.code === geolocationError.POSITION_UNAVAILABLE) {
    return { status: 'unavailable', error: 'Position unavailable' }
  }
  if (geolocationError.code === geolocationError.TIMEOUT) {
    return { status: 'timeout', error: 'Location request timed out' }
  }
  return { status: 'error', error: geolocationError.message || 'Location lookup failed' }
}

function captureGeolocation(): Promise<GeoPayload> {
  return new Promise((resolve) => {
    if (!('geolocation' in navigator)) {
      resolve({ status: 'unavailable', error: 'Geolocation not supported' })
      return
    }

    navigator.geolocation.getCurrentPosition(
      (position) => {
        resolve({
          status: 'captured',
          latitude: position.coords.latitude,
          longitude: position.coords.longitude,
          accuracy: position.coords.accuracy,
          timestamp: new Date(position.timestamp).toISOString(),
        })
      },
      (positionError) => {
        resolve(geoErrorPayload(positionError))
      },
      {
        enableHighAccuracy: true,
        timeout: 8000,
        maximumAge: 0,
      }
    )
  })
}

async function loadStatus() {
  error.value = ''
  try {
    const resp = await workerFetch('/api/worker/time-punch/')
    const ct = resp.headers.get('content-type') || ''
    const body = ct.includes('application/json') ? await resp.json() : null
    if (!resp.ok || !body) {
      error.value = body?.error || 'Could not load clock status.'
      return
    }
    const data = body as PunchStatusResponse
    isClockedIn.value = Boolean(data.is_clocked_in)
    serverTime.value = data.server_time
  } catch {
    error.value = 'No connection. Try again.'
  }
}

async function submitPunch() {
  busy.value = true
  error.value = ''
  message.value = ''
  try {
    const geolocation = await captureGeolocation()
    const action = isClockedIn.value ? 'clock_out' : 'clock_in'
    const resp = await workerFetch('/api/worker/time-punch/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action, geolocation }),
    })
    const ct = resp.headers.get('content-type') || ''
    const body = ct.includes('application/json') ? await resp.json() : null
    if (!resp.ok || !body) {
      error.value = body?.error || 'Could not record time entry.'
      return
    }

    isClockedIn.value = action === 'clock_in'
    serverTime.value = body.server_time || ''
    message.value = body.message || 'Time entry recorded.'
  } catch {
    error.value = 'No connection. Try again.'
  } finally {
    busy.value = false
  }
}

onMounted(() => {
  loadStatus()
})
</script>
