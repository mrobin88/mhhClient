<template>
  <span class="staff-tip" :class="{ 'staff-tip-open': open }">
    <button
      type="button"
      class="staff-tip-btn"
      :aria-label="label || 'What is this?'"
      :aria-expanded="open"
      @click.stop="toggle"
      @mouseenter="openOnHover"
      @mouseleave="closeOnHover"
      @focus="openOnHover"
      @blur="closeOnHover"
    >
      ?
    </button>
    <span
      v-show="open"
      class="staff-tip-bubble"
      role="tooltip"
      @mouseenter="openOnHover"
      @mouseleave="closeOnHover"
    >
      {{ text }}
    </span>
  </span>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'

defineProps<{
  text: string
  label?: string
}>()

const open = ref(false)
let hoverMode = false

function openOnHover() {
  hoverMode = true
  open.value = true
}

function closeOnHover() {
  if (hoverMode) {
    hoverMode = false
    open.value = false
  }
}

function toggle() {
  hoverMode = false
  open.value = !open.value
}

function onDocClick(e: MouseEvent) {
  if (!open.value) return
  const target = e.target as HTMLElement | null
  if (target?.closest('.staff-tip')) return
  open.value = false
}

onMounted(() => document.addEventListener('click', onDocClick))
onBeforeUnmount(() => document.removeEventListener('click', onDocClick))
</script>
