<template>
  <div class="checkin-page">
    <div class="checkin-page__inner">
      <header class="checkin-header">
        <p class="checkin-brand">Mission Hiring Hall</p>
        <h1>{{ heading }}</h1>
        <p class="checkin-lede">{{ lede }}</p>
      </header>

      <article class="checkin-card">
        <p v-if="message" class="checkin-alert" :class="messageKind === 'err' ? 'is-err' : 'is-ok'" role="alert">
          {{ message }}
        </p>

        <div class="checkin-step">
          <template v-if="step === 'phone'">
            <label for="phone">Phone</label>
            <input
              id="phone"
              v-model="phone"
              type="tel"
              inputmode="tel"
              autocomplete="tel"
              enterkeyhint="go"
              class="checkin-input checkin-input-phone"
              placeholder="415 555 0123"
              @keyup.enter="lookup"
            />
            <button type="button" class="checkin-btn checkin-btn-primary" :disabled="loading" @click="lookup">
              <span v-if="loading" class="checkin-spinner" aria-hidden="true" />
              {{ loading ? 'Looking you up…' : 'Continue' }}
            </button>
          </template>

          <template v-else-if="step === 'pick'">
            <ul class="checkin-names" role="listbox">
              <li v-for="c in clients" :key="c.id">
                <button type="button" class="checkin-name" @click="selectClient(c)">
                  {{ c.first_name }} {{ c.last_name }}
                </button>
              </li>
            </ul>
            <button type="button" class="checkin-btn checkin-btn-ghost" @click="resetFlow">
              Use a different number
            </button>
          </template>

          <template v-else-if="step === 'reason'">
            <label for="reason">Why are you here?</label>
            <textarea
              id="reason"
              v-model="visitReason"
              rows="3"
              class="checkin-input checkin-textarea"
              placeholder="Class, paperwork, or something else"
            />
            <button
              type="button"
              class="checkin-btn checkin-btn-primary"
              :disabled="loading || !visitReason.trim()"
              @click="submitCheckIn"
            >
              <span v-if="loading" class="checkin-spinner" aria-hidden="true" />
              {{ loading ? 'Saving…' : 'Check in' }}
            </button>
            <button type="button" class="checkin-btn checkin-btn-ghost" @click="resetFlow">
              Start over
            </button>
          </template>

          <template v-else-if="step === 'uploadPrompt'">
            <p class="checkin-prompt">Upload a photo ID now?</p>
            <p class="checkin-hint">You can skip this and bring it later.</p>
            <div class="checkin-actions">
              <button type="button" class="checkin-btn checkin-btn-primary" :disabled="loading" @click="goToUpload">
                Yes, upload
              </button>
              <button type="button" class="checkin-btn checkin-btn-secondary" :disabled="loading" @click="finishCheckIn">
                Not now
              </button>
            </div>
          </template>

          <template v-else-if="step === 'upload'">
            <div class="checkin-field">
              <label for="docTitle">Document title</label>
              <input
                id="docTitle"
                v-model="uploadTitle"
                type="text"
                class="checkin-input"
                placeholder="Driver license"
              />
            </div>

            <div class="checkin-field">
              <label for="docFile">Photo or PDF</label>
              <input
                id="docFile"
                ref="docFileInput"
                type="file"
                accept="image/*,application/pdf"
                class="checkin-input checkin-file"
                @click="onFilePickerOpen"
                @change="onFileChange"
              />
              <p v-if="filePicking" class="checkin-status" role="status">Opening files…</p>
              <div v-if="uploadFile" class="checkin-staged">
                <div>
                  <p class="checkin-staged-name">{{ uploadFile.name }}</p>
                  <p class="checkin-hint">{{ formatFileSize(uploadFile.size) }}</p>
                </div>
                <button type="button" class="checkin-remove" @click="removeUploadFile">Remove</button>
              </div>
            </div>

            <div class="checkin-field">
              <label for="docNotes">Notes (optional)</label>
              <textarea
                id="docNotes"
                v-model="uploadNotes"
                rows="2"
                class="checkin-input checkin-textarea"
                placeholder="Anything staff should know"
              />
            </div>

            <div class="checkin-actions">
              <button
                type="button"
                class="checkin-btn checkin-btn-primary"
                :disabled="loading || !uploadFile"
                @click="submitUpload"
              >
                <span v-if="loading" class="checkin-spinner" aria-hidden="true" />
                {{ loading ? 'Uploading…' : 'Upload' }}
              </button>
              <button type="button" class="checkin-btn checkin-btn-secondary" :disabled="loading" @click="finishCheckIn">
                Finish
              </button>
            </div>
            <p v-if="uploadedCount > 0" class="checkin-ok">
              {{ uploadedCount }} document{{ uploadedCount > 1 ? 's' : '' }} uploaded.
            </p>
          </template>

          <template v-else-if="step === 'done'">
            <p class="checkin-prompt">You’re checked in.</p>
            <p v-if="savedAt" class="checkin-hint">{{ savedAt }}</p>
            <button type="button" class="checkin-btn checkin-btn-secondary" @click="resetFlow">
              Check in someone else
            </button>
          </template>
        </div>
      </article>

      <p class="checkin-foot">
        <a href="/">Home</a>
        <span aria-hidden="true">·</span>
        New here?
        <a href="/signup">Sign up</a>
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
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

const uploadTitle = ref('')
const uploadNotes = ref('')
const uploadFile = ref<File | null>(null)
const uploadedCount = ref(0)
const filePicking = ref(false)
const docFileInput = ref<HTMLInputElement | null>(null)

const API_LOOKUP = getApiUrl('/api/kiosk/check-in/lookup/')
const API_SUBMIT = getApiUrl('/api/kiosk/check-in/submit/')
const API_UPLOAD_DOC = getApiUrl('/api/kiosk/check-in/upload-document/')

const heading = computed(() => {
  if (step.value === 'pick') return 'Which name?'
  if (step.value === 'reason') return selectedName.value ? `Hi, ${selectedName.value}` : 'Check in'
  if (step.value === 'uploadPrompt') return 'You’re in'
  if (step.value === 'upload') return 'Photo ID'
  if (step.value === 'done') return 'All set'
  return 'Check in'
})

const lede = computed(() => {
  if (step.value === 'phone') return 'Use the phone number we have on file.'
  if (step.value === 'pick') return 'More than one person uses this number.'
  if (step.value === 'reason') return 'Tell us why you came in today.'
  if (step.value === 'uploadPrompt') return 'Your visit is recorded.'
  if (step.value === 'upload') return 'A photo of your ID is enough.'
  return 'Staff has your check-in.'
})

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
          : 'No profile for that number. Sign up from the home page first.'
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
    uploadTitle.value = 'Government Photo ID'
    uploadNotes.value = ''
    uploadFile.value = null
    uploadedCount.value = 0
  } finally {
    loading.value = false
  }
}

function goToUpload() {
  clearMessage()
  filePicking.value = false
  step.value = 'upload'
}

function formatFileSize(bytes: number) {
  if (!bytes) return 'Selected'
  if (bytes < 1024) return `${bytes} bytes`
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function onFilePickerOpen() {
  filePicking.value = true
}

function stageChosenFile(file: File | null | undefined) {
  filePicking.value = false
  if (!file) return
  uploadFile.value = file
  clearMessage()
}

function onFileChange(event: Event) {
  const input = event.target as HTMLInputElement | null
  stageChosenFile(input?.files?.[0])
}

function harvestPickedFile() {
  const file = docFileInput.value?.files?.[0]
  if (file && file !== uploadFile.value) stageChosenFile(file)
  else filePicking.value = false
}

// Clear a staged file before upload so a wrong or too-big pick can be swapped out.
function removeUploadFile() {
  uploadFile.value = null
  filePicking.value = false
  if (docFileInput.value) docFileInput.value.value = ''
  clearMessage()
}

async function submitUpload() {
  clearMessage()
  if (!selected.value || !uploadFile.value) return

  loading.value = true
  try {
    const body = new FormData()
    body.append('client_id', String(selected.value.id))
    body.append('phone', phone.value.trim())
    body.append('doc_type', 'id')
    body.append('title', (uploadTitle.value || 'Government Photo ID').trim())
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
    filePicking.value = false
    uploadTitle.value = 'Government Photo ID'
    uploadNotes.value = ''
    if (docFileInput.value) docFileInput.value.value = ''
    messageKind.value = 'ok'
    message.value = 'Government Photo ID uploaded successfully.'
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
  uploadTitle.value = 'Government Photo ID'
  uploadNotes.value = ''
  uploadFile.value = null
  filePicking.value = false
  uploadedCount.value = 0
  if (docFileInput.value) docFileInput.value.value = ''
  clearMessage()
}

onMounted(() => {
  window.addEventListener('focus', harvestPickedFile)
  document.addEventListener('visibilitychange', harvestPickedFile)
})

onBeforeUnmount(() => {
  window.removeEventListener('focus', harvestPickedFile)
  document.removeEventListener('visibilitychange', harvestPickedFile)
})
</script>

<style scoped>
.checkin-page {
  min-height: 100dvh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1.25rem 1rem 1.75rem;
  font-family: system-ui, -apple-system, 'Segoe UI', sans-serif;
  font-size: 16px;
  line-height: 1.4;
  color: #1c1917;
  background: #f3f4f1;
  -webkit-text-size-adjust: 100%;
  touch-action: manipulation;
}

.checkin-page__inner {
  width: 100%;
  max-width: 22.5rem;
  min-width: 0;
}

.checkin-header {
  margin-bottom: 1rem;
}

.checkin-brand {
  margin: 0 0 0.2rem;
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: #0f766e;
}

.checkin-header h1 {
  margin: 0;
  font-size: 1.65rem;
    font-weight: 700;
  letter-spacing: -0.03em;
  line-height: 1.15;
  color: #134e4a;
}

.checkin-lede {
  margin: 0.3rem 0 0;
  color: #57534e;
}

.checkin-card {
  background: #fff;
  border: 1px solid #e4e4e0;
  border-radius: 0.85rem;
  padding: 1.1rem 1rem 1.2rem;
  overflow: hidden;
}

.checkin-step,
.checkin-field,
.checkin-actions {
  display: flex;
  flex-direction: column;
  gap: 0.7rem;
}

.checkin-step label {
  font-size: 0.88rem;
  font-weight: 700;
  color: #292524;
}

.checkin-input,
.checkin-btn,
.checkin-name {
  box-sizing: border-box;
  display: block;
  width: 100%;
  max-width: 100%;
  min-height: 3rem;
  padding: 0.7rem 0.85rem;
  border-radius: 0.65rem;
  font: inherit;
}

.checkin-input {
  border: 1px solid #d6d3d1;
  background: #fff;
  color: #1c1917;
}

.checkin-input:focus,
.checkin-textarea:focus {
  outline: 2px solid #0d9488;
  outline-offset: 1px;
  border-color: #0d9488;
}

.checkin-input-phone {
  min-height: 3.4rem;
  text-align: center;
  font-size: 1.25rem;
  font-weight: 700;
  letter-spacing: 0.03em;
}

.checkin-textarea {
  min-height: 5.5rem;
  resize: none;
}

.checkin-file {
  padding: 0.45rem;
}

.checkin-hint {
  margin: 0;
  font-size: 0.85rem;
  color: #78716c;
}

.checkin-alert {
  margin: 0 0 0.75rem;
  padding: 0.7rem 0.8rem;
  border-radius: 0.6rem;
  font-size: 0.92rem;
}

.checkin-alert.is-err {
  background: #fef2f2;
  color: #991b1b;
}

.checkin-alert.is-ok {
  background: #ecfdf5;
  color: #065f46;
}

.checkin-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.45rem;
  font-weight: 700;
  border: 1px solid transparent;
  cursor: pointer;
  -webkit-tap-highlight-color: transparent;
}

.checkin-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.checkin-btn-primary {
  background: #0d9488;
  color: #fff;
}

.checkin-btn-primary:not(:disabled):active {
  background: #0f766e;
}

.checkin-btn-secondary {
  background: #fff;
  color: #1c1917;
  border-color: #d6d3d1;
}

.checkin-btn-ghost {
  background: transparent;
  color: #57534e;
  min-height: 2.4rem;
  font-size: 0.92rem;
}

.checkin-names {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
}

.checkin-name {
  text-align: left;
  border: 1px solid #d6d3d1;
  background: #fff;
  font-weight: 700;
  color: #1c1917;
  cursor: pointer;
}

.checkin-name:focus-visible {
  outline: 2px solid #0d9488;
  outline-offset: 1px;
}

.checkin-prompt {
  margin: 0;
  font-size: 1.05rem;
  font-weight: 700;
}

.checkin-status {
  margin: 0;
  color: #155e75;
  font-size: 0.88rem;
  font-weight: 600;
}

.checkin-staged {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.7rem;
  padding: 0.65rem 0.75rem;
  border-radius: 0.65rem;
  background: #ecfdf5;
}

.checkin-staged-name {
  margin: 0;
  font-weight: 700;
  word-break: break-word;
}

.checkin-remove {
  flex-shrink: 0;
  border: 0;
  background: #fff;
  color: #b91c1c;
  font-size: 0.8rem;
  font-weight: 700;
  padding: 0.35rem 0.6rem;
  border-radius: 0.45rem;
  cursor: pointer;
}

.checkin-ok {
  margin: 0;
  text-align: center;
  color: #047857;
  font-weight: 600;
  font-size: 0.88rem;
}

.checkin-foot {
  margin: 1rem 0 0;
  text-align: center;
  font-size: 0.9rem;
  color: #57534e;
}

.checkin-foot a {
  color: #0f766e;
  font-weight: 700;
}

.checkin-foot span {
  margin: 0 0.35rem;
  color: #a8a29e;
}

.checkin-spinner {
  width: 1rem;
  height: 1rem;
  border-radius: 999px;
  border: 2px solid rgba(255, 255, 255, 0.35);
  border-top-color: #fff;
  animation: checkin-spin 0.8s linear infinite;
}

@keyframes checkin-spin {
  to {
    transform: rotate(360deg);
  }
}

@media (prefers-reduced-motion: reduce) {
  .checkin-spinner {
    animation: none;
    border-top-color: #fff;
  }
}
</style>
