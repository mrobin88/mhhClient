<template>
  <div class="space-y-2">
    <p class="worker-section-intro">Tap to clock in or out for your shift. Location services must be on.</p>

    <div v-if="loading" class="flex items-center justify-center py-6 text-slate-300 text-sm">
      <span class="worker-spinner worker-spinner--dark" aria-hidden="true"></span>
      Loading
    </div>

    <div v-else-if="error" class="worker-status-note worker-status-note--error">
      {{ error }}
    </div>

    <section v-else class="worker-card p-3 space-y-2">
      <div class="flex items-center justify-between gap-2">
        <h2 class="worker-card-title">Shift clock</h2>
        <span class="worker-pill" :class="activePunch ? 'worker-pill-green' : 'worker-pill-slate'">
          {{ activePunch ? 'Live position' : 'Flat' }}
        </span>
      </div>

      <div class="worker-status-note worker-status-note--ok">
        <ClockIcon class="w-3.5 h-3.5 inline-block mr-1 align-text-bottom" aria-hidden="true" />
        <template v-if="isOnLunch">
          On lunch since {{ formatDateTime(activePunch?.lunch_start_at) }}
        </template>
        <template v-else-if="activePunch">
          Clocked in for <strong>{{ activeDurationLabel }}</strong> · since {{ formatDateTime(activePunch.clock_in_at) }}
        </template>
        <template v-else>
          Currently clocked out.
        </template>
      </div>

      <div class="worker-metric-grid">
        <div class="worker-metric">
          <p class="worker-metric-label">Today</p>
          <p class="worker-metric-value">{{ formatHours(todayDisplayHours) }}</p>
        </div>
        <div class="worker-metric">
          <p class="worker-metric-label">This week</p>
          <p class="worker-metric-value">{{ formatHours(weekDisplayHours) }}</p>
        </div>
      </div>

      <div class="worker-action-grid">
        <button
          v-if="isOnLunch"
          type="button"
          class="worker-action-card worker-action-card-primary worker-action-card-full"
          :disabled="busy || cooldown"
          @click="submitAction('end_lunch')"
        >
          <span class="worker-action-kicker">Lunch</span>
          <span class="worker-action-title">
            <span v-if="busy">Sending…</span>
            <span v-else-if="cooldown">Please wait…</span>
            <span v-else>End lunch</span>
          </span>
        </button>

        <template v-else>
          <button
            type="button"
            class="worker-action-card"
            :class="activePunch ? 'worker-action-card-muted' : 'worker-action-card-primary'"
            :disabled="busy || cooldown"
            @click="submitAction(activePunch ? 'clock_out' : 'clock_in')"
          >
            <span class="worker-action-kicker">Shift</span>
            <span class="worker-action-title">
              <span v-if="busy">Sending…</span>
              <span v-else-if="cooldown">Please wait…</span>
              <span v-else>{{ activePunch ? 'Clock out' : 'Clock in' }}</span>
            </span>
            <StopCircleIcon v-if="!busy && activePunch" class="w-3.5 h-3.5" aria-hidden="true" />
            <PlayCircleIcon v-else-if="!busy" class="w-3.5 h-3.5" aria-hidden="true" />
          </button>

          <button
            v-if="canStartLunch"
            type="button"
            class="worker-action-card worker-action-card-muted worker-action-card-compact"
            :disabled="busy || cooldown"
            @click="submitAction('start_lunch')"
          >
            <span class="worker-action-kicker">Break</span>
            <span class="worker-action-title">Start lunch</span>
          </button>
        </template>
      </div>
    </section>

    <p v-if="message" class="worker-status-note worker-status-note--ok">{{ message }}</p>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import {
  ClockIcon,
  PlayCircleIcon,
  StopCircleIcon,
} from '@heroicons/vue/24/outline'
import { workerFetch } from '../api'

interface ActivePunch {
  id: number
  clock_in_at: string
  lunch_start_at: string | null
  lunch_end_at: string | null
  is_on_lunch: boolean
}

interface Coordinates {
  latitude: number
  longitude: number
  accuracy?: number
}

interface LocationReference {
  label: string
  mapBlob: Blob | null
  latitude: number
  longitude: number
  accuracy?: number
}

const PUNCH_COOLDOWN_MS = 2500
const LIVE_TICK_MS = 30_000
const OSM_STATIC_MAP = 'https://staticmap.openstreetmap.de/staticmap.php'

const activePunch = ref<ActivePunch | null>(null)
const todayHours = ref(0)
const weekHours = ref(0)
const nowTick = ref(Date.now())
const loading = ref(true)
const busy = ref(false)
const cooldown = ref(false)
const error = ref('')
const message = ref('')
let cooldownTimer: ReturnType<typeof setTimeout> | null = null
let liveTimer: ReturnType<typeof setInterval> | null = null

const isOnLunch = computed(() => Boolean(activePunch.value?.is_on_lunch))
const canStartLunch = computed(
  () => Boolean(activePunch.value) && !isOnLunch.value && !activePunch.value?.lunch_start_at,
)

const activeElapsedMs = computed(() => {
  if (!activePunch.value?.clock_in_at) return 0
  const started = new Date(activePunch.value.clock_in_at).getTime()
  if (Number.isNaN(started)) return 0
  return Math.max(nowTick.value - started, 0)
})

const activeDurationLabel = computed(() => {
  const totalMinutes = Math.floor(activeElapsedMs.value / 60_000)
  const hours = Math.floor(totalMinutes / 60)
  const minutes = totalMinutes % 60
  if (hours === 0) return `${minutes}m`
  return `${hours}h ${minutes}m`
})

const todayDisplayHours = computed(() => todayHours.value + activeElapsedMs.value / 3_600_000)
const weekDisplayHours = computed(() => weekHours.value + activeElapsedMs.value / 3_600_000)

function formatHours(hours: number) {
  if (!Number.isFinite(hours) || hours <= 0) return '0.00 hrs'
  return `${hours.toFixed(2)} hrs`
}

function startCooldown() {
  cooldown.value = true
  if (cooldownTimer) clearTimeout(cooldownTimer)
  cooldownTimer = setTimeout(() => {
    cooldown.value = false
  }, PUNCH_COOLDOWN_MS)
}

function formatDateTime(iso: string | null | undefined) {
  if (!iso) return ''
  const d = new Date(iso)
  return d.toLocaleString('en-US', {
    timeZone: 'America/Los_Angeles',
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  })
}

function captureCoordinates(): Promise<Coordinates> {
  return new Promise((resolve, reject) => {
    if (!('geolocation' in navigator)) {
      reject(new Error('Turn on location services to continue.'))
      return
    }
    navigator.geolocation.getCurrentPosition(
      (position) => {
        resolve({
          latitude: position.coords.latitude,
          longitude: position.coords.longitude,
          accuracy: position.coords.accuracy,
        })
      },
      (positionError) => {
        if (positionError.code === positionError.PERMISSION_DENIED) {
          reject(new Error('Location permission is required. Turn on location services.'))
          return
        }
        reject(new Error('Could not get your location. Turn on location services and try again.'))
      },
      { enableHighAccuracy: true, timeout: 8000, maximumAge: 0 },
    )
  })
}

async function reverseGeocodeLabel(latitude: number, longitude: number): Promise<string> {
  try {
    const url = new URL('https://nominatim.openstreetmap.org/reverse')
    url.searchParams.set('format', 'json')
    url.searchParams.set('lat', String(latitude))
    url.searchParams.set('lon', String(longitude))
    url.searchParams.set('zoom', '18')
    const resp = await fetch(url.toString(), {
      headers: { Accept: 'application/json' },
    })
    if (!resp.ok) return ''
    const data = await resp.json()
    return String(data.display_name || '').slice(0, 300)
  } catch {
    return ''
  }
}

async function fetchMapSnapshot(latitude: number, longitude: number): Promise<Blob | null> {
  const params = new URLSearchParams({
    center: `${latitude},${longitude}`,
    zoom: '16',
    size: '400x200',
    markers: `${latitude},${longitude}`,
  })
  try {
    const resp = await fetch(`${OSM_STATIC_MAP}?${params.toString()}`)
    if (!resp.ok) return null
    return await resp.blob()
  } catch {
    return null
  }
}

async function buildLocationReference(coords: Coordinates): Promise<LocationReference> {
  const [label, mapBlob] = await Promise.all([
    reverseGeocodeLabel(coords.latitude, coords.longitude),
    fetchMapSnapshot(coords.latitude, coords.longitude),
  ])
  return {
    label,
    mapBlob,
    latitude: coords.latitude,
    longitude: coords.longitude,
    accuracy: coords.accuracy,
  }
}

async function loadClockContext() {
  loading.value = true
  error.value = ''
  try {
    const punchResp = await workerFetch('/api/worker/time-punch/')
    const punchBody = await punchResp.json().catch(() => null)
    if (!punchResp.ok || !punchBody) {
      error.value = punchBody?.error || 'Could not load clock data.'
      return
    }
    activePunch.value = punchBody.active_punch
    todayHours.value = Number(punchBody.today_hours) || 0
    weekHours.value = Number(punchBody.week_hours) || 0
    nowTick.value = Date.now()
  } catch {
    error.value = 'No connection. Try again.'
  } finally {
    loading.value = false
  }
}

async function submitAction(action: 'clock_in' | 'clock_out' | 'start_lunch' | 'end_lunch') {
  if (busy.value || cooldown.value) return
  busy.value = true
  startCooldown()
  error.value = ''
  message.value = ''
  try {
    const coordinates = await captureCoordinates()
    const form = new FormData()
    form.append('action', action)
    form.append(
      'geolocation',
      JSON.stringify({
        status: 'captured',
        latitude: coordinates.latitude,
        longitude: coordinates.longitude,
        accuracy: coordinates.accuracy,
      }),
    )

    if (action === 'clock_in' || action === 'clock_out') {
      const location = await buildLocationReference(coordinates)
      if (location.label) form.append('location_label', location.label)
      if (location.mapBlob) form.append('map_snapshot', location.mapBlob, 'map_snapshot.png')
      form.append('map_latitude', String(location.latitude))
      form.append('map_longitude', String(location.longitude))
    }

    const resp = await workerFetch('/api/worker/time-punch/', {
      method: 'POST',
      body: form,
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
  } catch (submitError) {
    if (submitError instanceof Error) {
      error.value = submitError.message
    } else {
      error.value = 'No connection. Try again.'
    }
  } finally {
    busy.value = false
  }
}

onMounted(() => {
  loadClockContext()
  liveTimer = setInterval(() => {
    nowTick.value = Date.now()
  }, LIVE_TICK_MS)
})

onBeforeUnmount(() => {
  if (cooldownTimer) clearTimeout(cooldownTimer)
  if (liveTimer) clearInterval(liveTimer)
})
</script>
