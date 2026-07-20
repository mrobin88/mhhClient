<template>
  <span ref="rootEl" class="staff-tip" :class="{ 'staff-tip-open': open }">
    <button
      ref="btnEl"
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
    <Teleport to="body">
      <span
        v-show="open"
        class="staff-tip-bubble staff-tip-bubble-portal"
        role="tooltip"
        :style="bubbleStyle"
        @mouseenter="openOnHover"
        @mouseleave="closeOnHover"
      >
        {{ text }}
      </span>
    </Teleport>
  </span>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'

defineProps<{
  text: string
  label?: string
}>()

const open = ref(false)
const btnEl = ref<HTMLButtonElement | null>(null)
const rootEl = ref<HTMLElement | null>(null)
const coords = ref({ top: 0, left: 0, placeBelow: true })
let hoverMode = false

const bubbleStyle = computed(() => {
  const { top, left, placeBelow } = coords.value
  return {
    top: `${top}px`,
    left: `${left}px`,
    transform: placeBelow ? 'translate(-50%, 0)' : 'translate(-50%, -100%)',
  }
})

function measure() {
  const btn = btnEl.value
  if (!btn) return
  const rect = btn.getBoundingClientRect()
  const placeBelow = rect.top < 120
  const gap = 8
  coords.value = {
    left: rect.left + rect.width / 2,
    top: placeBelow ? rect.bottom + gap : rect.top - gap,
    placeBelow,
  }
}

async function show() {
  open.value = true
  await nextTick()
  measure()
}

function openOnHover() {
  hoverMode = true
  void show()
}

function closeOnHover() {
  if (hoverMode) {
    hoverMode = false
    open.value = false
  }
}

function toggle() {
  hoverMode = false
  if (open.value) {
    open.value = false
  } else {
    void show()
  }
}

function onDocClick(e: MouseEvent) {
  if (!open.value) return
  const target = e.target as HTMLElement | null
  if (target?.closest('.staff-tip') || target?.closest('.staff-tip-bubble-portal')) return
  open.value = false
}

function onScrollOrResize() {
  if (open.value) measure()
}

watch(open, (v) => {
  if (v) measure()
})

onMounted(() => {
  document.addEventListener('click', onDocClick)
  window.addEventListener('scroll', onScrollOrResize, true)
  window.addEventListener('resize', onScrollOrResize)
})
onBeforeUnmount(() => {
  document.removeEventListener('click', onDocClick)
  window.removeEventListener('scroll', onScrollOrResize, true)
  window.removeEventListener('resize', onScrollOrResize)
})
</script>
