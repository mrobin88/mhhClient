<template>
  <section class="staff-card p-4 space-y-3">
    <div class="staff-panel-header">
      <span class="material-symbols-outlined" aria-hidden="true">search</span>
      <h3>Find a client</h3>
      <StaffTip text="Type a name or phone. Tap the person to open their page — update info or enroll in JRT / orientation there." />
    </div>
    <input
      v-model="query"
      type="search"
      placeholder="Name or phone"
      class="staff-input"
      @input="debouncedSearch"
    />

    <CardSkeleton v-if="loading" variant="list" :count="3" />
    <p v-else-if="error" class="text-sm text-stone-500">{{ error }}</p>
    <p v-else-if="query.trim().length > 0 && results.length === 0" class="text-sm text-stone-500">
      No clients found.
    </p>
    <p v-else-if="query.trim().length === 0" class="text-sm text-stone-400">
      Start typing a name or phone number.
    </p>

    <ul v-else class="space-y-2 staff-fade-in">
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

    <RouterLink to="/clients" class="block text-center text-xs font-semibold staff-link pt-1">
      View all clients →
    </RouterLink>
  </section>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { staffFetch } from '../../api'
import CardSkeleton from './CardSkeleton.vue'
import StaffTip from '../StaffTip.vue'

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
