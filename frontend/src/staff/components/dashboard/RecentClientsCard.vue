<template>
  <section class="staff-card p-4">
    <div class="staff-panel-header">
      <span class="material-symbols-outlined" aria-hidden="true">person_add</span>
      <h3>Recently added</h3>
    </div>

    <CardSkeleton v-if="loading" variant="list" :count="4" />
    <p v-else-if="error" class="text-sm text-stone-500">{{ error }}</p>
    <p v-else-if="clients.length === 0" class="text-sm text-stone-500">No clients yet.</p>
    <ul v-else class="space-y-2 staff-fade-in">
      <li v-for="c in clients" :key="c.id">
        <RouterLink
          :to="{ name: 'ClientDetail', params: { id: c.id } }"
          class="flex items-center justify-between gap-2 border-t border-stone-100 pt-2 first:border-0 first:pt-0"
        >
          <span class="min-w-0">
            <span class="block text-sm font-semibold truncate">{{ c.full_name }}</span>
            <span class="block text-xs text-stone-500">{{ c.training_interest_display }}</span>
          </span>
          <span class="text-xs text-stone-400 shrink-0">{{ formatDate(c.created_at) }}</span>
        </RouterLink>
      </li>
    </ul>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { staffFetch } from '../../api'
import CardSkeleton from './CardSkeleton.vue'

interface RecentClient {
  id: number
  full_name: string
  created_at: string
  training_interest: string
  training_interest_display: string
  status: string
}

const clients = ref<RecentClient[]>([])
const loading = ref(true)
const error = ref('')

function formatDate(iso: string) {
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return ''
  return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const resp = await staffFetch('/api/staff/dashboard/recent-clients/?limit=5')
    if (!resp.ok) {
      error.value = 'Could not load recent clients.'
      return
    }
    const body = await resp.json()
    clients.value = body.results || []
  } catch {
    error.value = 'No connection.'
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>
