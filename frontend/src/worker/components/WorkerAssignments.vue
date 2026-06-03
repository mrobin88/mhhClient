<template>
  <div class="space-y-2">
    <p class="worker-section-intro">Tap to clock in or out for your shift.</p>

    <div v-if="loading" class="flex items-center justify-center py-6 text-slate-500 text-sm">
      <span class="worker-spinner worker-spinner--dark" aria-hidden="true"></span>
      Loading
    </div>

    <div v-else-if="error" class="rounded-lg bg-red-50 text-red-800 text-xs px-3 py-2 border border-red-100">
      {{ error }}
    </div>

    <section v-else class="worker-card p-3 space-y-2">
      <div class="worker-status-note bg-slate-50 text-slate-700 border border-slate-200">
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

      <div class="grid grid-cols-2 gap-2">
        <div class="rounded-lg border border-slate-200 bg-slate-50 px-2.5 py-1.5">
          <p class="text-[10px] font-semibold uppercase tracking-wide text-slate-500">Today</p>
          <p class="text-sm font-bold text-slate-900">{{ formatHours(todayDisplayHours) }}</p>
        </div>
        <div class="rounded-lg border border-slate-200 bg-slate-50 px-2.5 py-1.5">
          <p class="text-[10px] font-semibold uppercase tracking-wide text-slate-500">This week</p>
          <p class="text-sm font-bold text-slate-900">{{ formatHours(weekDisplayHours) }}</p>
        </div>
      </div>

      <button
        v-if="isOnLunch"
        type="button"
        class="worker-btn worker-btn-primary"
        :disabled="busy || cooldown"
        @click="submitAction('end_lunch')"
      >
        <span v-if="busy" class="worker-spinner" aria-hidden="true"></span>
        <span v-if="busy">Sending</span>
        <span v-else-if="cooldown">Please wait…</span>
        <span v-else>End lunch</span>
      </button>

      <button
        v-else
        type="button"
        class="worker-btn"
        :class="activePunch ? 'worker-btn-secondary' : 'worker-btn-primary'"
        :disabled="busy || cooldown"
        @click="submitAction(activePunch ? 'clock_out' : 'clock_in')"
      >
        <span v-if="busy" class="worker-spinner" aria-hidden="true"></span>
        <StopCircleIcon v-else-if="activePunch" class="w-3.5 h-3.5" aria-hidden="true" />
        <PlayCircleIcon v-else class="w-3.5 h-3.5" aria-hidden="true" />
        <span v-if="busy">Sending</span>
        <span v-else-if="cooldown">Please wait…</span>
        <span v-else>{{ activePunch ? 'Clock out' : 'Clock in' }}</span>
      </button>

      <button
        v-if="canStartLunch"
        type="button"
        class="worker-btn worker-btn-secondary"
        :disabled="busy || cooldown"
        @click="submitAction('start_lunch')"
      >
        Start lunch
      </button>
    </section>

    <p v-if="message" class="worker-status-note bg-slate-50 text-slate-800 border border-slate-200">{{ message }}</p>
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

interface LocationReference {
  label: string
  mapBlob: Blob | null
  latitude?: number
  longitude?: number
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

function captureCoordinates(): Promise<{ latitude: number; longitude: number } | null> {
  return new Promise((resolve) => {
    if (!('geolocation' in navigator)) {
      resolve(null)
      return
    }
    navigator.geolocation.getCurrentPosition(
      (position) => {
        resolve({
          latitude: position.coords.latitude,
          longitude: position.coords.longitude,
        })
      },
      () => resolve(null),
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

async function buildLocationReference(): Promise<LocationReference> {
  const coords = await captureCoordinates()
  if (!coords) {
    return { label: '', mapBlob: null }
  }
  const [label, mapBlob] = await Promise.all([
    reverseGeocodeLabel(coords.latitude, coords.longitude),
    fetchMapSnapshot(coords.latitude, coords.longitude),
  ])
  return {
    label,
    mapBlob,
    latitude: coords.latitude,
    longitude: coords.longitude,
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
    const form = new FormData()
    form.append('action', action)

    if (action === 'clock_in' || action === 'clock_out') {
      const location = await buildLocationReference()
      if (location.label) form.append('location_label', location.label)
      if (location.mapBlob) form.append('map_snapshot', location.mapBlob, 'map_snapshot.png')
      if (location.latitude != null && location.longitude != null) {
        form.append('map_latitude', String(location.latitude))
        form.append('map_longitude', String(location.longitude))
      }
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
  } catch {
    error.value = 'No connection. Try again.'
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
