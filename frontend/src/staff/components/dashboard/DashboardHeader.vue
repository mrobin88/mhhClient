<template>
  <RouterLink
    to="/dashboard"
    class="staff-dashboard-greeting block no-underline"
    title="Go to staff home"
  >
    <p class="text-xs uppercase tracking-wider opacity-80 font-semibold">{{ greetingWord }}</p>
    <p class="text-xl font-bold">{{ user?.display_name || 'Staff' }}</p>
    <p class="text-sm opacity-90 mt-1">Mission Hiring Hall staff home</p>
  </RouterLink>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import type { StaffUser } from '../../types'

defineProps<{ user: StaffUser | null }>()

const greetingWord = computed(() => {
  const hour = new Date().getHours()
  if (hour < 12) return 'Good morning'
  if (hour < 18) return 'Good afternoon'
  return 'Good evening'
})
</script>
