<template>
  <section class="space-y-3">
    <div class="staff-card p-4">
      <h2 class="font-bold text-lg">Training / skill note</h2>
      <p class="text-sm text-stone-600 mt-1">
        Log workforce training progress for a client (saved as a training case note).
      </p>
    </div>

    <form class="staff-card p-4 space-y-4 relative" @submit.prevent="submit">
      <div
        v-if="busy"
        class="absolute inset-0 bg-white/80 rounded-xl flex items-center justify-center z-10"
      >
        <BulldozerLoader label="Saving…" />
      </div>

      <div>
        <label class="block text-sm font-semibold mb-2">Client</label>
        <input
          v-model="clientQuery"
          type="search"
          class="staff-input"
          placeholder="Search name or phone"
          @input="searchClients"
        />
        <ul v-if="clientOptions.length" class="mt-2 border border-stone-200 rounded-lg overflow-hidden">
          <li v-for="c in clientOptions" :key="c.id">
            <button
              type="button"
              class="w-full text-left px-3 py-2 text-sm hover:bg-orange-50"
              :class="{ 'bg-orange-100 font-semibold': selectedClient?.id === c.id }"
              @click="selectClient(c)"
            >
              {{ c.full_name }} · {{ c.phone }}
            </button>
          </li>
        </ul>
        <p v-if="fieldErrors.client" class="text-sm text-red-700 mt-1">{{ fieldErrors.client }}</p>
      </div>

      <div>
        <label class="block text-sm font-semibold mb-2">Skill / training covered</label>
        <input v-model="skillTitle" type="text" class="staff-input" placeholder="e.g. Forklift safety, soft skills" />
        <p v-if="fieldErrors.skill" class="text-sm text-red-700 mt-1">{{ fieldErrors.skill }}</p>
      </div>

      <div>
        <label class="block text-sm font-semibold mb-2">Details</label>
        <textarea v-model="content" rows="4" class="staff-input" placeholder="What did the client learn or practice?" />
        <p v-if="fieldErrors.content" class="text-sm text-red-700 mt-1">{{ fieldErrors.content }}</p>
      </div>

      <div>
        <label class="block text-sm font-semibold mb-2">Next steps (optional)</label>
        <input v-model="nextSteps" type="text" class="staff-input" />
      </div>

      <button type="submit" class="staff-btn staff-btn-primary w-full" :disabled="busy">
        Save training note
      </button>
    </form>

    <div v-if="saved" class="staff-card p-4 text-center space-y-2 border-green-200 bg-green-50">
      <p class="font-semibold text-green-800">Training note saved</p>
      <button type="button" class="staff-btn staff-btn-secondary" @click="resetForm">Add another</button>
      <RouterLink
        v-if="selectedClient"
        :to="{ name: 'ClientDetail', params: { id: selectedClient.id } }"
        class="block text-sm font-semibold text-orange-600"
      >
        View {{ selectedClient.full_name }}
      </RouterLink>
    </div>
  </section>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { staffFetch } from '../api'
import { friendlyError, networkErrorMessage } from '../utils/errors'
import { useToast } from '../composables/useToast'
import BulldozerLoader from './BulldozerLoader.vue'

interface ClientOption {
  id: number
  full_name: string
  phone: string
}

const toast = useToast()
const clientQuery = ref('')
const clientOptions = ref<ClientOption[]>([])
const selectedClient = ref<ClientOption | null>(null)
const skillTitle = ref('')
const content = ref('')
const nextSteps = ref('')
const busy = ref(false)
const saved = ref(false)
const fieldErrors = reactive({ client: '', skill: '', content: '' })

let searchTimer: ReturnType<typeof setTimeout> | null = null

async function searchClients() {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(async () => {
    const q = clientQuery.value.trim()
    if (q.length < 2) {
      clientOptions.value = []
      return
    }
    const resp = await staffFetch(`/api/staff/clients/?q=${encodeURIComponent(q)}&limit=8`)
    if (resp.ok) clientOptions.value = await resp.json()
  }, 250)
}

function selectClient(c: ClientOption) {
  selectedClient.value = c
  clientQuery.value = c.full_name
  clientOptions.value = []
  fieldErrors.client = ''
}

function resetForm() {
  saved.value = false
  skillTitle.value = ''
  content.value = ''
  nextSteps.value = ''
  selectedClient.value = null
  clientQuery.value = ''
}

async function submit() {
  fieldErrors.client = ''
  fieldErrors.skill = ''
  fieldErrors.content = ''
  if (!selectedClient.value) fieldErrors.client = 'Select a client.'
  if (!skillTitle.value.trim()) fieldErrors.skill = 'Enter a skill or training topic.'
  if (!content.value.trim()) fieldErrors.content = 'Add training details.'
  if (fieldErrors.client || fieldErrors.skill || fieldErrors.content) return

  busy.value = true
  saved.value = false
  try {
    const noteBody = `[${skillTitle.value.trim()}]\n\n${content.value.trim()}`
    const resp = await staffFetch(`/api/staff/clients/${selectedClient.value!.id}/notes/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        note_date: new Date().toISOString().slice(0, 10),
        note_type: 'training',
        content: noteBody,
        next_steps: nextSteps.value.trim() || undefined,
      }),
    })
    const body = await resp.json().catch(() => null)
    if (!resp.ok) {
      toast.error(friendlyError(body, 'Could not save training note.'))
      return
    }
    saved.value = true
    toast.success('Training note saved.')
  } catch (e) {
    toast.error(networkErrorMessage(e))
  } finally {
    busy.value = false
  }
}
</script>
