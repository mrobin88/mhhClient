<template>
  <section class="staff-card p-4 space-y-3 staff-search-hero">
    <div class="staff-panel-header">
      <span class="material-symbols-outlined" aria-hidden="true">search</span>
      <h3>Find someone</h3>
      <StaffTip text="Type a name or phone. Open their info here, add them to a class, or go to their full page." />
    </div>
    <input
      ref="searchInput"
      v-model="query"
      type="search"
      placeholder="Name or phone"
      class="staff-input staff-search-hero-input"
      autocomplete="off"
      @input="debouncedSearch"
    />

    <CardSkeleton v-if="loading" variant="list" :count="3" />
    <p v-else-if="error" class="text-sm text-stone-500">{{ error }}</p>
    <p v-else-if="query.trim().length > 0 && results.length === 0" class="text-sm text-stone-500">
      No clients found.
      <RouterLink :to="{ name: 'ClientCreate' }" class="staff-link font-semibold">Add a client →</RouterLink>
    </p>
    <p v-else-if="query.trim().length === 0" class="text-sm text-stone-400">
      Start typing a name or phone number.
    </p>

    <ul v-else class="space-y-2 staff-fade-in">
      <li v-for="c in results" :key="c.id">
        <button
          type="button"
          class="w-full text-left flex items-center justify-between gap-2 border-t border-stone-100 pt-2 first:border-0 first:pt-0"
          :class="{ 'staff-search-result-active': selected?.id === c.id }"
          @click="selectClient(c)"
        >
          <span class="min-w-0">
            <span class="block text-sm font-semibold truncate">{{ c.full_name }}</span>
            <span class="block text-xs text-stone-500">
              {{ c.phone }}
              <span v-if="c.training_interest_display"> · {{ c.training_interest_display }}</span>
            </span>
          </span>
          <span class="text-[10px] uppercase font-bold tracking-wide text-stone-500 bg-stone-100 rounded-full px-2 py-0.5 shrink-0">
            {{ c.status }}
          </span>
        </button>
      </li>
    </ul>

    <div v-if="selected" class="staff-search-picked staff-fade-in">
      <div class="flex items-start justify-between gap-2">
        <div class="min-w-0">
          <p class="font-semibold">{{ selected.full_name }}</p>
          <p class="text-sm text-stone-600 mt-0.5">{{ selected.phone }}</p>
          <p v-if="selected.email" class="text-sm text-stone-600">{{ selected.email }}</p>
        </div>
        <RouterLink
          :to="{ name: 'ClientDetail', params: { id: selected.id } }"
          class="staff-btn staff-btn-secondary staff-btn-sm shrink-0"
        >
          Full page
        </RouterLink>
      </div>
      <dl class="staff-search-meta">
        <div>
          <dt>Program</dt>
          <dd>{{ selected.training_interest_display || '—' }}</dd>
        </div>
        <div>
          <dt>Status</dt>
          <dd>{{ selected.status }}</dd>
        </div>
        <div v-if="stageLine">
          <dt>Stage</dt>
          <dd>{{ stageLine }}</dd>
        </div>
        <div v-if="selected.staff_name">
          <dt>Staff</dt>
          <dd>{{ selected.staff_name }}</dd>
        </div>
        <div v-if="selected.neighborhood">
          <dt>Neighborhood</dt>
          <dd>{{ selected.neighborhood }}</dd>
        </div>
      </dl>
      <ClientQuickEnroll :client-id="selected.id" />
    </div>

    <RouterLink to="/clients" class="block text-center text-xs font-semibold staff-link pt-1">
      View all clients →
    </RouterLink>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { staffFetch } from '../../api'
import CardSkeleton from './CardSkeleton.vue'
import StaffTip from '../StaffTip.vue'
import ClientQuickEnroll from '../ClientQuickEnroll.vue'

interface ClientResult {
  id: number
  full_name: string
  phone: string
  email?: string | null
  status: string
  staff_name?: string | null
  neighborhood?: string | null
  training_interest: string
  training_interest_display: string
  pit_stop_stage?: string
  pit_stop_stage_display?: string
  citybuild_stage?: string
  citybuild_stage_display?: string
}

const query = ref('')
const results = ref<ClientResult[]>([])
const selected = ref<ClientResult | null>(null)
const loading = ref(false)
const error = ref('')
const searchInput = ref<HTMLInputElement | null>(null)
let debounceTimer: ReturnType<typeof setTimeout> | null = null

const stageLine = computed(() => {
  const c = selected.value
  if (!c) return ''
  if (c.training_interest === 'pit_stop') return c.pit_stop_stage_display || ''
  if (c.training_interest === 'citybuild') return c.citybuild_stage_display || ''
  return ''
})

function selectClient(c: ClientResult) {
  selected.value = selected.value?.id === c.id ? null : c
}

function debouncedSearch() {
  if (debounceTimer) clearTimeout(debounceTimer)
  debounceTimer = setTimeout(search, 300)
}

async function search() {
  const q = query.value.trim()
  if (!q) {
    results.value = []
    selected.value = null
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
    if (results.value.length === 1) {
      selected.value = results.value[0]
    } else if (selected.value && !results.value.some((c) => c.id === selected.value?.id)) {
      selected.value = null
    }
  } catch {
    error.value = 'No connection.'
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  searchInput.value?.focus()
})
</script>
