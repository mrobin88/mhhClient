<template>
  <section class="space-y-3">
    <div class="staff-card p-4">
      <div class="staff-panel-header">
        <span class="material-symbols-outlined" aria-hidden="true">chat</span>
        <h3>Client messages</h3>
        <StaffTip text="SMS threads with clients. Tap a name to open the conversation, then use Main page to jump to their full record." />
      </div>
      <p class="text-sm text-stone-600">Updates every 20 seconds.</p>
    </div>

    <ClientHopBar
      v-if="hopClient"
      :client-id="hopClient.id"
      :client-name="hopClient.name"
      active="messages"
    />

    <BulldozerLoader v-if="loading && threads.length === 0" label="Loading messages…" />

    <div v-else-if="error" class="staff-card p-4 text-center space-y-3">
      <p class="text-sm">{{ error }}</p>
      <button type="button" class="staff-btn staff-btn-secondary" @click="load">Retry</button>
    </div>

    <p v-else-if="threads.length === 0" class="text-center text-sm text-stone-500 py-8">
      No recent messages.
      <span v-if="hopClient" class="block mt-2">
        <RouterLink
          :to="{ name: 'ClientDetail', params: { id: hopClient.id } }"
          class="staff-activity-link font-semibold"
        >
          Open {{ hopClient.name }}’s main page
        </RouterLink>
      </span>
    </p>

    <template v-else>
      <p v-if="!selectedId" class="text-sm text-stone-500 text-center py-2">
        Pick a conversation below.
      </p>

      <ul class="space-y-2">
        <li v-for="thread in threads" :key="thread.client_id">
          <button
            type="button"
            class="staff-card w-full text-left p-4"
            :class="{ 'staff-accent-ring': selectedId === thread.client_id }"
            @click="selectThread(thread.client_id)"
          >
            <div class="flex justify-between gap-2">
              <p class="font-semibold truncate">{{ thread.client_name }}</p>
              <span
                v-if="thread.unread"
                class="shrink-0 text-[10px] font-bold uppercase staff-accent-chip px-2 py-0.5 rounded-full"
              >
                New
              </span>
            </div>
            <p class="text-xs text-stone-500 mt-1">{{ formatTime(thread.last_at) }}</p>
            <p class="text-sm text-stone-600 mt-1 line-clamp-2">{{ thread.preview }}</p>
          </button>
        </li>
      </ul>

      <div v-if="selectedThread" class="staff-card p-4 space-y-3 max-h-[50vh] overflow-y-auto">
        <h3 class="font-semibold">
          <RouterLink
            :to="{ name: 'ClientDetail', params: { id: selectedThread.client_id } }"
            class="staff-activity-link"
          >
            {{ selectedThread.client_name }}
          </RouterLink>
        </h3>
        <RouterLink
          :to="{ name: 'ClientDetail', params: { id: selectedThread.client_id }, query: { focus: 'notes' } }"
          class="text-xs font-semibold staff-link"
        >
          Leave a case note →
        </RouterLink>
        <div
          v-for="msg in selectedThread.messages"
          :key="msg.id"
          class="flex"
          :class="msg.direction === 'outbound' ? 'justify-end' : 'justify-start'"
        >
          <div
            class="max-w-[85%] rounded-2xl px-3 py-2 text-sm"
            :class="
              msg.direction === 'outbound'
                ? 'staff-accent-fill rounded-br-sm'
                : 'bg-stone-100 text-stone-800 rounded-bl-sm'
            "
          >
            <p>{{ msg.body }}</p>
            <p class="text-[10px] mt-1 opacity-75">{{ formatTime(msg.at) }}</p>
          </div>
        </div>
      </div>

      <div
        v-else-if="queryClientId && !selectedThread && hopClient"
        class="staff-card p-4 text-sm text-stone-600"
      >
        No SMS thread for
        <RouterLink
          :to="{ name: 'ClientDetail', params: { id: hopClient.id } }"
          class="staff-activity-link font-semibold"
        >
          {{ hopClient.name }}
        </RouterLink>
        yet. You can still open their main page.
      </div>
    </template>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { staffFetch } from '../api'
import { friendlyError, networkErrorMessage } from '../utils/errors'
import BulldozerLoader from './BulldozerLoader.vue'
import ClientHopBar from './ClientHopBar.vue'
import StaffTip from './StaffTip.vue'

interface MessageRow {
  id: number
  direction: string
  body: string
  at: string
  status: string
}

interface Thread {
  client_id: number
  client_name: string
  preview: string
  last_at: string
  unread: boolean
  messages: MessageRow[]
}

const route = useRoute()
const router = useRouter()
const threads = ref<Thread[]>([])
const loading = ref(true)
const error = ref('')
const selectedId = ref<number | null>(null)
const orphanClient = ref<{ id: number; name: string } | null>(null)
let pollTimer: ReturnType<typeof setInterval> | null = null

const selectedThread = computed(() =>
  threads.value.find((t) => t.client_id === selectedId.value) ?? null,
)

const queryClientId = computed(() => {
  const raw = route.query.client
  const value = Array.isArray(raw) ? raw[0] : raw
  if (value == null || value === '') return null
  const id = Number(value)
  return Number.isFinite(id) && id > 0 ? id : null
})

const hopClient = computed(() => {
  if (selectedThread.value) {
    return { id: selectedThread.value.client_id, name: selectedThread.value.client_name }
  }
  if (orphanClient.value) return orphanClient.value
  return null
})

function formatTime(iso: string) {
  if (!iso) return ''
  return new Date(iso).toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  })
}

function selectThread(clientId: number) {
  selectedId.value = clientId
  orphanClient.value = null
  router.replace({ name: 'Messages', query: { client: String(clientId) } })
}

async function resolveOrphanClient(id: number) {
  const inList = threads.value.find((t) => t.client_id === id)
  if (inList) {
    orphanClient.value = null
    selectedId.value = id
    return
  }
  try {
    const resp = await staffFetch(`/api/staff/clients/${id}/`)
    if (!resp.ok) {
      orphanClient.value = null
      return
    }
    const body = await resp.json()
    orphanClient.value = { id: body.id, name: body.full_name || `Client #${id}` }
    selectedId.value = id
  } catch {
    orphanClient.value = null
  }
}

async function syncFromQuery() {
  const id = queryClientId.value
  if (!id) {
    // Clean empty ?client= so the URL is shareable and not confusing.
    if (route.query.client !== undefined && route.query.client !== null) {
      const empty =
        route.query.client === '' ||
        (Array.isArray(route.query.client) && route.query.client[0] === '')
      if (empty) {
        router.replace({ name: 'Messages' })
      }
    }
    // Do not auto-pick a thread — staff must choose (avoids wrong conversation).
    if (!selectedId.value) orphanClient.value = null
    return
  }
  selectedId.value = id
  await resolveOrphanClient(id)
}

async function load() {
  if (!threads.value.length) loading.value = true
  error.value = ''
  try {
    const resp = await staffFetch('/api/staff/messages/')
    const body = await resp.json().catch(() => null)
    if (!resp.ok) {
      error.value = friendlyError(body, 'Could not load messages.')
      return
    }
    threads.value = body.threads || []
    await syncFromQuery()
  } catch (e) {
    error.value = networkErrorMessage(e)
  } finally {
    loading.value = false
  }
}

watch(() => route.query.client, () => {
  void syncFromQuery()
})

onMounted(() => {
  void load()
  pollTimer = setInterval(() => {
    void load()
  }, 20_000)
})
onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
})
</script>
