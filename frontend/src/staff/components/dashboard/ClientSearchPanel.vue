<template>
  <section class="staff-card p-4 space-y-3">
    <h3 class="font-semibold flex items-center gap-1.5">
      <span class="material-symbols-outlined text-orange-600" aria-hidden="true">search</span>
      Find a client
    </h3>
    <input
      v-model="query"
      type="search"
      placeholder="Name or phone"
      class="staff-input"
      @input="debouncedSearch"
    />

    <p v-if="loading" class="text-sm text-stone-500">Searching…</p>
    <p v-else-if="error" class="text-sm text-stone-500">{{ error }}</p>
    <p v-else-if="query.trim().length > 0 && results.length === 0" class="text-sm text-stone-500">
      No clients found.
    </p>
    <p v-else-if="query.trim().length === 0" class="text-sm text-stone-400">
      Start typing a name or phone number.
    </p>

    <ul v-else class="space-y-2">
      <li v-for="c in results" :key="c.id">
        <RouterLink
          :to="{ name: 'ClientDetail', params: { id: c.id } }"
          class="flex items-center justify-between gap-2 border-t border-stone-100 pt-2 first:border-0 first:pt-0"
        >
          <span class="min-w-0">
            <span class="block text-sm font-semibold truncate">{{ c.full_name }}</span>
            <span class="block text-xs text-stone-500">{{ c.phone }}</span>
          </span>
          <span class="text-[10px] uppercase font-bold tracking-wide text-stone-500 bg-stone-100 rounded-full px-2 py-0.5 shrink-0">
            {{ c.status }}
          </span>
        </RouterLink>
      </li>
    </ul>

    <RouterLink to="/clients" class="block text-center text-xs font-semibold text-orange-600 pt-1">
      View all clients →
    </RouterLink>
  </section>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { staffFetch } from '../../api'

interface ClientResult {
  id: number
  full_name: string
  phone: string
  status: string
}

const query = ref('')
const results = ref<ClientResult[]>([])
const loading = ref(false)
const error = ref('')
let debounceTimer: ReturnType<typeof setTimeout> | null = null

function debouncedSearch() {
  if (debounceTimer) clearTimeout(debounceTimer)
  debounceTimer = setTimeout(search, 300)
}

async function search() {
  const q = query.value.trim()
  if (!q) {
    results.value = []
    error.value = ''
    return
  }
  loading.value = true
  error.value = ''
  try {
    const resp = await staffFetch(`/api/staff/clients/?q=${encodeURIComponent(q)}&limit=10`)
    if (!resp.ok) {
      error.value = 'Search failed. Try again.'
      return
    }
    results.value = await resp.json()
  } catch {
    error.value = 'No connection.'
  } finally {
    loading.value = false
  }
}
</script>
