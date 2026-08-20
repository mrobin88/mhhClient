<template>
  <div class="staff-card p-4 space-y-3">
    <div class="staff-panel-header">
      <span class="material-symbols-outlined" aria-hidden="true">upload_file</span>
      <h3>Client document upload link</h3>
      <StaffTip text="Create an expiring link that can upload only the documents you select. The link cannot view or download the client record." />
    </div>
    <p class="text-xs text-stone-500">
      Select missing documents, then copy the link or send it directly.
    </p>
    <div v-if="loading" class="text-sm text-stone-500">Loading document checklist…</div>
    <template v-else>
      <div class="grid grid-cols-1 sm:grid-cols-2 gap-1.5 max-h-64 overflow-y-auto">
        <label v-for="option in options" :key="option.value" class="flex items-start gap-2 text-xs text-stone-700">
          <input v-model="selected" type="checkbox" :value="option.value" />
          <span>{{ option.label }}</span>
        </label>
      </div>
      <div class="flex flex-wrap gap-2">
        <button type="button" class="staff-btn staff-btn-secondary" @click="selected = [...suggested]">
          Select missing
        </button>
        <button type="button" class="staff-btn staff-btn-secondary" @click="selected = []">Clear</button>
      </div>
      <div class="grid grid-cols-1 sm:grid-cols-2 gap-2">
        <select v-model="delivery" class="staff-input" aria-label="Link delivery">
          <option value="copy">Create and copy link</option>
          <option value="email">Send by email</option>
          <option value="sms">Send by text message</option>
        </select>
        <select v-model.number="expiresDays" class="staff-input" aria-label="Link expiration">
          <option :value="7">Expires in 7 days</option>
          <option :value="14">Expires in 14 days</option>
          <option :value="30">Expires in 30 days</option>
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
      <div v-if="invites.length" class="space-y-1">
        <p class="text-xs font-semibold text-stone-600">Recent links</p>
        <div v-for="invite in invites" :key="invite.id" class="flex items-center justify-between gap-2 text-xs">
          <span>
            {{ invite.is_usable ? 'Active' : invite.revoked_at ? 'Revoked' : 'Expired' }}
            · {{ invite.upload_count }} upload(s) · expires {{ shortDate(invite.expires_at) }}
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
import { onMounted, ref } from 'vue'
import { staffFetch } from '../api'
import { friendlyError, networkErrorMessage } from '../utils/errors'
import { useToast } from '../composables/useToast'
import StaffTip from './StaffTip.vue'

const props = defineProps<{ clientId: number }>()
const toast = useToast()
const loading = ref(true)
const creating = ref(false)
const options = ref<Array<{ value: string; label: string }>>([])
const suggested = ref<string[]>([])
const selected = ref<string[]>([])
const delivery = ref<'copy' | 'email' | 'sms'>('copy')
const expiresDays = ref(14)
const latestLink = ref('')
const invites = ref<Array<{
  id: number
  expires_at: string
  upload_count: number
  revoked_at: string | null
  is_usable: boolean
}>>([])

function shortDate(value: string) {
  return new Date(value).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
}

async function load() {
  loading.value = true
  try {
    const response = await staffFetch(`/api/staff/clients/${props.clientId}/upload-invites/`)
    const body = await response.json().catch(() => null)
    if (!response.ok) {
      toast.error(friendlyError(body, 'Could not load document links.'))
      return
    }
    options.value = body.document_options || []
    suggested.value = body.suggested_doc_types || []
    selected.value = [...suggested.value]
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
        expires_days: expiresDays.value,
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
