<template>
  <div class="staff-cal">
    <div class="staff-cal-nav">
      <button type="button" class="staff-btn staff-btn-secondary staff-btn-sm" @click="shiftMonth(-1)">
        Previous
      </button>
      <h4>{{ monthLabel }}</h4>
      <button type="button" class="staff-btn staff-btn-secondary staff-btn-sm" @click="shiftMonth(1)">
        Next
      </button>
    </div>
    <p v-if="loading" class="text-sm text-stone-500 px-1">Loading calendar…</p>
    <p v-else-if="error" class="text-sm text-stone-500 px-1">{{ error }}</p>
    <div v-else class="staff-cal-grid" role="grid" aria-label="Class calendar">
      <span v-for="day in WEEKDAYS" :key="day" class="staff-cal-dow">{{ day }}</span>
      <div
        v-for="cell in cells"
        :key="cell.key"
        class="staff-cal-cell"
        :class="{
          'is-outside': !cell.inMonth,
          'is-today': cell.isToday,
        }"
      >
        <span class="staff-cal-num">{{ cell.day }}</span>
        <button
          v-for="s in cell.sessions"
          :key="s.id"
          type="button"
          class="staff-cal-event"
          :class="[`is-${s.program || 'general'}`, { 'is-selected': selectedId === s.id, 'is-cancelled': s.status === 'cancelled' }]"
          @click="select(s)"
        >
          <span class="staff-cal-event-name">{{ s.template_name }}</span>
          <span class="staff-cal-event-meta">
            {{ formatTime(s.start_time) }}
            · {{ s.enrolled_count }}
          </span>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { staffFetch } from '../api'

export interface CalendarSession {
  id: number
  template_id: number
  template_name: string
  program: string
  program_display: string
  session_date: string
  start_time: string
  end_time: string
  location: string
  facilitator: string
  capacity: number
  enrolled_count: number
  spots_remaining: number
  status: 'scheduled' | 'completed' | 'cancelled'
}

defineProps<{ selectedId?: number | null }>()
const emit = defineEmits<{ select: [session: CalendarSession] }>()

const WEEKDAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']

const cursor = ref(startOfMonth(new Date()))
const sessions = ref<CalendarSession[]>([])
const loading = ref(true)
const error = ref('')

const monthKey = computed(() => {
  const d = cursor.value
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
})

const monthLabel = computed(() =>
  cursor.value.toLocaleDateString(undefined, { month: 'long', year: 'numeric' }),
)

const byDate = computed(() => {
  const map: Record<string, CalendarSession[]> = {}
  for (const s of sessions.value) {
    const key = s.session_date
    if (!map[key]) map[key] = []
    map[key].push(s)
  }
  return map
})

const cells = computed(() => {
  const start = cursor.value
  const year = start.getFullYear()
  const month = start.getMonth()
  const firstDow = new Date(year, month, 1).getDay()
  const daysInMonth = new Date(year, month + 1, 0).getDate()
  const todayKey = isoDate(new Date())
  const out: {
    key: string
    day: number
    inMonth: boolean
    isToday: boolean
    sessions: CalendarSession[]
  }[] = []

  for (let i = 0; i < firstDow; i += 1) {
    const d = new Date(year, month, 1 - (firstDow - i))
    out.push({
      key: `lead-${isoDate(d)}`,
      day: d.getDate(),
      inMonth: false,
      isToday: false,
      sessions: [],
    })
  }
  for (let day = 1; day <= daysInMonth; day += 1) {
    const d = new Date(year, month, day)
    const key = isoDate(d)
    out.push({
      key,
      day,
      inMonth: true,
      isToday: key === todayKey,
      sessions: byDate.value[key] || [],
    })
  }
  while (out.length % 7 !== 0) {
    const d = new Date(year, month, daysInMonth + (out.length - firstDow - daysInMonth) + 1)
    out.push({
      key: `tail-${isoDate(d)}`,
      day: d.getDate(),
      inMonth: false,
      isToday: false,
      sessions: [],
    })
  }
  return out
})

function startOfMonth(d: Date) {
  return new Date(d.getFullYear(), d.getMonth(), 1)
}

function isoDate(d: Date) {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

function formatTime(t: string) {
  const [h, m] = (t || '00:00').split(':').map(Number)
  const period = h >= 12 ? 'PM' : 'AM'
  const hour12 = h % 12 === 0 ? 12 : h % 12
  return `${hour12}:${String(m).padStart(2, '0')} ${period}`
}

function shiftMonth(delta: number) {
  const d = cursor.value
  cursor.value = new Date(d.getFullYear(), d.getMonth() + delta, 1)
}

function select(session: CalendarSession) {
  emit('select', session)
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const resp = await staffFetch(`/api/staff/classes/upcoming/?month=${monthKey.value}`)
    if (!resp.ok) {
      error.value = 'Could not load the calendar.'
      return
    }
    const body = await resp.json()
    sessions.value = body.results || []
  } catch {
    error.value = 'No connection.'
  } finally {
    loading.value = false
  }
}

watch(monthKey, load)
onMounted(load)

defineExpose({ reload: load })
</script>
