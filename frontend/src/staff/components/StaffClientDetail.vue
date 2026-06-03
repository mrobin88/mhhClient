<template>
  <section class="space-y-3">
    <button type="button" class="text-sm text-slate-600 underline" @click="$emit('back')">
      ← Back to search
    </button>

    <p v-if="loading" class="text-sm text-slate-500 py-6 text-center">Loading…</p>
    <p v-else-if="error" class="text-sm text-red-700">{{ error }}</p>

    <template v-else-if="client">
      <div class="bg-white rounded-xl border border-slate-200 p-4 space-y-1">
        <h2 class="text-lg font-bold">{{ client.full_name }}</h2>
        <p class="text-sm text-slate-600">{{ client.phone }}</p>
        <p class="text-sm text-slate-600">{{ client.status }} · {{ client.staff_name || 'Unassigned' }}</p>
        <p v-if="client.address" class="text-xs text-slate-500 pt-1">{{ client.address }}, {{ client.city }}</p>
      </div>

      <div class="bg-white rounded-xl border border-slate-200 p-4 space-y-3">
        <h3 class="font-semibold">Quick case note</h3>
        <textarea
          v-model="noteContent"
          rows="3"
          placeholder="What happened today?"
          class="w-full rounded-lg border border-slate-300 px-3 py-2 text-base"
        />
        <button
          type="button"
          class="w-full rounded-lg bg-slate-900 text-white font-semibold py-2.5 disabled:opacity-60"
          :disabled="noteBusy || !noteContent.trim()"
          @click="saveNote"
        >
          {{ noteBusy ? 'Saving…' : 'Save note' }}
        </button>
        <p v-if="noteMessage" class="text-sm text-green-700">{{ noteMessage }}</p>
      </div>

      <div class="bg-white rounded-xl border border-slate-200 p-4 space-y-2">
        <h3 class="font-semibold">Recent notes</h3>
        <p v-if="notes.length === 0" class="text-sm text-slate-500">No notes yet.</p>
        <article
          v-for="note in notes"
          :key="note.id"
          class="border-t border-slate-100 pt-2 first:border-0 first:pt-0"
        >
          <p class="text-xs text-slate-500">{{ note.note_date }} · {{ note.staff_member }}</p>
          <p class="text-sm whitespace-pre-wrap">{{ note.content }}</p>
        </article>
      </div>
    </template>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { staffFetch } from '../api'

const props = defineProps<{ clientId: number }>()
defineEmits<{ (e: 'back'): void }>()

interface ClientDetail {
  id: number
  full_name: string
  phone: string
  status: string
  staff_name?: string
  address?: string
  city?: string
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
const noteMessage = ref('')

async function load() {
  loading.value = true
  error.value = ''
  try {
    const [clientResp, notesResp] = await Promise.all([
      staffFetch(`/api/staff/clients/${props.clientId}/`),
      staffFetch(`/api/staff/clients/${props.clientId}/notes/`),
    ])
    if (!clientResp.ok) {
      error.value = 'Client not found.'
      return
    }
    client.value = await clientResp.json()
    notes.value = notesResp.ok ? await notesResp.json() : []
  } catch {
    error.value = 'No connection.'
  } finally {
    loading.value = false
  }
}

async function saveNote() {
  if (!noteContent.value.trim()) return
  noteBusy.value = true
  noteMessage.value = ''
  try {
    const today = new Date().toISOString().slice(0, 10)
    const resp = await staffFetch(`/api/staff/clients/${props.clientId}/notes/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        note_date: today,
        note_type: 'general',
        content: noteContent.value.trim(),
      }),
    })
    if (!resp.ok) {
      noteMessage.value = 'Could not save note.'
      return
    }
    noteContent.value = ''
    noteMessage.value = 'Note saved.'
    const notesResp = await staffFetch(`/api/staff/clients/${props.clientId}/notes/`)
    notes.value = notesResp.ok ? await notesResp.json() : notes.value
  } catch {
    noteMessage.value = 'No connection.'
  } finally {
    noteBusy.value = false
  }
}

onMounted(load)
watch(() => props.clientId, load)
</script>
