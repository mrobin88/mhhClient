<template>
  <div class="staff-toast-stack" aria-live="polite">
    <div
      v-for="t in toasts"
      :key="t.id"
      class="staff-toast"
      :class="`staff-toast-${t.kind}`"
    >
      {{ t.message }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { useToast } from '../composables/useToast'

const { toasts } = useToast()
</script>
