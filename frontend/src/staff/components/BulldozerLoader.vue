<template>
  <div class="py-8 px-4 text-center" role="status" aria-live="polite">
    <p class="text-3xl mb-3" aria-hidden="true">🚜</p>
    <p class="text-sm font-semibold text-stone-600 mb-3">{{ label }}</p>
    <div class="staff-bulldozer-track max-w-xs mx-auto">
      <div class="staff-bulldozer-bar" />
    </div>
  </div>
</template>

<script setup lang="ts">
withDefaults(defineProps<{ label?: string }>(), { label: 'Loading…' })
</script>
