<template>
  <div class="space-y-4">
    <p class="worker-section-intro">
      Your PitStop assignments. When a supervisor asks, take one photo at your post and send your location.
    </p>

    <div v-if="loading" class="text-center py-16 text-slate-500 text-base">Loading...</div>

    <div v-else-if="error" class="rounded-xl bg-red-50 text-red-800 text-sm px-4 py-3 border border-red-100">
      {{ error }}
    </div>

    <div v-else-if="assignments.length === 0" class="worker-card text-center py-14 px-4">
      <InboxIcon class="w-12 h-12 text-slate-300 mx-auto mb-3" aria-hidden="true" />
      <p class="text-slate-600 font-medium">No assignments posted.</p>
      <p class="text-sm text-slate-600 mt-1">Staff will text or call when work is assigned.</p>
    </div>

    <ul v-else class="space-y-4">
      <li v-for="assignment in assignments" :key="assignment.id" class="worker-card overflow-hidden">
        <div class="p-4 space-y-3">
          <div class="flex items-start justify-between gap-2">
            <h2 class="text-lg font-semibold text-slate-900 leading-snug">
              {{ assignment.work_site_name || 'PitStop assignment' }}
            </h2>
            <span class="shrink-0 text-xs font-semibold px-2.5 py-1 rounded-full bg-slate-100 text-slate-700">
              {{ assignment.status_display || assignment.status }}
            </span>
          </div>

          <div class="space-y-2 text-sm text-slate-700">
            <div class="flex gap-2 items-start">
              <MapPinIcon class="w-5 h-5 text-teal-600 shrink-0 mt-0.5" aria-hidden="true" />
              <span>{{ assignment.location_display }}</span>
            </div>
            <div class="flex gap-2 items-center">
              <CalendarDaysIcon class="w-5 h-5 text-teal-600 shrink-0" aria-hidden="true" />
              <span>{{ formatDate(assignment.assignment_date) }}</span>
            </div>
            <div class="flex gap-2 items-center">
              <ClockIcon class="w-5 h-5 text-teal-600 shrink-0" aria-hidden="true" />
              <span>{{ formatTime(assignment.start_time) }} - {{ formatTime(assignment.end_time) }}</span>
            </div>
          </div>

          <p v-if="assignment.assignment_notes" class="text-sm text-slate-700 border-t border-slate-100 pt-3">
            {{ assignment.assignment_notes }}
          </p>

          <div v-if="assignment.latest_proof" class="worker-status-note bg-emerald-50 text-emerald-900 border border-emerald-100">
            <CheckCircleIcon class="w-5 h-5 inline-block mr-1 align-text-bottom" aria-hidden="true" />
            Photo sent {{ formatDateTime(assignment.latest_proof.submitted_at) }}.
          </div>

          <label
            class="worker-btn worker-btn-primary cursor-pointer"
            :class="{ 'opacity-60 pointer-events-none': busyId === assignment.id || !assignment.can_submit_proof }"
          >
            <CameraIcon class="w-5 h-5" aria-hidden="true" />
            <span v-if="busyId === assignment.id">Sending...</span>
            <span v-else>Take photo and send location</span>
            <input
              class="sr-only"
              type="file"
              accept="image/*"
              capture="environment"
              :disabled="busyId === assignment.id || !assignment.can_submit_proof"
              @change="submitProof(assignment, $event)"
            />
          </label>

          <p class="worker-status-note bg-slate-50 text-slate-700 border border-slate-200">
            This does not clock you in or out. Your supervisor still confirms hours.
          </p>
        </div>
      </li>
    </ul>

    <p v-if="message" class="worker-status-note bg-slate-50 text-slate-800 border border-slate-200">{{ message }}</p>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import {
  CalendarDaysIcon,
  CameraIcon,
  CheckCircleIcon,
  ClockIcon,
  InboxIcon,
  MapPinIcon,
} from '@heroicons/vue/24/outline'
import { workerFetch } from '../api'

type GeoStatus = 'captured' | 'denied' | 'unavailable' | 'timeout' | 'error' | 'skipped'

interface WorkerAssignment {
  id: number
  work_site_name?: string
  location_display: string
  assignment_date: string
  start_time: string
  end_time: string
  status: string
  status_display?: string
  assignment_notes?: string
  can_submit_proof: boolean
  latest_proof?: {
    id: number
    submitted_at: string
    geo_basic_ok?: boolean
    geo_basic_note?: string
  } | null
}

interface GeoPayload {
  status: GeoStatus
  latitude?: number
  longitude?: number
  accuracy?: number
  error?: string
  timestamp?: string
}

const assignments = ref<WorkerAssignment[]>([])
const loading = ref(true)
const busyId = ref<number | null>(null)
const error = ref('')
const message = ref('')

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

function formatDateTime(iso: string) {
  if (!iso) return ''
  const d = new Date(iso)
  return d.toLocaleString(undefined, {
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
      (positionError) => resolve(geoErrorPayload(positionError)),
      { enableHighAccuracy: true, timeout: 8000, maximumAge: 0 }
    )
  })
}

async function loadAssignments() {
  loading.value = true
  error.value = ''
  try {
    const resp = await workerFetch('/api/worker/assignments/')
    const body = await resp.json().catch(() => null)
    if (!resp.ok || !body) {
      error.value = body?.error || 'Could not load assignments.'
      return
    }
    assignments.value = body
  } catch {
    error.value = 'No connection. Try again.'
  } finally {
    loading.value = false
  }
}

async function submitProof(assignment: WorkerAssignment, event: Event) {
  const input = event.target as HTMLInputElement
  const photo = input.files?.[0]
  if (!photo) return

  busyId.value = assignment.id
  error.value = ''
  message.value = ''
  try {
    const geolocation = await captureGeolocation()
    const form = new FormData()
    form.append('assignment_id', String(assignment.id))
    form.append('photo', photo)
    form.append('geolocation', JSON.stringify(geolocation))

    const resp = await workerFetch('/api/worker/shift-proof/', {
      method: 'POST',
      body: form,
    })
    const body = await resp.json().catch(() => null)
    if (!resp.ok || !body) {
      error.value = body?.error || body?.photo?.[0] || 'Could not send photo.'
      return
    }
    message.value = body.message || 'Photo and location sent.'
    await loadAssignments()
  } catch {
    error.value = 'No connection. Try again.'
  } finally {
    busyId.value = null
    input.value = ''
  }
}

onMounted(() => {
  loadAssignments()
})
</script>
