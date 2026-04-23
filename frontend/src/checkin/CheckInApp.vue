<template>
  <div
    class="checkin-shell min-h-[100dvh] min-w-full flex flex-col items-center justify-center px-5 py-12 sm:px-8 sm:py-16 text-slate-800 antialiased"
  >
    <div class="checkin-shell__grid pointer-events-none fixed inset-0 -z-10" aria-hidden="true" />
    <div class="checkin-shell__wash pointer-events-none fixed inset-0 -z-10" aria-hidden="true" />

    <div class="w-full max-w-2xl mx-auto flex flex-col items-center">
      <header class="checkin-reveal text-center mb-10 sm:mb-12 w-full" style="animation-delay: 60ms">
        <p class="text-xs sm:text-sm font-semibold tracking-[0.28em] uppercase text-mission-700 mb-4">
          Visitor check-in
        </p>
        <h1 class="text-3xl sm:text-4xl lg:text-[2.75rem] font-bold tracking-tight text-slate-900 leading-tight">
          Record your arrival
        </h1>
        <p class="mt-4 text-base sm:text-lg text-slate-600 leading-relaxed max-w-xl mx-auto font-medium px-2">
          Enter the phone number we have on file. Your check-in is securely recorded.
        </p>
      </header>

      <article
        class="checkin-card w-full rounded-xl border border-slate-200/90 bg-white shadow-[0_4px_6px_-1px_rgba(0,0,0,0.06),0_20px_50px_-12px_rgba(15,118,110,0.12)] overflow-hidden checkin-reveal"
        style="animation-delay: 120ms"
      >
        <div class="h-1.5 w-full bg-gradient-to-r from-mission-600 via-mission-500 to-mission-600" aria-hidden="true" />

        <div class="px-6 sm:px-8 pt-6 pb-2 border-b border-slate-100 bg-slate-50/80">
          <h2 class="text-xs sm:text-sm font-bold tracking-[0.18em] uppercase text-slate-500">{{ stepTitle }}</h2>
        </div>

        <div class="p-6 sm:p-8 sm:pt-7 min-h-[240px] bg-white">
          <Transition name="panel" mode="out-in">
            <div :key="step" class="space-y-6 sm:space-y-7">
              <p
                v-if="message"
                class="text-base rounded-lg px-4 py-3 border"
                :class="messageClass"
                role="alert"
              >
                {{ message }}
              </p>

              <template v-if="step === 'phone'">
                <div class="space-y-4">
                  <label
                    for="phone"
                    class="block text-center text-xs sm:text-sm font-semibold tracking-[0.2em] uppercase text-slate-500"
                  >
                    Phone on file
                  </label>

                  <div
                    class="checkin-well rounded-xl border-2 border-slate-200 bg-slate-50 p-2 sm:p-2.5 shadow-[inset_0_1px_2px_rgba(255,255,255,0.9),inset_0_-2px_8px_rgba(15,23,42,0.04)]"
                  >
                    <div class="px-5 py-9 sm:py-11 sm:px-8 rounded-lg bg-white border border-slate-100">
                      <input
                        id="phone"
                        v-model="phone"
                        type="tel"
                        inputmode="tel"
                        autocomplete="tel"
                        class="checkin-phone-input w-full bg-transparent border-0 text-center text-3xl sm:text-4xl lg:text-[2.65rem] font-semibold tracking-[0.06em] text-slate-900 placeholder:text-slate-400 focus:ring-0 focus:outline-none caret-mission-600"
                        placeholder="000 000 0000"
                        @keyup.enter="lookup"
                      />
                    </div>
                  </div>
                  <p class="text-center text-sm text-slate-500 font-medium">
                    Digits only or formatted — both work
                  </p>
                </div>

                <button
                  type="button"
                  class="checkin-cta w-full rounded-xl py-4 sm:py-5 px-6 font-bold uppercase tracking-[0.16em] text-sm text-white bg-mission-600 hover:bg-mission-700 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-mission-600 disabled:opacity-50 disabled:pointer-events-none shadow-sm hover:shadow-md transition-[transform,box-shadow,background-color] duration-200 ease-out active:translate-y-px"
                  :disabled="loading"
                  @click="lookup"
                >
                  <span v-if="loading" class="inline-flex items-center justify-center gap-3">
                    <span
                      class="checkin-spinner h-5 w-5 rounded-full border-2 border-white/35 border-t-white"
                      aria-hidden="true"
                    />
                    Locating profile
                  </span>
                  <span v-else>Continue</span>
                </button>
              </template>

              <template v-else-if="step === 'pick'">
                <p class="text-base sm:text-lg text-slate-600 text-center leading-relaxed font-medium">
                  Multiple profiles match this number. Select the name that is yours.
                </p>
                <ul class="space-y-3" role="listbox">
                  <li
                    v-for="(c, i) in clients"
                    :key="c.id"
                    class="checkin-stagger opacity-0"
                    :style="{ animationDelay: `${80 + i * 55}ms` }"
                  >
                    <button
                      type="button"
                      class="checkin-name-btn w-full text-left rounded-xl border-2 border-slate-200 bg-slate-50 px-5 py-4 sm:py-5 text-lg font-semibold text-slate-900 tracking-tight transition-[border-color,background-color,transform,box-shadow] duration-200 ease-out hover:border-mission-400 hover:bg-white hover:shadow-md focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-mission-600 active:scale-[0.998]"
                      @click="selectClient(c)"
                    >
                      {{ c.first_name }} {{ c.last_name }}
                    </button>
                  </li>
                </ul>
                <button
                  type="button"
                  class="w-full text-center text-sm font-semibold uppercase tracking-[0.15em] text-slate-500 hover:text-mission-700 transition-colors duration-200 py-2"
                  @click="resetFlow"
                >
                  Use different number
                </button>
              </template>

              <template v-else-if="step === 'reason'">
                <p class="text-center text-xl sm:text-2xl font-semibold text-slate-900 tracking-tight">
                  Welcome back,
                  <span class="text-mission-700">{{ selectedName }}</span>
                </p>

                <label
                  for="reason"
                  class="block text-center text-xs sm:text-sm font-semibold tracking-[0.2em] uppercase text-slate-500"
                >
                  Reason for visit
                </label>
                <div
                  class="checkin-well rounded-xl border-2 border-slate-200 bg-slate-50 p-2 sm:p-2.5 shadow-[inset_0_1px_2px_rgba(255,255,255,0.9),inset_0_-2px_8px_rgba(15,23,42,0.04)]"
                >
                  <textarea
                    id="reason"
                    v-model="visitReason"
                    rows="6"
                    class="checkin-textarea w-full resize-none bg-white border border-slate-100 rounded-lg px-5 py-5 text-base sm:text-lg text-slate-800 placeholder:text-slate-400 focus:ring-0 focus:outline-none leading-relaxed min-h-[160px]"
                    placeholder="State the purpose of your visit in clear terms."
                  />
                </div>

                <button
                  type="button"
                  class="checkin-cta w-full rounded-xl py-4 sm:py-5 px-6 font-bold uppercase tracking-[0.16em] text-sm text-white bg-mission-600 hover:bg-mission-700 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-mission-600 disabled:opacity-45 disabled:pointer-events-none shadow-sm hover:shadow-md transition-[transform,box-shadow,background-color] duration-200 ease-out active:translate-y-px"
                  :disabled="loading || !visitReason.trim()"
                  @click="submitCheckIn"
                >
                  <span v-if="loading" class="inline-flex items-center justify-center gap-3">
                    <span
                      class="checkin-spinner h-5 w-5 rounded-full border-2 border-white/35 border-t-white"
                      aria-hidden="true"
                    />
                    Submitting
                  </span>
                  <span v-else>Submit check-in</span>
                </button>
                <button
                  type="button"
                  class="w-full text-center text-sm font-semibold uppercase tracking-[0.15em] text-slate-500 hover:text-mission-700 transition-colors duration-200 py-2"
                  @click="resetFlow"
                >
                  Start over
                </button>
              </template>

              <template v-else-if="step === 'uploadPrompt'">
                <div class="text-center space-y-4 py-2">
                  <p class="text-slate-900 font-semibold text-xl tracking-tight">Check-in recorded</p>
                  <p class="text-base text-slate-600 leading-relaxed max-w-md mx-auto">
                    Would you like to upload a document now?
                  </p>
                  <p class="text-sm text-slate-500">You can skip this and do it later with staff.</p>
                </div>
                <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <button
                    type="button"
                    class="w-full rounded-xl py-4 px-6 font-bold uppercase tracking-[0.14em] text-sm text-white bg-mission-600 hover:bg-mission-700 disabled:opacity-50"
                    :disabled="loading"
                    @click="goToUpload"
                  >
                    Yes, upload now
                  </button>
                  <button
                    type="button"
                    class="w-full rounded-xl border-2 border-slate-200 py-4 px-6 font-bold uppercase tracking-[0.14em] text-sm text-slate-700 hover:border-slate-300 hover:bg-slate-50"
                    :disabled="loading"
                    @click="finishCheckIn"
                  >
                    No, finish
                  </button>
                </div>
              </template>

              <template v-else-if="step === 'upload'">
                <p class="text-center text-xl sm:text-2xl font-semibold text-slate-900 tracking-tight">
                  Upload document
                </p>
                <div class="space-y-4">
                  <div>
                    <label for="docType" class="block text-sm font-semibold text-slate-700 mb-2">Document type</label>
                    <select
                      id="docType"
                      v-model="uploadDocType"
                      class="w-full rounded-lg border border-slate-300 px-4 py-3 text-slate-800"
                    >
                      <option v-for="opt in docTypeOptions" :key="opt.value" :value="opt.value">
                        {{ opt.label }}
                      </option>
                    </select>
                  </div>

                  <div>
                    <label for="docTitle" class="block text-sm font-semibold text-slate-700 mb-2">Document title</label>
                    <input
                      id="docTitle"
                      v-model="uploadTitle"
                      type="text"
                      class="w-full rounded-lg border border-slate-300 px-4 py-3 text-slate-800"
                      placeholder="Example: Driver License, Resume, Diploma"
                    />
                  </div>

                  <div>
                    <label for="docFile" class="block text-sm font-semibold text-slate-700 mb-2">Choose file</label>
                    <input
                      id="docFile"
                      type="file"
                      class="w-full rounded-lg border border-slate-300 px-4 py-3 text-slate-700 bg-white"
                      @change="onFileChange"
                    />
                    <p class="mt-2 text-xs text-slate-500">Accepted by device: PDF, image, Word, or related file types.</p>
                  </div>

                  <div>
                    <label for="docNotes" class="block text-sm font-semibold text-slate-700 mb-2">Notes (optional)</label>
                    <textarea
                      id="docNotes"
                      v-model="uploadNotes"
                      rows="3"
                      class="w-full rounded-lg border border-slate-300 px-4 py-3 text-slate-800"
                      placeholder="Optional notes about this document."
                    />
                  </div>
                </div>

                <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <button
                    type="button"
                    class="w-full rounded-xl py-4 px-6 font-bold uppercase tracking-[0.14em] text-sm text-white bg-mission-600 hover:bg-mission-700 disabled:opacity-45"
                    :disabled="loading || !uploadFile"
                    @click="submitUpload"
                  >
                    <span v-if="loading">Uploading</span>
                    <span v-else>Upload document</span>
                  </button>
                  <button
                    type="button"
                    class="w-full rounded-xl border-2 border-slate-200 py-4 px-6 font-bold uppercase tracking-[0.14em] text-sm text-slate-700 hover:border-slate-300 hover:bg-slate-50"
                    :disabled="loading"
                    @click="finishCheckIn"
                  >
                    Finish check-in
                  </button>
                </div>

                <p v-if="uploadedCount > 0" class="text-center text-sm text-emerald-700 font-medium">
                  {{ uploadedCount }} document{{ uploadedCount > 1 ? 's' : '' }} uploaded successfully.
                </p>
              </template>

              <template v-else-if="step === 'done'">
                <div class="text-center space-y-4 py-3">
                  <div
                    class="mx-auto flex h-14 w-14 items-center justify-center rounded-full border-2 border-emerald-200 bg-emerald-50 checkin-success-ring"
                    aria-hidden="true"
                  >
                    <svg class="h-8 w-8 text-emerald-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                      <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7" />
                    </svg>
                  </div>
                  <p class="text-slate-900 font-semibold text-xl tracking-tight">All set</p>
                  <p class="text-base text-slate-600 leading-relaxed max-w-md mx-auto">
                    Thank you. Your information has been received.
                  </p>
                  <p v-if="savedAt" class="text-sm font-semibold uppercase tracking-[0.12em] text-slate-500">
                    {{ savedAt }}
                  </p>
                </div>
                <button
                  type="button"
                  class="w-full rounded-xl border-2 border-slate-200 py-4 text-sm font-bold uppercase tracking-[0.14em] text-slate-700 hover:border-slate-300 hover:bg-slate-50 transition-all duration-200"
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
        class="checkin-reveal mt-12 text-center text-sm sm:text-base text-slate-600 max-w-lg leading-relaxed font-medium px-2"
        style="animation-delay: 180ms"
      >
        New to services?
        <RouterLink
          to="/"
          class="text-mission-700 hover:text-mission-800 font-semibold underline underline-offset-4 decoration-mission-300 hover:decoration-mission-600 transition-colors"
        >
          Client registration
        </RouterLink>
        — this kiosk is for returning clients.
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { getApiUrl } from '../config/api'

type ClientRow = { id: number; first_name: string; last_name: string }
type Step = 'phone' | 'pick' | 'reason' | 'uploadPrompt' | 'upload' | 'done'

const step = ref<Step>('phone')
const phone = ref('')
const clients = ref<ClientRow[]>([])
const selected = ref<ClientRow | null>(null)
const visitReason = ref('')
const loading = ref(false)
const message = ref('')
const messageKind = ref<'err' | 'ok'>('err')
const savedAt = ref('')

const uploadDocType = ref('other')
const uploadTitle = ref('')
const uploadNotes = ref('')
const uploadFile = ref<File | null>(null)
const uploadedCount = ref(0)

const docTypeOptions = [
  { value: 'resume', label: 'Resume' },
  { value: 'sf_residency', label: 'Proof of SF Residency' },
  { value: 'hs_diploma', label: 'High School Diploma / GED' },
  { value: 'id', label: 'Government ID' },
  { value: 'photo_release', label: 'Photo Release Form' },
  { value: 'intake', label: 'Intake Form' },
  { value: 'consent', label: 'Consent Form' },
  { value: 'certificate', label: 'Certificate / Credential' },
  { value: 'reference', label: 'Reference Letter' },
  { value: 'other', label: 'Other' },
]

const API_LOOKUP = getApiUrl('/api/kiosk/check-in/lookup/')
const API_SUBMIT = getApiUrl('/api/kiosk/check-in/submit/')
const API_UPLOAD_DOC = getApiUrl('/api/kiosk/check-in/upload-document/')

const stepTitle = computed(() => {
  if (step.value === 'phone') return 'Identity'
  if (step.value === 'pick') return 'Confirmation'
  if (step.value === 'reason') return 'Visit log'
  if (step.value === 'uploadPrompt') return 'Optional documents'
  if (step.value === 'upload') return 'Document upload'
  return 'Complete'
})

const messageClass = computed(() =>
  messageKind.value === 'err'
    ? 'bg-red-50 text-red-900 border-red-200'
    : 'bg-emerald-50 text-emerald-900 border-emerald-200',
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

async function submitCheckIn() {
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
    step.value = 'uploadPrompt'
    uploadTitle.value = ''
    uploadNotes.value = ''
    uploadDocType.value = 'other'
    uploadFile.value = null
    uploadedCount.value = 0
  } finally {
    loading.value = false
  }
}

function goToUpload() {
  clearMessage()
  step.value = 'upload'
}

function onFileChange(event: Event) {
  const input = event.target as HTMLInputElement | null
  uploadFile.value = input?.files?.[0] ?? null
}

async function submitUpload() {
  clearMessage()
  if (!selected.value || !uploadFile.value) return

  loading.value = true
  try {
    const body = new FormData()
    body.append('client_id', String(selected.value.id))
    body.append('phone', phone.value.trim())
    body.append('doc_type', uploadDocType.value)
    body.append('title', uploadTitle.value.trim())
    body.append('notes', uploadNotes.value.trim())
    body.append('file', uploadFile.value)

    const res = await fetch(API_UPLOAD_DOC, {
      method: 'POST',
      body,
    })
    const data = await res.json().catch(() => ({}))
    if (!res.ok) {
      messageKind.value = 'err'
      message.value = typeof data.detail === 'string' ? data.detail : 'Upload failed. Please try again.'
      return
    }

    uploadedCount.value += 1
    uploadFile.value = null
    uploadTitle.value = ''
    uploadNotes.value = ''
    messageKind.value = 'ok'
    message.value = 'Document uploaded successfully.'
  } finally {
    loading.value = false
  }
}

function finishCheckIn() {
  clearMessage()
  step.value = 'done'
}

function resetFlow() {
  step.value = 'phone'
  phone.value = ''
  clients.value = []
  selected.value = null
  visitReason.value = ''
  savedAt.value = ''
  uploadDocType.value = 'other'
  uploadTitle.value = ''
  uploadNotes.value = ''
  uploadFile.value = null
  uploadedCount.value = 0
  clearMessage()
}
</script>

<style scoped>
.checkin-shell {
  background: linear-gradient(to bottom right, #f0fdfa, #e2f8f4, #ccfbf1);
}

.checkin-shell__grid {
  background-image:
    linear-gradient(rgba(15, 118, 110, 0.06) 1px, transparent 1px),
    linear-gradient(90deg, rgba(15, 118, 110, 0.06) 1px, transparent 1px);
  background-size: 48px 48px;
  mask-image: radial-gradient(ellipse 95% 80% at 50% 20%, black 15%, transparent 65%);
  opacity: 0.5;
}

.checkin-shell__wash {
  background: radial-gradient(ellipse 120% 70% at 50% 0%, rgba(255, 255, 255, 0.75), transparent 55%);
}

.checkin-card {
  box-shadow:
    0 0 0 1px rgba(255, 255, 255, 0.8) inset,
    0 20px 50px -12px rgba(15, 118, 110, 0.15);
}

.checkin-phone-input::placeholder {
  letter-spacing: 0.08em;
}

.checkin-textarea:focus,
.checkin-phone-input:focus {
  outline: none;
}

.checkin-well:focus-within {
  border-color: rgba(13, 148, 136, 0.45);
  box-shadow:
    inset 0 1px 2px rgba(255, 255, 255, 0.95),
    0 0 0 3px rgba(13, 148, 136, 0.12);
  transition: border-color 200ms ease, box-shadow 200ms ease;
}

.checkin-well {
  transition: border-color 200ms ease, box-shadow 200ms ease;
}

.checkin-spinner {
  animation: checkin-spin 0.7s linear infinite;
}

.checkin-success-ring {
  animation: checkin-success-pulse 1.35s ease-out 1 both;
}

.checkin-reveal {
  animation: checkin-reveal-up 0.65s cubic-bezier(0.22, 1, 0.36, 1) both;
}

.checkin-stagger {
  animation: checkin-stagger-in 0.48s cubic-bezier(0.22, 1, 0.36, 1) forwards;
}

.panel-enter-active,
.panel-leave-active {
  transition:
    opacity 0.26s cubic-bezier(0.22, 1, 0.36, 1),
    transform 0.3s cubic-bezier(0.22, 1, 0.36, 1);
}

.panel-enter-from {
  opacity: 0;
  transform: translateY(12px);
}

.panel-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}

@keyframes checkin-spin {
  to {
    transform: rotate(360deg);
  }
}

@keyframes checkin-reveal-up {
  from {
    opacity: 0;
    transform: translateY(16px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes checkin-stagger-in {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes checkin-success-pulse {
  0% {
    box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.35);
  }
  70% {
    box-shadow: 0 0 0 14px rgba(16, 185, 129, 0);
  }
  100% {
    box-shadow: 0 0 0 0 rgba(16, 185, 129, 0);
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
    border-color: rgba(255, 255, 255, 0.45);
    border-top-color: white;
  }

  .panel-enter-active,
  .panel-leave-active {
    transition-duration: 0.01ms !important;
  }

  .checkin-cta,
  .checkin-name-btn {
    transition: none !important;
  }
}
</style>
