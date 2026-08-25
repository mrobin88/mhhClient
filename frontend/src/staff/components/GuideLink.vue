<template>
  <RouterLink v-if="link.to" :to="link.to" class="staff-guide-item-link">
    <span class="material-symbols-outlined" aria-hidden="true">arrow_forward</span>
    {{ link.label }}
  </RouterLink>
  <a
    v-else-if="link.href"
    :href="link.href"
    target="_blank"
    rel="noopener"
    class="staff-guide-item-link"
  >
    <span class="material-symbols-outlined" aria-hidden="true">open_in_new</span>
    {{ link.label }}
  </a>
</template>

<script setup lang="ts">
defineProps<{
  link: { label: string; to?: string; href?: string }
}>()
</script>
