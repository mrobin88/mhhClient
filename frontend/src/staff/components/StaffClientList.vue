<template>
  <section class="space-y-3">
    <div class="bg-white rounded-xl border border-slate-200 p-4 space-y-3">
      <h2 class="font-semibold text-lg">Clients</h2>
      <input
        v-model="query"
        type="search"
        placeholder="Search name or phone"
        class="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-base"
        @input="debouncedSearch"
      />
    </div>

    <p v-if="loading" class="text-sm text-slate-500 text-center py-6">Loading…</p>
    <p v-else-if="error" class="text-sm text-red-700">{{ error }}</p>
    <p v-else-if="clients.length === 0" class="text-sm text-slate-500 text-center py-6">No clients found.</p>

    <ul v-else class="space-y-2">
      <li v-for="client in clients" :key="client.id">
        <button
          type="button"
          class="w-full text-left bg-white rounded-xl border border-slate-200 px-4 py-3 hover:border-slate-400"
          @click="$emit('select', client.id)"
        >
          <p class="font-semibold">{{ client.full_name }}</p>
          <p class="text-sm text-slate-600">{{ client.phone }} · {{ client.status }}</p>
          <p v-if="client.staff_name" class="text-xs text-slate-500 mt-0.5">{{ client.staff_name }}</p>
        </button>
      </li>
    </ul>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { staffFetch } from '../api'

defineEmits<{ (e: 'select', id: number): void }>()

interface ClientRow {
  id: number
  full_name: string
  phone: string
  status: string
  staff_name?: string
}

const query = ref('')
const clients = ref<ClientRow[]>([])
const loading = ref(false)
const error = ref('')
let debounceTimer: ReturnType<typeof setTimeout> | null = null

async function search() {
  loading.value = true
  error.value = ''
  try {
    const params = new URLSearchParams()
    if (query.value.trim()) params.set('q', query.value.trim())
    const resp = await staffFetch(`/api/staff/clients/?${params.toString()}`)
    if (!resp.ok) {
      error.value = 'Could not load clients.'
      return
    }
    clients.value = await resp.json()
  } catch {
    error.value = 'No connection.'
  } finally {
    loading.value = false
  }
}

function debouncedSearch() {
  if (debounceTimer) clearTimeout(debounceTimer)
  debounceTimer = setTimeout(search, 250)
}

onMounted(search)
</script>
