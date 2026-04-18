<template>
  <div class="min-h-screen bg-gradient py-10 px-4 text-slate-800">
    <div class="max-w-lg mx-auto">
      <header class="text-center mb-8">
        <h1 class="text-3xl font-bold text-mission-700">Check in</h1>
        <p class="text-slate-600 mt-2">
          Enter the phone number on your profile. We will save a time-stamped visit note for staff.
        </p>
      </header>

      <div class="form-card shadow-lg rounded-2xl overflow-hidden bg-white">
        <div class="bg-mission-600 text-white px-6 py-4">
          <h2 class="text-lg font-semibold">{{ stepTitle }}</h2>
        </div>

        <div class="p-6 space-y-4">
          <p v-if="message" class="text-sm rounded-lg px-3 py-2" :class="messageClass">{{ message }}</p>

          <template v-if="step === 'phone'">
            <label class="block text-sm font-medium text-slate-700" for="phone">Phone number</label>
            <input
              id="phone"
              v-model="phone"
              type="tel"
              autocomplete="tel"
              class="w-full border border-slate-300 rounded-lg px-4 py-3 text-lg"
              placeholder="(415) 555-0100"
              @keyup.enter="lookup"
            />
            <button
              type="button"
              class="w-full submit-button py-3 rounded-lg font-semibold text-white bg-mission-600 hover:bg-mission-700"
              :disabled="loading"
              @click="lookup"
            >
              {{ loading ? 'Looking up…' : 'Continue' }}
            </button>
          </template>

          <template v-else-if="step === 'pick'">
            <p class="text-slate-600 text-sm">Several profiles use this number. Tap yours:</p>
            <ul class="space-y-2">
              <li v-for="c in clients" :key="c.id">
                <button
                  type="button"
                  class="w-full text-left border border-slate-200 rounded-lg px-4 py-3 hover:border-mission-500 hover:bg-mission-50"
                  @click="selectClient(c)"
                >
                  <span class="font-medium">{{ c.first_name }} {{ c.last_name }}</span>
                </button>
              </li>
            </ul>
            <button type="button" class="text-sm text-mission-700 underline" @click="resetFlow">Different number</button>
          </template>

          <template v-else-if="step === 'reason'">
            <p class="text-lg text-slate-800">
              Welcome back, <span class="font-semibold text-mission-700">{{ selectedName }}</span>
            </p>
            <label class="block text-sm font-medium text-slate-700" for="reason">Reason for today’s visit</label>
            <textarea
              id="reason"
              v-model="visitReason"
              rows="5"
              class="w-full border border-slate-300 rounded-lg px-4 py-3"
              placeholder="Briefly describe why you came in today."
            />
            <button
              type="button"
              class="w-full submit-button py-3 rounded-lg font-semibold text-white bg-mission-600 hover:bg-mission-700"
              :disabled="loading || !visitReason.trim()"
              @click="submit"
            >
              {{ loading ? 'Saving…' : 'Submit check-in' }}
            </button>
            <button type="button" class="text-sm text-mission-700 underline" @click="resetFlow">Start over</button>
          </template>

          <template v-else-if="step === 'done'">
            <p class="text-green-800 font-medium">You’re checked in. Staff can see your note in the case file.</p>
            <p v-if="savedAt" class="text-sm text-slate-600">Recorded: {{ savedAt }}</p>
            <button
              type="button"
              class="w-full mt-4 py-3 rounded-lg font-semibold border border-slate-300 hover:bg-slate-50"
              @click="resetFlow"
            >
              Check in again
            </button>
          </template>
        </div>
      </div>

      <p class="text-center text-xs text-slate-500 mt-8 max-w-md mx-auto">
        New here?
        <a class="text-mission-700 underline font-medium" href="/">Use client registration</a>
        instead. This page only adds a visit note for an existing profile.
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { getApiUrl } from '../config/api'

type ClientRow = { id: number; first_name: string; last_name: string }

const step = ref<'phone' | 'pick' | 'reason' | 'done'>('phone')
const phone = ref('')
const clients = ref<ClientRow[]>([])
const selected = ref<ClientRow | null>(null)
const visitReason = ref('')
const loading = ref(false)
const message = ref('')
const messageKind = ref<'err' | 'ok'>('err')
const savedAt = ref('')

const API_LOOKUP = getApiUrl('/api/kiosk/check-in/lookup/')
const API_SUBMIT = getApiUrl('/api/kiosk/check-in/submit/')

const stepTitle = computed(() => {
  if (step.value === 'phone') return 'Find your profile'
  if (step.value === 'pick') return 'Confirm your name'
  if (step.value === 'reason') return 'Reason for visit'
  return 'Done'
})

const messageClass = computed(() =>
  messageKind.value === 'err' ? 'bg-red-50 text-red-800' : 'bg-green-50 text-green-800',
)

const selectedName = computed(() => {
  if (!selected.value) return ''
  return `${selected.value.first_name} ${selected.value.last_name}`.trim()
})

function clearMessage() {
  message.value = ''
}

async function lookup() {
  clearMessage()
  loading.value = true
  try {
    const res = await fetch(API_LOOKUP, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ phone: phone.value.trim() }),
    })
    const data = await res.json().catch(() => ({}))
    if (res.status === 404) {
      messageKind.value = 'err'
      message.value =
        typeof data.detail === 'string'
          ? data.detail
          : 'No profile for that number. Use registration on the home page first.'
      return
    }
    if (!res.ok) {
      messageKind.value = 'err'
      message.value = typeof data.detail === 'string' ? data.detail : 'Something went wrong. Try again.'
      return
    }
    const list: ClientRow[] = Array.isArray(data.clients) ? data.clients : []
    if (list.length === 0) {
      messageKind.value = 'err'
      message.value = 'No matching profile.'
      return
    }
    if (list.length === 1) {
      selectClient(list[0])
      return
    }
    clients.value = list
    step.value = 'pick'
  } finally {
    loading.value = false
  }
}

function selectClient(c: ClientRow) {
  selected.value = c
  visitReason.value = ''
  step.value = 'reason'
  clearMessage()
}

async function submit() {
  clearMessage()
  if (!selected.value) return
  loading.value = true
  try {
    const res = await fetch(API_SUBMIT, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        client_id: selected.value.id,
        phone: phone.value.trim(),
        visit_reason: visitReason.value.trim(),
      }),
    })
    const data = await res.json().catch(() => ({}))
    if (!res.ok) {
      messageKind.value = 'err'
      message.value = typeof data.detail === 'string' ? data.detail : 'Could not save. See staff for help.'
      return
    }
    savedAt.value =
      typeof data.case_note?.formatted_timestamp === 'string'
        ? data.case_note.formatted_timestamp
        : new Date().toLocaleString()
    step.value = 'done'
  } finally {
    loading.value = false
  }
}

function resetFlow() {
  step.value = 'phone'
  phone.value = ''
  clients.value = []
  selected.value = null
  visitReason.value = ''
  savedAt.value = ''
  clearMessage()
}
</script>
