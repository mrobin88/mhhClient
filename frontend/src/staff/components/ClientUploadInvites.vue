<template>
  <div id="client-documents" class="staff-card p-4 space-y-3">
    <div class="staff-panel-header">
      <span class="material-symbols-outlined" aria-hidden="true">folder_open</span>
      <h3>Documents</h3>
      <StaffTip text="This is the same checklist as Django admin. Missing items are what you still need to request. Check those, then send a secure upload link." />
    </div>
    <p v-if="!loading" class="text-xs text-stone-500">
      {{ onFileCount }} of {{ totalCount }} on file
      <template v-if="missingCount"> · {{ missingCount }} still needed</template>
    </p>
    <div v-if="loading" class="text-sm text-stone-500">Loading document checklist…</div>
    <template v-else>
      <div class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead>
            <tr class="text-left text-xs text-stone-500 border-b border-stone-200">
              <th class="w-8 py-1.5 font-semibold"></th>
              <th class="py-1.5 font-semibold">Document</th>
              <th class="py-1.5 font-semibold w-24">Status</th>
            </tr>
          </thead>
          <tbody>
            <template v-for="(item, index) in checklist" :key="item.value + index">
              <tr v-if="item.panel && item.panel !== checklist[index - 1]?.panel">
                <td colspan="3" class="pt-3 pb-1 text-[11px] font-bold uppercase tracking-wide text-stone-500">
                  {{ item.panel }}
                </td>
              </tr>
              <tr class="border-b border-stone-100">
                <td class="py-1.5 align-top">
                  <input
                    v-if="item.sendable"
                    v-model="selected"
                    type="checkbox"
                    :value="item.value"
                    :aria-label="item.label"
                  />
                </td>
                <td class="py-1.5 pr-2">{{ item.label }}</td>
                <td class="py-1.5 whitespace-nowrap font-semibold" :class="item.present ? 'text-emerald-700' : 'text-red-700'">
                  {{ item.present ? 'On file' : 'Missing' }}
                </td>
              </tr>
            </template>
          </tbody>
        </table>
      </div>
      <p class="text-xs text-stone-500">
        Check missing items, then copy the link or send it. The link stays active until you revoke it.
      </p>
      <div class="flex flex-wrap gap-2">
        <button type="button" class="staff-btn staff-btn-secondary" @click="selected = [...suggestedSendable]">
          Select missing
        </button>
        <button type="button" class="staff-btn staff-btn-secondary" @click="selected = []">Clear</button>
      </div>
      <div class="grid grid-cols-1 gap-2">
        <select v-model="delivery" class="staff-input" aria-label="Link delivery">
          <option value="copy">Create and copy link</option>
          <option value="email">Send by email</option>
          <option value="sms">Send by text message</option>
        </select>
      </div>
      <button
        type="button"
        class="staff-btn staff-btn-primary w-full"
        :disabled="creating || selected.length === 0"
        @click="createInvite"
      >
        {{ creating ? 'Creating secure link…' : 'Create secure upload link' }}
      </button>
      <div v-if="latestLink" class="staff-stat-tile space-y-2">
        <p class="text-xs break-all">{{ latestLink }}</p>
        <button type="button" class="staff-btn staff-btn-secondary w-full" @click="copyLatest">Copy link</button>
      </div>
      <div v-if="files.length" class="space-y-1 pt-1">
        <p class="text-xs font-semibold text-stone-600">Files on record</p>
        <ul class="space-y-1">
          <li v-for="file in files" :key="file.id" class="text-xs text-stone-600">
            {{ file.doc_type_label }} · {{ file.title }}
            <span v-if="file.uploaded_by"> · {{ file.uploaded_by }}</span>
          </li>
        </ul>
      </div>
      <div v-if="invites.length" class="space-y-1">
        <p class="text-xs font-semibold text-stone-600">Recent links</p>
        <div v-for="invite in invites" :key="invite.id" class="flex items-center justify-between gap-2 text-xs">
          <span>
            {{ invite.is_usable ? 'Active' : 'Revoked' }}
            · {{ invite.upload_count }} upload(s)
          </span>
          <button
            v-if="invite.is_usable"
            type="button"
            class="text-red-700 font-semibold"
            @click="revoke(invite.id)"
          >
            Revoke
          </button>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { staffFetch } from '../api'
import { friendlyError, networkErrorMessage } from '../utils/errors'
import { useToast } from '../composables/useToast'
import StaffTip from './StaffTip.vue'

interface ChecklistItem {
  value: string
  label: string
  panel: string
  present: boolean
  sendable: boolean
}

interface FileRow {
  id: number
  doc_type: string
  doc_type_label: string
  title: string
  uploaded_by: string
}

const props = defineProps<{ clientId: number }>()
const toast = useToast()
const loading = ref(true)
const creating = ref(false)
const checklist = ref<ChecklistItem[]>([])
const files = ref<FileRow[]>([])
const onFileCount = ref(0)
const totalCount = ref(0)
const missingCount = ref(0)
const suggested = ref<string[]>([])
const selected = ref<string[]>([])
const delivery = ref<'copy' | 'email' | 'sms'>('copy')
const latestLink = ref('')
const invites = ref<Array<{
  id: number
  upload_count: number
  revoked_at: string | null
  is_usable: boolean
}>>([])

const suggestedSendable = computed(() => {
  const sendable = new Set(
    checklist.value.filter((item) => item.sendable && !item.present).map((item) => item.value),
  )
  return suggested.value.filter((value) => sendable.has(value) || !checklist.value.length)
})

async function load() {
  loading.value = true
  try {
    const response = await staffFetch(`/api/staff/clients/${props.clientId}/upload-invites/`)
    const body = await response.json().catch(() => null)
    if (!response.ok) {
      toast.error(friendlyError(body, 'Could not load document links.'))
      return
    }
    checklist.value = body.checklist || []
    files.value = body.files || []
    onFileCount.value = body.on_file_count || 0
    totalCount.value = body.total_count || checklist.value.length
    missingCount.value = body.missing_count || 0
    suggested.value = body.suggested_doc_types || []
    selected.value = checklist.value
      .filter((item) => item.sendable && !item.present)
      .map((item) => item.value)
    invites.value = body.results || []
  } catch (error) {
    toast.error(networkErrorMessage(error))
  } finally {
    loading.value = false
  }
}

async function createInvite() {
  if (!selected.value.length || creating.value) return
  creating.value = true
  try {
    const response = await staffFetch(`/api/staff/clients/${props.clientId}/upload-invites/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        doc_types: selected.value,
        delivery: delivery.value,
      }),
    })
    const body = await response.json().catch(() => null)
    if (!response.ok) {
      toast.error(friendlyError(body, 'Could not create the upload link.'))
      return
    }
    latestLink.value = body.link
    if (delivery.value === 'copy') await copyLatest()
    toast.success(body.delivery_detail || 'Secure upload link created.')
    await load()
  } catch (error) {
    toast.error(networkErrorMessage(error))
  } finally {
    creating.value = false
  }
}

async function copyLatest() {
  if (!latestLink.value) return
  await navigator.clipboard.writeText(latestLink.value)
  toast.success('Upload link copied.')
}

async function revoke(inviteId: number) {
  const response = await staffFetch(`/api/staff/upload-invites/${inviteId}/revoke/`, { method: 'POST' })
  if (!response.ok) {
    toast.error('Could not revoke that link.')
    return
  }
  toast.success('Upload link revoked.')
  await load()
}

onMounted(load)
</script>
