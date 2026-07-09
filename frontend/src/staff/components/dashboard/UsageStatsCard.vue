<template>
  <section class="staff-card p-4 space-y-3">
    <h3 class="font-semibold flex items-center gap-1.5">
      <span class="material-symbols-outlined text-orange-600" aria-hidden="true">monitoring</span>
      Usage this month
    </h3>

    <p v-if="loading" class="text-sm text-stone-500">Loading…</p>
    <p v-else-if="error" class="text-sm text-stone-500">{{ error }}</p>
    <div v-else-if="stats" class="staff-stat-grid">
      <div class="staff-stat-tile">
        <p class="staff-stat-value">{{ stats.total_active_clients }}</p>
        <p class="staff-stat-label">Active clients</p>
      </div>
      <div class="staff-stat-tile">
        <p class="staff-stat-value">{{ stats.clients_updated_7d }}</p>
        <p class="staff-stat-label">Updated (7d)</p>
      </div>
      <div class="staff-stat-tile">
        <p class="staff-stat-value">{{ stats.documents_uploaded_30d }}</p>
        <p class="staff-stat-label">Docs uploaded (30d)</p>
      </div>
      <div class="staff-stat-tile">
        <p class="staff-stat-value">{{ stats.staff_active_7d }}</p>
        <p class="staff-stat-label">Staff active (7d)</p>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { staffFetch } from '../../api'

interface UsageStats {
  total_active_clients: number
  clients_updated_7d: number
  clients_updated_30d: number
  documents_uploaded_7d: number
  documents_uploaded_30d: number
  staff_active_7d: number
  staff_active_30d: number
}

const stats = ref<UsageStats | null>(null)
const loading = ref(true)
const error = ref('')

async function load() {
  loading.value = true
  error.value = ''
  try {
    const resp = await staffFetch('/api/staff/dashboard/usage-stats/')
    if (!resp.ok) {
      error.value = 'Could not load usage stats.'
      return
    }
    stats.value = await resp.json()
  } catch {
    error.value = 'No connection.'
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>
