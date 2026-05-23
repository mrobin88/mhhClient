<template>
  <div class="space-y-4">
    <p class="worker-section-intro">Clock in and out for your assigned PitStop shift.</p>

    <div v-if="loading" class="text-center py-16 text-slate-500 text-base">Loading...</div>

    <div v-else-if="error" class="rounded-xl bg-red-50 text-red-800 text-sm px-4 py-3 border border-red-100">
      {{ error }}
    </div>

    <div v-else-if="sites.length === 0" class="worker-card text-center py-14 px-4">
      <InboxIcon class="w-12 h-12 text-slate-300 mx-auto mb-3" aria-hidden="true" />
      <p class="text-slate-600 font-medium">No active PitStop locations.</p>
      <p class="text-sm text-slate-600 mt-1">Ask staff to enable at least one work site.</p>
    </div>

    <section v-else class="worker-card p-4 sm:p-5 space-y-4">
      <div class="rounded-xl border border-slate-200 bg-slate-50 px-3.5 py-3">
        <p class="text-[11px] font-semibold uppercase tracking-wide text-slate-500">PitStop location</p>
        <p class="mt-1 text-sm font-semibold text-slate-900">{{ selectedSite?.name || 'Site not available' }}</p>
        <p v-if="selectedSite?.address" class="mt-0.5 text-xs text-slate-600">{{ selectedSite.address }}</p>
      </div>

      <div class="worker-status-note bg-slate-50 text-slate-700 border border-slate-200">
        <ClockIcon class="w-4 h-4 inline-block mr-1.5 align-text-bottom" aria-hidden="true" />
        {{ activePunch ? `Clocked in at ${activePunch.work_site_name} ${formatDateTime(activePunch.clock_in_at)}` : 'Currently clocked out.' }}
      </div>

      <button
        type="button"
        class="worker-btn worker-btn-normalized"
        :class="activePunch ? 'worker-btn-secondary' : 'worker-btn-primary'"
        :disabled="busy || (!activePunch && !selectedSite)"
        @click="submitPunch()"
      >
        <StopCircleIcon v-if="activePunch" class="w-4 h-4" aria-hidden="true" />
        <PlayCircleIcon v-else class="w-4 h-4" aria-hidden="true" />
        <span v-if="busy">Sending...</span>
        <span v-else>{{ activePunch ? 'Clock out' : 'Clock in' }}</span>
      </button>
    </section>

    <p v-if="message" class="worker-status-note bg-slate-50 text-slate-800 border border-slate-200">{{ message }}</p>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
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

const sites = ref<WorkSite[]>([])
const selectedSiteId = ref<number | null>(null)
const activePunch = ref<ActivePunch | null>(null)
const loading = ref(true)
const busy = ref(false)
const error = ref('')
const message = ref('')
const selectedSite = computed(() => sites.value.find((site) => site.id === selectedSiteId.value) || null)

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
  if (!activePunch.value && !selectedSite.value) {
    error.value = 'No active PitStop location available.'
    return
  }
  busy.value = true
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
</script>

<style scoped>
.worker-btn-normalized {
  min-height: 44px;
  font-size: 0.95rem;
  font-weight: 700;
  border-radius: 0.75rem;
}

@media (max-width: 1024px) {
  .worker-btn-normalized {
    min-height: 46px;
    font-size: 0.94rem;
  }
}
</style>
