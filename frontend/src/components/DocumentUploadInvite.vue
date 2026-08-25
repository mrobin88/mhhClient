<template>
  <main class="upload-page">
    <section class="upload-card">
      <div class="upload-brand">Mission Hiring Hall</div>
      <h1>{{ pageTitle }}</h1>
      <p v-if="loading">Checking your link…</p>
      <div v-else-if="blockReason" class="upload-expired">
        <p class="upload-expired-lead">{{ blockMessage }}</p>
        <p v-if="expiredOn">This link ended on {{ expiredOn }}.</p>
        <p>
          Ask staff to send a new upload link, or bring copies when you come in.
          Do not email documents.
        </p>
        <p class="upload-note">
          If this was for City Build, staff will confirm which files are needed.
          That list is not on this page.
        </p>
        <p>
          Questions:
          <a href="mailto:info@missionhiringhall.org">info@missionhiringhall.org</a>
        </p>
      </div>
      <div v-else-if="error" class="upload-error">{{ error }}</div>
      <template v-else-if="invite">
        <p>Hi {{ invite.first_name }}. Upload only the documents requested below.</p>
        <p class="upload-note">Files are stored privately and this page cannot download your documents.</p>

        <form
          v-for="document in invite.documents"
          :key="document.value"
          class="upload-row"
          @submit.prevent="uploadDocument(document.value)"
        >
          <label :for="`file-${document.value}`">{{ document.label }}</label>
          <input
            :id="`file-${document.value}`"
            :ref="(element) => setFileInput(document.value, element)"
            type="file"
            accept=".jpg,.jpeg,.png,.webp,.heic,.heif,.pdf,.doc,.docx,.txt"
            required
            @change="(event) => onFileChosen(document.value, event)"
          />
          <p v-if="fileErrors[document.value]" class="upload-file-error">{{ fileErrors[document.value] }}</p>
          <button
            type="submit"
            :disabled="uploading === document.value || Boolean(fileErrors[document.value])"
          >
            {{ uploading === document.value ? 'Uploading…' : completed.has(document.value) ? 'Replace upload' : 'Upload' }}
          </button>
          <span v-if="completed.has(document.value)" class="upload-success">Uploaded successfully</span>
        </form>
        <p class="upload-expiry">This link expires {{ formatDate(invite.expires_at) }}.</p>
        <p class="upload-note">Staff can send a new link if this one expires.</p>
      </template>
    </section>
  </main>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { getApiUrl } from '../config/api'

interface InvitePayload {
  first_name: string
  documents: Array<{ value: string; label: string }>
  expires_at: string
  uploads_remaining: number
}

const ALLOWED_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.webp', '.heic', '.heif', '.pdf', '.doc', '.docx', '.txt']

const route = useRoute()
const invite = ref<InvitePayload | null>(null)
const loading = ref(true)
const error = ref('')
const blockReason = ref('')
const blockExpiresAt = ref('')
const uploading = ref('')
const completed = ref(new Set<string>())
const fileErrors = reactive<Record<string, string>>({})
const fileInputs = new Map<string, HTMLInputElement>()
const token = String(route.params.token || '')

function setFileInput(docType: string, element: unknown) {
  if (element instanceof HTMLInputElement) fileInputs.set(docType, element)
}

function formatDate(value: string) {
  return new Date(value).toLocaleDateString(undefined, { month: 'long', day: 'numeric', year: 'numeric' })
}

function fileExtension(name: string) {
  const parts = String(name || '').split('.')
  return parts.length > 1 ? `.${parts.pop()?.toLowerCase()}` : ''
}

const pageTitle = computed(() => {
  if (blockReason.value === 'expired') return 'This upload link expired'
  if (blockReason.value === 'revoked') return 'This upload link is no longer active'
  if (blockReason.value === 'used_up') return 'This upload link cannot take more files'
  if (blockReason.value) return 'This upload link is not available'
  return 'Secure document upload'
})

const blockMessage = computed(() => {
  if (blockReason.value === 'expired') {
    return 'The secure link you opened is past its expiration date, so files cannot be uploaded here.'
  }
  if (blockReason.value === 'revoked') {
    return 'Staff turned this link off. A new link can be sent if you still need to upload files.'
  }
  if (blockReason.value === 'used_up') {
    return 'This link has already received the maximum number of uploads.'
  }
  return 'This upload link is invalid or has expired.'
})

const expiredOn = computed(() => {
  if (blockReason.value !== 'expired' || !blockExpiresAt.value) return ''
  return formatDate(blockExpiresAt.value)
})

function onFileChosen(docType: string, event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) {
    delete fileErrors[docType]
    return
  }
  const extension = fileExtension(file.name)
  if (!ALLOWED_EXTENSIONS.includes(extension)) {
    fileErrors[docType] = 'Use a photo, PDF, Word, or text file.'
    input.value = ''
    return
  }
  delete fileErrors[docType]
}

async function loadInvite() {
  try {
    const response = await fetch(getApiUrl(`/api/document-upload/${encodeURIComponent(token)}/`))
    const body = await response.json().catch(() => null)
    if (!response.ok) {
      blockReason.value = body?.code || (response.status === 410 ? 'expired' : 'not_found')
      blockExpiresAt.value = body?.expires_at || ''
      if (response.status !== 410) {
        error.value = body?.detail || 'This upload link is invalid or has expired.'
        blockReason.value = ''
      }
      return
    }
    invite.value = body
  } catch {
    error.value = 'Could not connect. Check your internet connection and try again.'
  } finally {
    loading.value = false
  }
}

async function uploadDocument(docType: string) {
  const input = fileInputs.get(docType)
  const file = input?.files?.[0]
  if (!file || uploading.value) return
  uploading.value = docType
  error.value = ''
  const data = new FormData()
  data.append('doc_type', docType)
  data.append('file', file)
  try {
    const response = await fetch(getApiUrl(`/api/document-upload/${encodeURIComponent(token)}/`), {
      method: 'POST',
      body: data,
    })
    const body = await response.json().catch(() => null)
    if (response.status === 410) {
      blockReason.value = body?.code || 'expired'
      blockExpiresAt.value = body?.expires_at || ''
      invite.value = null
      return
    }
    if (!response.ok) {
      error.value = body?.detail || 'That document could not be uploaded.'
      return
    }
    completed.value = new Set([...completed.value, docType])
    if (input) input.value = ''
  } catch {
    error.value = 'The upload did not finish. Check your connection and try again.'
  } finally {
    uploading.value = ''
  }
}

onMounted(loadInvite)
</script>

<style scoped>
.upload-page { min-height: 100vh; padding: 2rem 1rem; background: #f5f5f4; color: #292524; }
.upload-card { width: min(42rem, 100%); margin: 0 auto; padding: 1.5rem; border: 1px solid #d6d3d1; border-radius: 1rem; background: white; box-shadow: 0 10px 30px rgb(28 25 23 / 8%); }
.upload-brand { color: #c2410c; font-weight: 800; text-transform: uppercase; letter-spacing: .08em; font-size: .8rem; }
h1 { margin: .5rem 0; font-size: 1.75rem; }
.upload-note, .upload-expiry { color: #78716c; font-size: .9rem; }
.upload-row { display: grid; gap: .6rem; margin-top: 1rem; padding: 1rem; border: 1px solid #e7e5e4; border-radius: .75rem; }
.upload-row label { font-weight: 700; }
.upload-row input { max-width: 100%; }
.upload-row button { border: 0; border-radius: .6rem; padding: .75rem 1rem; background: #ea580c; color: white; font-weight: 700; cursor: pointer; }
.upload-row button:disabled { opacity: .6; cursor: wait; }
.upload-success { color: #047857; font-size: .85rem; font-weight: 700; }
.upload-error { margin: 1rem 0; border-radius: .6rem; padding: .8rem; background: #fef2f2; color: #b91c1c; }
.upload-file-error { margin: 0; color: #b91c1c; font-size: .85rem; font-weight: 600; }
.upload-expired { margin-top: 1rem; display: grid; gap: .75rem; }
.upload-expired-lead { font-size: 1.05rem; font-weight: 600; }
.upload-expired a { color: #c2410c; font-weight: 700; }
</style>
