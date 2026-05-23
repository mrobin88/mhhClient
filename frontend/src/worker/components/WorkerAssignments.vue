<template>
  <div class="space-y-2">
    <p class="worker-section-intro">Clock in / out for your PitStop shift.</p>

    <div v-if="loading" class="flex items-center justify-center py-6 text-slate-500 text-sm">
      <span class="worker-spinner worker-spinner--dark" aria-hidden="true"></span>
      Loading
    </div>

    <div v-else-if="error" class="rounded-lg bg-red-50 text-red-800 text-xs px-3 py-2 border border-red-100">
      {{ error }}
    </div>

    <div v-else-if="sites.length === 0" class="worker-card text-center py-6 px-3">
      <InboxIcon class="w-7 h-7 text-slate-300 mx-auto mb-2" aria-hidden="true" />
      <p class="text-slate-600 text-sm font-medium">No active PitStop locations.</p>
      <p class="text-xs text-slate-500 mt-0.5">Ask staff to enable a work site.</p>
    </div>

    <section v-else class="worker-card p-3 space-y-2">
      <div class="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2">
        <p class="text-[10px] font-semibold uppercase tracking-wide text-slate-500">PitStop location</p>
        <p class="mt-0.5 text-sm font-semibold text-slate-900">{{ selectedSite?.name || 'Site not available' }}</p>
        <p v-if="selectedSite?.address" class="text-[11px] text-slate-600">{{ selectedSite.address }}</p>
      </div>

      <div class="worker-status-note bg-slate-50 text-slate-700 border border-slate-200">
        <ClockIcon class="w-3.5 h-3.5 inline-block mr-1 align-text-bottom" aria-hidden="true" />
        {{ activePunch ? `Clocked in ${formatDateTime(activePunch.clock_in_at)}` : 'Currently clocked out.' }}
      </div>

      <button
        type="button"
        class="worker-btn"
        :class="activePunch ? 'worker-btn-secondary' : 'worker-btn-primary'"
        :disabled="busy || cooldown || (!activePunch && !selectedSite)"
        @click="submitPunch()"
      >
        <span v-if="busy" class="worker-spinner" aria-hidden="true"></span>
        <StopCircleIcon v-else-if="activePunch" class="w-3.5 h-3.5" aria-hidden="true" />
        <PlayCircleIcon v-else class="w-3.5 h-3.5" aria-hidden="true" />
        <span v-if="busy">Sending</span>
        <span v-else-if="cooldown">Please wait…</span>
        <span v-else>{{ activePunch ? 'Clock out' : 'Clock in' }}</span>
      </button>
    </section>

    <p v-if="message" class="worker-status-note bg-slate-50 text-slate-800 border border-slate-200">{{ message }}</p>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import {
  ClockIcon,
  InboxIcon,
  PlayCircleIcon,
  StopCircleIcon,
} from '@heroicons/vue/24/outline'
import { workerFetch } from '../api'

type GeoStatus = 'captured' | 'denied' | 'unavailable' | 'timeout' | 'error' | 'skipped'

interface WorkSite {
  id: number
  name: string
  address: string
}

interface GeoPayload {
  status: GeoStatus
  latitude?: number
  longitude?: number
  accuracy?: number
  error?: string
  timestamp?: string
}

interface ActivePunch {
  id: number
  work_site: number | null
  work_site_name?: string
  clock_in_at: string
}

const PUNCH_COOLDOWN_MS = 2500

const sites = ref<WorkSite[]>([])
const selectedSiteId = ref<number | null>(null)
const activePunch = ref<ActivePunch | null>(null)
const loading = ref(true)
const busy = ref(false)
const cooldown = ref(false)
const error = ref('')
const message = ref('')
const selectedSite = computed(() => sites.value.find((site) => site.id === selectedSiteId.value) || null)
let cooldownTimer: ReturnType<typeof setTimeout> | null = null

function startCooldown() {
  cooldown.value = true
  if (cooldownTimer) clearTimeout(cooldownTimer)
  cooldownTimer = setTimeout(() => {
    cooldown.value = false
  }, PUNCH_COOLDOWN_MS)
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

async function loadClockContext() {
  loading.value = true
  error.value = ''
  try {
    const [sitesResp, punchResp] = await Promise.all([
      workerFetch('/api/worker/work-sites/'),
      workerFetch('/api/worker/time-punch/'),
    ])
    const sitesBody = await sitesResp.json().catch(() => null)
    const punchBody = await punchResp.json().catch(() => null)
    if (!sitesResp.ok || !sitesBody || !punchResp.ok || !punchBody) {
      error.value = sitesBody?.error || punchBody?.error || 'Could not load clock data.'
      return
    }
    sites.value = sitesBody
    activePunch.value = punchBody.active_punch
    if (activePunch.value?.work_site) {
      selectedSiteId.value = activePunch.value.work_site
    } else if (sites.value.length > 0) {
      selectedSiteId.value = sites.value[0].id
    } else {
      selectedSiteId.value = null
    }
  } catch {
    error.value = 'No connection. Try again.'
  } finally {
    loading.value = false
  }
}

async function submitPunch() {
  if (busy.value || cooldown.value) return
  if (!activePunch.value && !selectedSite.value) {
    error.value = 'No active PitStop location available.'
    return
  }
  busy.value = true
  startCooldown()
  error.value = ''
  message.value = ''
  try {
    const geolocation = await captureGeolocation()
    const action = activePunch.value ? 'clock_out' : 'clock_in'
    const resp = await workerFetch('/api/worker/time-punch/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        action,
        work_site_id: selectedSite.value?.id || selectedSiteId.value,
        geolocation,
      }),
    })
    if (resp.status === 429) {
      error.value = 'Too many requests. Wait a moment and try again.'
      return
    }
    const body = await resp.json().catch(() => null)
    if (!resp.ok || !body) {
      error.value = body?.error || body?.action?.[0] || 'Could not submit clock action.'
      return
    }
    message.value = body.message || 'Clock update saved.'
    await loadClockContext()
  } catch {
    error.value = 'No connection. Try again.'
  } finally {
    busy.value = false
  }
}

onMounted(() => {
  loadClockContext()
})

onBeforeUnmount(() => {
  if (cooldownTimer) clearTimeout(cooldownTimer)
})
</script>
