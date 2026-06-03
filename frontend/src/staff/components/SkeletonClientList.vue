<template>
  <ul class="space-y-2">
    <li v-for="n in count" :key="n" class="staff-card p-4 space-y-2">
      <div class="staff-skeleton h-5 w-2/3" />
      <div class="staff-skeleton h-4 w-1/2" />
    </li>
  </ul>
</template>

<script setup lang="ts">
withDefaults(defineProps<{ count?: number }>(), { count: 5 })
</script>
