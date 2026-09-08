<template>
  <main class="upload-page">
    <section class="upload-card">
      <div class="upload-brand">Mission Hiring Hall</div>
      <h1>{{ pageTitle }}</h1>
      <p v-if="loading">Checking your link…</p>
      <div v-else-if="blockReason" class="upload-expired">
        <p class="upload-expired-lead">{{ blockMessage }}</p>
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
        <p class="upload-help">
          Use the file box below. On this phone, pick Camera, Gallery, or Files.
          If nothing opens, this page is still inside the text-message app — open the same
          link in Chrome, or bring copies when you come in.
        </p>

        <div ref="pageRoot" class="upload-list">
          <form
            v-for="document in invite.documents"
            :key="document.value"
            class="upload-row"
            @submit.prevent="uploadDocument(document.value)"
          >
            <p class="upload-doc-label">{{ document.label }}</p>
            <label class="upload-native-label">
              Photo or PDF
              <input
                type="file"
                accept="image/*,application/pdf"
                class="upload-native-input"
                :data-doc-type="document.value"
                @click="picking[document.value] = true"
                @change="(event) => onFileChosen(document.value, event)"
              />
            </label>
            <p v-if="picking[document.value] && !staged[document.value]" class="upload-picking" role="status">
              Opening files on this phone…
            </p>
            <div v-if="staged[document.value]" class="upload-staging">
              <img
                v-if="staged[document.value].preview"
                :src="staged[document.value].preview"
                :alt="staged[document.value].name"
                class="upload-staging-preview"
              />
              <div class="upload-staging-meta">
                <span class="upload-staging-label">File selected</span>
                <span class="upload-staging-name">{{ staged[document.value].name }}</span>
              </div>
              <button type="button" class="upload-staging-remove" @click="clearStaged(document.value)">
                Remove
              </button>
            </div>
            <p v-if="fileErrors[document.value]" class="upload-file-error">{{ fileErrors[document.value] }}</p>
            <button
              type="submit"
              :disabled="uploading === document.value || !staged[document.value] || Boolean(fileErrors[document.value])"
            >
              {{ uploading === document.value ? 'Uploading…' : completed.has(document.value) ? 'Replace upload' : 'Upload' }}
            </button>
            <span v-if="completed.has(document.value)" class="upload-success">Uploaded successfully</span>
          </form>
        </div>
      </template>
    </section>
  </main>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
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
const uploading = ref('')
const completed = ref(new Set<string>())
const fileErrors = reactive<Record<string, string>>({})
const picking = reactive<Record<string, boolean>>({})
const staged = ref<Record<string, { file: File; name: string; preview: string }>>({})
const pageRoot = ref<HTMLElement | null>(null)
const token = String(route.params.token || '')

function fileExtension(name: string) {
  const parts = String(name || '').split('.')
  return parts.length > 1 ? `.${parts.pop()?.toLowerCase()}` : ''
}

function fileLooksAllowed(file: File) {
  const mime = (file.type || '').split(';')[0].trim().toLowerCase()
  if (mime.startsWith('image/') || mime === 'application/pdf') return true
  const extension = fileExtension(file.name)
  if (ALLOWED_EXTENSIONS.includes(extension)) return true
  // Android camera shots sometimes have no name and an empty MIME.
  if (!extension && !mime) return true
  return false
}

const pageTitle = computed(() => {
  if (blockReason.value === 'revoked') return 'This upload link is no longer active'
  if (blockReason.value === 'used_up') return 'This upload link cannot take more files'
  if (blockReason.value) return 'This upload link is not available'
  return 'Secure document upload'
})

const blockMessage = computed(() => {
  if (blockReason.value === 'revoked') {
    return 'Staff turned this link off. A new link can be sent if you still need to upload files.'
  }
  if (blockReason.value === 'used_up') {
    return 'This link has already received the maximum number of uploads.'
  }
  return 'This upload link is invalid. Ask staff to send a new one.'
})

function revokePreview(docType: string) {
  const current = staged.value[docType]
  if (current?.preview) URL.revokeObjectURL(current.preview)
}

function stageFile(docType: string, file: File) {
  picking[docType] = false
  if (!fileLooksAllowed(file)) {
    fileErrors[docType] = 'Use a photo or PDF.'
    return
  }
  delete fileErrors[docType]
  revokePreview(docType)
  staged.value = {
    ...staged.value,
    [docType]: {
      file,
      name: file.name || 'Photo from this phone',
      preview: (file.type || '').startsWith('image/') ? URL.createObjectURL(file) : '',
    },
  }
}

function onFileChosen(docType: string, event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) {
    picking[docType] = false
    return
  }
  stageFile(docType, file)
}

function clearStaged(docType: string) {
  revokePreview(docType)
  picking[docType] = false
  const next = { ...staged.value }
  delete next[docType]
  staged.value = next
  pageRoot.value?.querySelectorAll<HTMLInputElement>(`input[type="file"][data-doc-type="${docType}"]`).forEach((input) => {
    input.value = ''
  })
}

function harvestPickedFiles() {
  pageRoot.value?.querySelectorAll<HTMLInputElement>('input[type="file"]').forEach((input) => {
    const docType = input.dataset.docType
    const file = input.files?.[0]
    if (!docType) return
    if (!file) {
      picking[docType] = false
      return
    }
    const already = staged.value[docType]
    if (already && already.file === file) {
      picking[docType] = false
      return
    }
    stageFile(docType, file)
  })
}

async function loadInvite() {
  try {
    const response = await fetch(getApiUrl(`/api/document-upload/${encodeURIComponent(token)}/`))
    const body = await response.json().catch(() => null)
    if (!response.ok) {
      blockReason.value = body?.code || 'not_found'
      if (response.status !== 410) {
        error.value = body?.detail || 'This upload link is invalid. Ask staff to send a new one.'
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
  const file = staged.value[docType]?.file
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
      blockReason.value = body?.code || 'not_found'
      invite.value = null
      return
    }
    if (!response.ok) {
      error.value = body?.detail || 'That document could not be uploaded.'
      return
    }
    completed.value = new Set([...completed.value, docType])
    clearStaged(docType)
  } catch {
    error.value = 'The upload did not finish. Check your connection and try again.'
  } finally {
    uploading.value = ''
  }
}

onMounted(() => {
  loadInvite()
  window.addEventListener('focus', harvestPickedFiles)
  document.addEventListener('visibilitychange', harvestPickedFiles)
})

onBeforeUnmount(() => {
  window.removeEventListener('focus', harvestPickedFiles)
  document.removeEventListener('visibilitychange', harvestPickedFiles)
  Object.keys(staged.value).forEach(revokePreview)
})
</script>

<style scoped>
.upload-page { min-height: 100vh; padding: 2rem 1rem; background: #f5f5f4; color: #292524; }
.upload-card { width: min(42rem, 100%); margin: 0 auto; padding: 1.5rem; border: 1px solid #d6d3d1; border-radius: 1rem; background: white; box-shadow: 0 10px 30px rgb(28 25 23 / 8%); }
.upload-brand { color: #c2410c; font-weight: 800; text-transform: uppercase; letter-spacing: .08em; font-size: .8rem; }
h1 { margin: .5rem 0; font-size: 1.75rem; }
.upload-note, .upload-expiry { color: #78716c; font-size: .9rem; }
.upload-help {
  margin: 0.85rem 0 0;
  padding: 0.85rem 1rem;
  border-radius: 0.75rem;
  background: #fff7ed;
  border: 1px solid #fed7aa;
  color: #9a3412;
  font-size: 0.92rem;
  line-height: 1.45;
}
.upload-list { display: grid; gap: 1rem; margin-top: 1rem; }
.upload-row { display: grid; gap: .7rem; padding: 1rem; border: 1px solid #e7e5e4; border-radius: .75rem; }
.upload-doc-label { margin: 0; font-weight: 700; }
.upload-native-label {
  display: grid;
  gap: 0.4rem;
  font-size: 0.8rem;
  font-weight: 700;
  color: #57534e;
}
.upload-native-input {
  display: block;
  width: 100%;
  min-height: 3.15rem;
  font-size: 16px;
  padding: 0.55rem 0.35rem;
  background: #fff;
  border: 2px solid #e7e5e4;
  border-radius: 0.6rem;
  color: #1c1917;
}
.upload-picking {
  margin: 0;
  padding: 0.7rem 0.85rem;
  border-radius: 0.6rem;
  background: #ecfeff;
  border: 1px solid #a5f3fc;
  color: #155e75;
  font-size: 0.9rem;
  font-weight: 600;
}
.upload-row > button[type="submit"] { border: 0; border-radius: .6rem; padding: .85rem 1rem; background: #c2410c; color: white; font-weight: 700; cursor: pointer; min-height: 3rem; }
.upload-row > button[type="submit"]:disabled { opacity: .55; cursor: not-allowed; }
.upload-staging {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem 0.85rem;
  border: 2px dashed #fdba74;
  border-radius: 0.75rem;
  background: #fff7ed;
}
.upload-staging-preview {
  width: 3.25rem;
  height: 3.25rem;
  object-fit: cover;
  border-radius: 0.45rem;
  background: #fed7aa;
  flex-shrink: 0;
}
.upload-staging-meta { min-width: 0; flex: 1; display: grid; gap: 0.15rem; }
.upload-staging-label { font-size: 0.72rem; font-weight: 800; text-transform: uppercase; letter-spacing: 0.04em; color: #c2410c; }
.upload-staging-name { font-size: 0.9rem; font-weight: 700; color: #0f766e; word-break: break-word; }
.upload-staging-remove {
  flex-shrink: 0;
  border: 1px solid #fecaca;
  background: #fef2f2;
  color: #b91c1c;
  font-size: 0.75rem;
  font-weight: 700;
  padding: 0.4rem 0.7rem;
  border-radius: 0.5rem;
  cursor: pointer;
}
.upload-success { color: #047857; font-size: .85rem; font-weight: 700; }
.upload-error { margin: 1rem 0; border-radius: .6rem; padding: .8rem; background: #fef2f2; color: #b91c1c; }
.upload-file-error { margin: 0; color: #b91c1c; font-size: .85rem; font-weight: 600; }
.upload-expired { margin-top: 1rem; display: grid; gap: .75rem; }
.upload-expired-lead { font-size: 1.05rem; font-weight: 600; }
.upload-expired a { color: #c2410c; font-weight: 700; }
</style>
