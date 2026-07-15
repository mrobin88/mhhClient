<template>
  <section class="staff-card p-4">
    <div class="staff-panel-header">
      <span class="material-symbols-outlined" aria-hidden="true">monitoring</span>
      <h3>Usage this month</h3>
    </div>

    <CardSkeleton v-if="loading" variant="stats" :count="4" />
    <p v-else-if="error" class="text-sm text-stone-500">{{ error }}</p>
    <div v-else-if="stats" class="staff-stat-grid staff-fade-in">
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
import CardSkeleton from './CardSkeleton.vue'

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
