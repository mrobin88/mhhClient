<template>
  <div
    class="checkin-shell min-h-[100dvh] min-w-full flex flex-col items-center justify-center px-4 py-10 sm:py-14 text-zinc-100 antialiased"
  >
    <!-- ambient grid + vignette -->
    <div class="checkin-shell__grid pointer-events-none fixed inset-0 -z-10" aria-hidden="true" />
    <div class="checkin-shell__vignette pointer-events-none fixed inset-0 -z-10" aria-hidden="true" />

    <div class="w-full max-w-[420px] mx-auto flex flex-col items-center">
      <!-- brand rail -->
      <header class="checkin-reveal text-center mb-8 sm:mb-10 w-full" style="animation-delay: 60ms">
        <p class="text-[10px] sm:text-xs font-semibold tracking-[0.35em] uppercase text-amber-500/90 mb-3">
          Visitor check-in
        </p>
        <h1 class="text-[1.65rem] sm:text-3xl font-bold tracking-tight text-zinc-50 leading-tight">
          Record your arrival
        </h1>
        <p class="mt-3 text-sm sm:text-[15px] text-zinc-400 leading-relaxed max-w-[34ch] mx-auto font-medium">
          Enter the phone number we have on file. Staff receives a time-stamped visit note.
        </p>
      </header>

      <article
        class="checkin-card w-full rounded-sm border border-zinc-600/70 bg-zinc-900/75 backdrop-blur-xl shadow-[0_24px_80px_-12px_rgba(0,0,0,0.65)] overflow-hidden checkin-reveal"
        style="animation-delay: 120ms"
      >
        <!-- caution accent (minimal, not playful) -->
        <div class="h-1 w-full bg-gradient-to-r from-amber-600 via-amber-400 to-amber-600" aria-hidden="true" />

        <div class="px-5 pt-5 pb-1 border-b border-zinc-700/60">
          <h2 class="text-[11px] font-bold tracking-[0.2em] uppercase text-zinc-500">{{ stepTitle }}</h2>
        </div>

        <div class="p-5 sm:p-6 min-h-[200px]">
          <Transition name="panel" mode="out-in">
            <div :key="step" class="space-y-5">
              <p
                v-if="message"
                class="text-sm rounded-sm px-3.5 py-2.5 border checkin-message"
                :class="messageClass"
                role="alert"
              >
                {{ message }}
              </p>

              <!-- PHONE -->
              <template v-if="step === 'phone'">
                <div class="space-y-3">
                  <label
                    for="phone"
                    class="block text-center text-[11px] font-semibold tracking-[0.22em] uppercase text-zinc-500"
                  >
                    Phone on file
                  </label>

                  <!-- well: inset, generous padding, industrial frame -->
                  <div
                    class="checkin-well rounded-sm border border-zinc-700/90 bg-zinc-950/70 p-1.5 shadow-[inset_0_1px_0_rgba(255,255,255,0.04),inset_0_-8px_24px_rgba(0,0,0,0.35)]"
                  >
                    <div class="px-4 py-7 sm:py-9 sm:px-6">
                      <input
                        id="phone"
                        v-model="phone"
                        type="tel"
                        inputmode="tel"
                        autocomplete="tel"
                        class="checkin-phone-input w-full bg-transparent border-0 text-center text-2xl sm:text-[1.75rem] font-semibold tracking-[0.08em] text-zinc-50 placeholder:text-zinc-600 focus:ring-0 focus:outline-none caret-amber-400"
                        placeholder="000 000 0000"
                        @keyup.enter="lookup"
                      />
                    </div>
                  </div>
                  <p class="text-center text-[11px] text-zinc-500 font-medium tracking-wide">
                    Digits only or formatted — both work
                  </p>
                </div>

                <button
                  type="button"
                  class="checkin-cta group relative w-full overflow-hidden rounded-sm py-4 px-4 font-bold uppercase tracking-[0.18em] text-xs sm:text-[13px] text-zinc-950 bg-amber-500 hover:bg-amber-400 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-amber-400/80 disabled:opacity-50 disabled:pointer-events-none transition-[transform,box-shadow,background-color] duration-200 ease-out hover:shadow-[0_0_0_1px_rgba(251,191,36,0.35),0_16px_40px_-8px_rgba(245,158,11,0.35)] active:translate-y-[1px]"
                  :disabled="loading"
                  @click="lookup"
                >
                  <span
                    v-if="loading"
                    class="inline-flex items-center justify-center gap-2"
                  >
                    <span class="checkin-spinner h-4 w-4 rounded-full border-2 border-zinc-950/30 border-t-zinc-950" aria-hidden="true" />
                    Locating profile
                  </span>
                  <span v-else>Continue</span>
                </button>
              </template>

              <!-- PICK -->
              <template v-else-if="step === 'pick'">
                <p class="text-sm text-zinc-400 text-center leading-relaxed font-medium">
                  Multiple profiles match this number. Select the name that is yours.
                </p>
                <ul class="space-y-2.5" role="listbox">
                  <li
                    v-for="(c, i) in clients"
                    :key="c.id"
                    class="checkin-stagger opacity-0"
                    :style="{ animationDelay: `${80 + i * 55}ms` }"
                  >
                    <button
                      type="button"
                      class="checkin-name-btn w-full text-left rounded-sm border border-zinc-700/80 bg-zinc-950/40 px-4 py-3.5 font-semibold text-zinc-100 tracking-tight transition-[border-color,background-color,transform,box-shadow] duration-200 ease-out hover:border-amber-500/50 hover:bg-zinc-800/60 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-amber-500/60 active:scale-[0.99]"
                      @click="selectClient(c)"
                    >
                      {{ c.first_name }} {{ c.last_name }}
                    </button>
                  </li>
                </ul>
                <button
                  type="button"
                  class="w-full text-center text-xs font-semibold uppercase tracking-[0.2em] text-zinc-500 hover:text-amber-500/90 transition-colors duration-200 py-2"
                  @click="resetFlow"
                >
                  Use different number
                </button>
              </template>

              <!-- REASON -->
              <template v-else-if="step === 'reason'">
                <p class="text-center text-lg sm:text-xl font-semibold text-zinc-100 tracking-tight">
                  Welcome back,
                  <span class="text-amber-400">{{ selectedName }}</span>
                </p>

                <label
                  for="reason"
                  class="block text-center text-[11px] font-semibold tracking-[0.22em] uppercase text-zinc-500"
                >
                  Reason for visit
                </label>
                <div
                  class="checkin-well rounded-sm border border-zinc-700/90 bg-zinc-950/70 p-1.5 shadow-[inset_0_1px_0_rgba(255,255,255,0.04),inset_0_-8px_24px_rgba(0,0,0,0.35)]"
                >
                  <textarea
                    id="reason"
                    v-model="visitReason"
                    rows="5"
                    class="checkin-textarea w-full resize-none bg-transparent border-0 rounded-sm px-4 py-4 text-[15px] sm:text-base text-zinc-200 placeholder:text-zinc-600 focus:ring-0 focus:outline-none leading-relaxed"
                    placeholder="State the purpose of your visit in clear terms."
                  />
                </div>

                <button
                  type="button"
                  class="checkin-cta group relative w-full overflow-hidden rounded-sm py-4 px-4 font-bold uppercase tracking-[0.18em] text-xs sm:text-[13px] text-zinc-950 bg-amber-500 hover:bg-amber-400 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-amber-400/80 disabled:opacity-45 disabled:pointer-events-none transition-[transform,box-shadow,background-color] duration-200 ease-out hover:shadow-[0_0_0_1px_rgba(251,191,36,0.35),0_16px_40px_-8px_rgba(245,158,11,0.35)] active:translate-y-[1px]"
                  :disabled="loading || !visitReason.trim()"
                  @click="submit"
                >
                  <span v-if="loading" class="inline-flex items-center justify-center gap-2">
                    <span class="checkin-spinner h-4 w-4 rounded-full border-2 border-zinc-950/30 border-t-zinc-950" aria-hidden="true" />
                    Submitting
                  </span>
                  <span v-else>Submit check-in</span>
                </button>
                <button
                  type="button"
                  class="w-full text-center text-xs font-semibold uppercase tracking-[0.2em] text-zinc-500 hover:text-amber-500/90 transition-colors duration-200 py-2"
                  @click="resetFlow"
                >
                  Start over
                </button>
              </template>

              <!-- DONE -->
              <template v-else-if="step === 'done'">
                <div class="text-center space-y-3 py-2">
                  <div
                    class="mx-auto flex h-12 w-12 items-center justify-center rounded-full border border-emerald-500/40 bg-emerald-950/50 checkin-success-ring"
                    aria-hidden="true"
                  >
                    <svg class="h-6 w-6 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                      <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7" />
                    </svg>
                  </div>
                  <p class="text-zinc-100 font-semibold text-base tracking-tight">Check-in recorded</p>
                  <p class="text-sm text-zinc-400 leading-relaxed">
                    Staff can review your visit note in the case file.
                  </p>
                  <p v-if="savedAt" class="text-xs font-medium uppercase tracking-[0.15em] text-zinc-500">
                    {{ savedAt }}
                  </p>
                </div>
                <button
                  type="button"
                  class="w-full rounded-sm border border-zinc-600 py-3.5 text-xs font-bold uppercase tracking-[0.18em] text-zinc-300 hover:border-zinc-500 hover:bg-zinc-800/40 transition-all duration-200"
                  @click="resetFlow"
                >
                  Check in again
                </button>
              </template>
            </div>
          </Transition>
        </div>
      </article>

      <p
        class="checkin-reveal mt-10 text-center text-[11px] sm:text-xs text-zinc-500 max-w-[36ch] leading-relaxed font-medium"
        style="animation-delay: 180ms"
      >
        New to services?
        <a
          href="/"
          class="text-amber-500/90 hover:text-amber-400 underline-offset-4 hover:underline transition-colors font-semibold"
        >
          Client registration
        </a>
        — this kiosk only adds a note for an existing profile.
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { getApiUrl } from '../config/api'

const DOC_BG = '#07080a'
onMounted(() => {
  document.documentElement.style.backgroundColor = DOC_BG
  document.body.style.backgroundColor = DOC_BG
})
onUnmounted(() => {
  document.documentElement.style.backgroundColor = ''
  document.body.style.backgroundColor = ''
})

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
  if (step.value === 'phone') return 'Identity'
  if (step.value === 'pick') return 'Confirmation'
  if (step.value === 'reason') return 'Visit log'
  return 'Complete'
})

const messageClass = computed(() =>
  messageKind.value === 'err'
    ? 'bg-red-950/50 text-red-200 border-red-800/60'
    : 'bg-emerald-950/40 text-emerald-100 border-emerald-800/50',
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

<style scoped>
.checkin-shell {
  background-color: #07080a;
  background-image:
    linear-gradient(180deg, rgba(9, 9, 11, 0.2) 0%, rgba(7, 8, 10, 0.92) 100%),
    linear-gradient(135deg, #0a0c0f 0%, #0c0e12 48%, #090b0d 100%);
}

.checkin-shell__grid {
  background-image:
    linear-gradient(rgba(255, 255, 255, 0.03) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255, 255, 255, 0.03) 1px, transparent 1px);
  background-size: 48px 48px;
  mask-image: radial-gradient(ellipse 85% 70% at 50% 38%, black 20%, transparent 72%);
  opacity: 0.55;
}

.checkin-shell__vignette {
  background: radial-gradient(ellipse 120% 80% at 50% 0%, rgba(245, 158, 11, 0.07), transparent 55%);
}

.checkin-card {
  box-shadow:
    0 0 0 1px rgba(255, 255, 255, 0.03) inset,
    0 24px 80px -12px rgba(0, 0, 0, 0.65);
}

.checkin-phone-input::placeholder {
  letter-spacing: 0.12em;
}

.checkin-textarea:focus,
.checkin-phone-input:focus {
  outline: none;
}

.checkin-well:focus-within {
  border-color: rgba(245, 158, 11, 0.45);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.05),
    inset 0 -8px 24px rgba(0, 0, 0, 0.35),
    0 0 0 1px rgba(245, 158, 11, 0.12),
    0 0 28px -8px rgba(245, 158, 11, 0.12);
  transition: border-color 220ms ease, box-shadow 220ms ease;
}

.checkin-well {
  transition: border-color 220ms ease, box-shadow 220ms ease;
}

.checkin-spinner {
  animation: checkin-spin 0.7s linear infinite;
}

.checkin-success-ring {
  animation: checkin-success-pulse 1.4s ease-out 1 both;
}

.checkin-reveal {
  animation: checkin-reveal-up 0.7s cubic-bezier(0.22, 1, 0.36, 1) both;
}

.checkin-stagger {
  animation: checkin-stagger-in 0.5s cubic-bezier(0.22, 1, 0.36, 1) forwards;
}

/* Step transitions */
.panel-enter-active,
.panel-leave-active {
  transition:
    opacity 0.28s cubic-bezier(0.22, 1, 0.36, 1),
    transform 0.32s cubic-bezier(0.22, 1, 0.36, 1);
}

.panel-enter-from {
  opacity: 0;
  transform: translateY(14px);
}

.panel-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}

@keyframes checkin-spin {
  to {
    transform: rotate(360deg);
  }
}

@keyframes checkin-reveal-up {
  from {
    opacity: 0;
    transform: translateY(18px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes checkin-stagger-in {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes checkin-success-pulse {
  0% {
    box-shadow: 0 0 0 0 rgba(52, 211, 153, 0.35);
  }
  70% {
    box-shadow: 0 0 0 14px rgba(52, 211, 153, 0);
  }
  100% {
    box-shadow: 0 0 0 0 rgba(52, 211, 153, 0);
  }
}

@media (prefers-reduced-motion: reduce) {
  .checkin-reveal,
  .checkin-stagger,
  .checkin-success-ring {
    animation: none !important;
    opacity: 1 !important;
    transform: none !important;
  }

  .checkin-spinner {
    animation: none;
    border-color: rgba(9, 9, 11, 0.5);
  }

  .panel-enter-active,
  .panel-leave-active {
    transition-duration: 0.01ms !important;
  }

  .checkin-cta {
    transition: none !important;
  }

  .checkin-name-btn {
    transition: none !important;
  }
}
</style>
