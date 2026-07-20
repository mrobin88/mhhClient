<template>
  <section class="staff-card p-4 space-y-3">
    <div class="staff-panel-header">
      <span class="material-symbols-outlined" aria-hidden="true">upload_file</span>
      <h3>Upload a document</h3>
      <StaffTip text="Attach an ID, resume, or other file to a client’s record. Find the person first, pick the document type, then upload." />
    </div>

    <div class="space-y-1">
      <label class="text-xs font-semibold text-stone-600">Client</label>
      <div v-if="selectedClient" class="flex items-center justify-between gap-2 staff-stat-tile">
        <RouterLink
          :to="{ name: 'ClientDetail', params: { id: selectedClient.id } }"
          class="staff-activity-link text-sm truncate"
        >
          {{ selectedClient.full_name }}
        </RouterLink>
        <button type="button" class="text-xs font-semibold text-orange-600 shrink-0" @click="clearClient">
          Change
        </button>
      </div>
      <template v-else>
        <input
          v-model="clientQuery"
          type="search"
          placeholder="Search client by name or phone"
          class="staff-input"
          @input="debouncedSearch"
        />
        <ul v-if="clientResults.length > 0" class="staff-card divide-y divide-stone-100 max-h-40 overflow-y-auto">
          <li v-for="c in clientResults" :key="c.id">
            <button
              type="button"
              class="w-full text-left px-3 py-2 text-sm hover:bg-stone-50"
              @click="selectClient(c)"
            >
              {{ c.full_name }} <span class="text-stone-400">· {{ c.phone }}</span>
            </button>
          </li>
        </ul>
      </template>
    </div>

    <div class="space-y-1">
      <label class="text-xs font-semibold text-stone-600" for="doc-type-select">Document type</label>
      <select id="doc-type-select" v-model="docType" class="staff-input">
        <option value="" disabled>Select a type…</option>
        <option v-for="opt in docTypes" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
      </select>
    </div>

    <div class="space-y-1">
      <label class="text-xs font-semibold text-stone-600" for="doc-file-input">File</label>
      <input id="doc-file-input" type="file" class="staff-input" @change="onFileChange" />
      <p class="text-[11px] text-stone-500">
        Images are compressed only if very large; PDFs/docs upload as-is.
      </p>
    </div>

    <button
      type="button"
      class="staff-btn staff-btn-primary w-full"
      :disabled="busy || !selectedClient || !docType || !file"
      @click="upload"
    >
      {{ busy ? 'Uploading…' : 'Upload document' }}
    </button>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { staffFetch } from '../../api'
import { friendlyError, networkErrorMessage } from '../../utils/errors'
import { useToast } from '../../composables/useToast'
import StaffTip from '../StaffTip.vue'

interface ClientOption {
  id: number
  full_name: string
  phone: string
}

interface DocTypeOption {
  value: string
  label: string
}

const clientQuery = ref('')
const clientResults = ref<ClientOption[]>([])
const selectedClient = ref<ClientOption | null>(null)
const docTypes = ref<DocTypeOption[]>([])
const docType = ref('')
const file = ref<File | null>(null)
const busy = ref(false)
const toast = useToast()
let debounceTimer: ReturnType<typeof setTimeout> | null = null

function debouncedSearch() {
  if (debounceTimer) clearTimeout(debounceTimer)
  debounceTimer = setTimeout(searchClients, 300)
}

async function searchClients() {
  const q = clientQuery.value.trim()
  if (q.length < 2) {
    clientResults.value = []
    return
  }
  try {
    const resp = await staffFetch(`/api/staff/clients/?q=${encodeURIComponent(q)}&limit=6`)
    if (!resp.ok) return
    clientResults.value = await resp.json()
  } catch {
    /* keep prior results on transient error */
  }
}

function selectClient(client: ClientOption) {
  selectedClient.value = client
  clientResults.value = []
  clientQuery.value = ''
}

function clearClient() {
  selectedClient.value = null
}

function onFileChange(event: Event) {
  const input = event.target as HTMLInputElement
  file.value = input.files?.[0] || null
}

async function loadDocTypes() {
  try {
    const resp = await staffFetch('/api/staff/dashboard/document-types/')
    if (!resp.ok) return
    const body = await resp.json()
    docTypes.value = body.results || []
  } catch {
    /* dropdown stays empty; user can retry by reloading */
  }
}

async function upload() {
  if (busy.value || !selectedClient.value || !docType.value || !file.value) return
  busy.value = true
  try {
    const formData = new FormData()
    formData.append('client_id', String(selectedClient.value.id))
    formData.append('doc_type', docType.value)
    formData.append('file', file.value)

    const resp = await staffFetch('/api/staff/dashboard/document-upload/', {
      method: 'POST',
      body: formData,
    })
    const body = await resp.json().catch(() => null)
    if (!resp.ok) {
      toast.error(friendlyError(body, 'Could not upload document.'))
      return
    }
    toast.success(body?.message || 'Document uploaded.')
    docType.value = ''
    file.value = null
    selectedClient.value = null
  } catch (err) {
    toast.error(networkErrorMessage(err))
  } finally {
    busy.value = false
  }
}

onMounted(loadDocTypes)
</script>
