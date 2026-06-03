<template>
  <section class="space-y-3">
    <div class="staff-card p-4">
      <h2 class="font-bold text-lg">Client messages</h2>
      <p class="text-sm text-stone-600 mt-1">SMS threads with program clients (updates every 20s)</p>
    </div>

    <BulldozerLoader v-if="loading && threads.length === 0" label="Loading messages…" />

    <div v-else-if="error" class="staff-card p-4 text-center space-y-3">
      <p class="text-sm">{{ error }}</p>
      <button type="button" class="staff-btn staff-btn-secondary" @click="load">Retry</button>
    </div>

    <p v-else-if="threads.length === 0" class="text-center text-sm text-stone-500 py-8">No recent messages.</p>

    <ul v-else class="space-y-2">
      <li v-for="thread in threads" :key="thread.client_id">
        <button
          type="button"
          class="staff-card w-full text-left p-4"
          :class="{ 'ring-2 ring-orange-400': selectedId === thread.client_id }"
          @click="selectedId = thread.client_id"
        >
          <div class="flex justify-between gap-2">
            <p class="font-semibold truncate">{{ thread.client_name }}</p>
            <span
              v-if="thread.unread"
              class="shrink-0 text-[10px] font-bold uppercase bg-orange-100 text-orange-800 px-2 py-0.5 rounded-full"
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
      <h3 class="font-semibold">{{ selectedThread.client_name }}</h3>
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
              ? 'bg-orange-600 text-white rounded-br-sm'
              : 'bg-stone-100 text-stone-800 rounded-bl-sm'
          "
        >
          <p>{{ msg.body }}</p>
          <p class="text-[10px] mt-1 opacity-75">{{ formatTime(msg.at) }}</p>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { staffFetch } from '../api'
import { friendlyError, networkErrorMessage } from '../utils/errors'
import BulldozerLoader from './BulldozerLoader.vue'

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

const threads = ref<Thread[]>([])
const loading = ref(true)
const error = ref('')
const selectedId = ref<number | null>(null)
let pollTimer: ReturnType<typeof setInterval> | null = null

const selectedThread = computed(() =>
  threads.value.find((t) => t.client_id === selectedId.value) ?? null,
)

function formatTime(iso: string) {
  if (!iso) return ''
  return new Date(iso).toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  })
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
    if (!selectedId.value && threads.value.length) {
      selectedId.value = threads.value[0].client_id
    }
  } catch (e) {
    error.value = networkErrorMessage(e)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  load()
  pollTimer = setInterval(load, 20_000)
})
onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
})
</script>
