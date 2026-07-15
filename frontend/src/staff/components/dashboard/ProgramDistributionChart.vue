<template>
  <section class="staff-card p-4">
    <div class="staff-panel-header">
      <span class="material-symbols-outlined" aria-hidden="true">donut_large</span>
      <h3>Clients by program</h3>
    </div>

    <CardSkeleton v-if="loading" variant="block" block-height="220px" />
    <p v-else-if="error" class="text-sm text-stone-500">{{ error }}</p>
    <p v-else-if="rows.length === 0" class="text-sm text-stone-500">No client data yet.</p>
    <div v-else class="relative staff-fade-in" style="height: 220px;">
      <canvas ref="canvasEl" role="img" aria-label="Clients grouped by program"></canvas>
    </div>
  </section>
</template>

<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { Chart, type ChartConfiguration } from 'chart.js/auto'
import { staffFetch } from '../../api'
import CardSkeleton from './CardSkeleton.vue'

interface ProgramRow {
  program: string
  program_display: string
  count: number
}

const rows = ref<ProgramRow[]>([])
const loading = ref(true)
const error = ref('')
const canvasEl = ref<HTMLCanvasElement | null>(null)
let chartInstance: Chart | null = null

const PALETTE = ['#ea580c', '#0f766e', '#7c3aed', '#0369a1', '#b45309', '#4d7c0f']

function renderChart(categoryCount: number) {
  if (!canvasEl.value) return
  if (chartInstance) {
    chartInstance.destroy()
    chartInstance = null
  }

  const kind = categoryCount <= 5 ? 'pie' : 'bar'
  const config: ChartConfiguration = {
    type: kind,
    data: {
      labels: rows.value.map((r) => r.program_display),
      datasets: [
        {
          label: 'Clients',
          data: rows.value.map((r) => r.count),
          backgroundColor: rows.value.map((_, i) => PALETTE[i % PALETTE.length]),
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { position: kind === 'pie' ? 'bottom' : undefined, display: true },
      },
      scales:
        kind === 'bar'
          ? { y: { beginAtZero: true, ticks: { precision: 0 } } }
          : undefined,
    },
  }
  chartInstance = new Chart(canvasEl.value, config)
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const resp = await staffFetch('/api/staff/dashboard/program-distribution/')
    if (!resp.ok) {
      error.value = 'Could not load program distribution.'
      return
    }
    const body = await resp.json()
    rows.value = body.results || []
    await nextTick()
    if (rows.value.length > 0) renderChart(body.category_count ?? rows.value.length)
  } catch {
    error.value = 'No connection.'
  } finally {
    loading.value = false
  }
}

onMounted(load)
onBeforeUnmount(() => {
  chartInstance?.destroy()
})
</script>
