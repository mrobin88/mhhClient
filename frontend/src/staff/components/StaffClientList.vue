<template>
  <section class="space-y-3">
    <div class="staff-card p-4">
      <h2 class="font-bold text-lg mb-3">Find a client</h2>
      <input
        v-model="query"
        type="search"
        placeholder="Name or phone"
        class="staff-input"
        @input="debouncedSearch"
      />
    </div>

    <SkeletonClientList v-if="loading" />
    <div v-else-if="error" class="staff-card p-4 text-center space-y-3">
      <p class="text-sm text-stone-600">{{ error }}</p>
      <button type="button" class="staff-btn staff-btn-secondary" @click="search">Try again</button>
    </div>
    <p v-else-if="clients.length === 0" class="text-sm text-stone-500 text-center py-8">No clients found.</p>

    <ul v-else class="space-y-2">
      <li v-for="client in clients" :key="client.id">
        <button
          type="button"
          class="staff-card w-full text-left px-4 py-3 hover:border-orange-300 transition-colors"
          @click="router.push({ name: 'ClientDetail', params: { id: client.id } })"
        >
          <p class="font-semibold">{{ client.full_name }}</p>
          <p class="text-sm text-stone-600">{{ client.phone }} · {{ client.status }}</p>
        </button>
      </li>
    </ul>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { staffFetch } from '../api'
import { friendlyError, networkErrorMessage } from '../utils/errors'
import SkeletonClientList from './SkeletonClientList.vue'

interface ClientRow {
  id: number
  full_name: string
  phone: string
  status: string
}

const router = useRouter()
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
    const body = await resp.json().catch(() => null)
    if (!resp.ok) {
      error.value = friendlyError(body, 'Could not load clients.')
      return
    }
    clients.value = body
  } catch (e) {
    error.value = networkErrorMessage(e)
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
