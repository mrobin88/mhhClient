<template>
  <div v-if="variant === 'stats'" class="staff-stat-grid" aria-hidden="true">
    <div v-for="n in count" :key="n" class="staff-stat-tile">
      <div class="staff-skeleton h-6 w-12 mb-2" />
      <div class="staff-skeleton h-2.5 w-16" />
    </div>
  </div>

  <div
    v-else-if="variant === 'block'"
    class="staff-skeleton staff-skeleton-block"
    :style="{ height: blockHeight }"
    aria-hidden="true"
  />

  <ul v-else class="space-y-0" aria-hidden="true">
    <li v-for="n in count" :key="n" class="staff-skeleton-list-row">
      <span class="min-w-0 flex-1 space-y-1.5 py-1">
        <span class="staff-skeleton block h-3.5" :style="{ width: titleWidths[n % titleWidths.length] }" />
        <span class="staff-skeleton block h-2.5" :style="{ width: subWidths[n % subWidths.length] }" />
      </span>
      <span class="staff-skeleton h-4 w-11 rounded-full shrink-0" />
    </li>
  </ul>
</template>

<script setup lang="ts">
withDefaults(
  defineProps<{
    variant?: 'list' | 'stats' | 'block'
    count?: number
    blockHeight?: string
  }>(),
  { variant: 'list', count: 4, blockHeight: '220px' },
)

const titleWidths = ['72%', '55%', '82%', '62%']
const subWidths = ['46%', '38%', '52%', '35%']
</script>
