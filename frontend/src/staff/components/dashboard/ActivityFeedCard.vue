<template>
  <section class="staff-card p-4">
    <div class="staff-panel-header">
      <span class="material-symbols-outlined" aria-hidden="true">history</span>
      <h3>Recent activity</h3>
    </div>
    <p v-if="caveat" class="staff-panel-note">{{ caveat }}</p>

    <CardSkeleton v-if="loading" variant="list" :count="5" />
    <p v-else-if="error" class="text-sm text-stone-500">{{ error }}</p>
    <p v-else-if="entries.length === 0" class="text-sm text-stone-500">No recent admin activity.</p>
    <ul v-else class="space-y-2 staff-fade-in">
      <li
        v-for="entry in entries"
        :key="entry.id"
        class="text-sm border-t border-stone-100 pt-2 first:border-0 first:pt-0"
      >
        <span class="font-semibold">{{ entry.actor }}</span>
        {{ entry.action.toLowerCase() }}
        <span class="text-stone-600">{{ entry.model }}</span>
        <span class="text-stone-500">— {{ entry.object_repr }}</span>
        <span class="block text-xs text-stone-400">{{ formatWhen(entry.action_time) }}</span>
      </li>
    </ul>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { staffFetch } from '../../api'
import CardSkeleton from './CardSkeleton.vue'

interface ActivityEntry {
  id: number
  actor: string
  action: string
  model: string
  object_repr: string
  change_message: string
  action_time: string
}

const entries = ref<ActivityEntry[]>([])
const loading = ref(true)
const error = ref('')
const caveat = ref('')

function formatWhen(iso: string) {
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return ''
  return date.toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  })
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const resp = await staffFetch('/api/staff/dashboard/activity-feed/?limit=12')
    if (!resp.ok) {
      error.value = 'Could not load activity feed.'
      return
    }
    const body = await resp.json()
    entries.value = body.results || []
    caveat.value = body.caveat || ''
  } catch {
    error.value = 'No connection.'
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>
