<template>
  <section class="space-y-3">
    <button type="button" class="text-sm font-semibold text-orange-600" @click="router.back()">
      ← Back
    </button>

    <BulldozerLoader v-if="loading" label="Loading client…" />
    <div v-else-if="error" class="staff-card p-4 text-center space-y-3">
      <p class="text-sm">{{ error }}</p>
      <button type="button" class="staff-btn staff-btn-secondary" @click="load">Retry</button>
    </div>

    <template v-else-if="client">
      <div class="staff-card p-4">
        <h2 class="text-lg font-bold">{{ client.full_name }}</h2>
        <p class="text-sm text-stone-600">{{ client.phone }}</p>
        <p class="text-sm text-stone-600">{{ client.status }} · {{ client.staff_name || 'Unassigned' }}</p>
      </div>

      <div class="staff-card p-4 space-y-3 relative">
        <div
          v-if="noteBusy"
          class="absolute inset-0 bg-white/70 rounded-xl flex items-center justify-center z-10"
        >
          <BulldozerLoader label="Saving note…" />
        </div>
        <h3 class="font-semibold">Quick case note</h3>
        <textarea
          v-model="noteContent"
          rows="4"
          class="staff-input"
          placeholder="What happened today?"
        />
        <button
          type="button"
          class="staff-btn staff-btn-primary w-full"
          :disabled="noteBusy || !noteContent.trim()"
          @click="saveNote"
        >
          Save note
        </button>
      </div>

      <div class="staff-card p-4 space-y-2">
        <h3 class="font-semibold">Recent notes</h3>
        <p v-if="notes.length === 0" class="text-sm text-stone-500">No notes yet.</p>
        <article
          v-for="note in notes"
          :key="note.id"
          class="border-t border-stone-100 pt-2 first:border-0 first:pt-0"
        >
          <p class="text-xs text-stone-500">{{ note.note_date }} · {{ note.staff_member }}</p>
          <p class="text-sm whitespace-pre-wrap">{{ note.content }}</p>
        </article>
      </div>
    </template>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { staffFetch } from '../api'
import { friendlyError, networkErrorMessage } from '../utils/errors'
import { useToast } from '../composables/useToast'
import BulldozerLoader from './BulldozerLoader.vue'

const route = useRoute()
const router = useRouter()
const toast = useToast()

interface ClientDetail {
  id: number
  full_name: string
  phone: string
  status: string
  staff_name?: string
}

interface CaseNote {
  id: number
  note_date: string
  content: string
  staff_member: string
}

const client = ref<ClientDetail | null>(null)
const notes = ref<CaseNote[]>([])
const loading = ref(true)
const error = ref('')
const noteContent = ref('')
const noteBusy = ref(false)

const clientId = () => Number(route.params.id)

async function load() {
  loading.value = true
  error.value = ''
  try {
    const id = clientId()
    const [clientResp, notesResp] = await Promise.all([
      staffFetch(`/api/staff/clients/${id}/`),
      staffFetch(`/api/staff/clients/${id}/notes/`),
    ])
    if (!clientResp.ok) {
      error.value = 'Client not found.'
      return
    }
    client.value = await clientResp.json()
    notes.value = notesResp.ok ? await notesResp.json() : []
  } catch (e) {
    error.value = networkErrorMessage(e)
  } finally {
    loading.value = false
  }
}

async function saveNote() {
  if (!noteContent.value.trim()) return
  noteBusy.value = true
  try {
    const resp = await staffFetch(`/api/staff/clients/${clientId()}/notes/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        note_date: new Date().toISOString().slice(0, 10),
        note_type: 'general',
        content: noteContent.value.trim(),
      }),
    })
    const body = await resp.json().catch(() => null)
    if (!resp.ok) {
      toast.error(friendlyError(body, 'Could not save your note.'))
      return
    }
    noteContent.value = ''
    toast.success('Case note saved.')
    const notesResp = await staffFetch(`/api/staff/clients/${clientId()}/notes/`)
    notes.value = notesResp.ok ? await notesResp.json() : notes.value
  } catch (e) {
    toast.error(networkErrorMessage(e))
  } finally {
    noteBusy.value = false
  }
}

onMounted(load)
watch(() => route.params.id, load)
</script>
