<template>
  <div class="inline-flex items-center relative group">
    <slot />
    <button
      type="button"
      class="ml-2 inline-flex items-center justify-center w-6 h-6 rounded-full bg-blue-100 text-blue-700 hover:bg-blue-200 text-xs font-bold transition-all cursor-help"
      @mouseenter="show"
      @mouseleave="hide"
      @click="toggle"
    >
      ?
    </button>
    <Transition
      enter-active-class="transition ease-out duration-200"
      enter-from-class="opacity-0 scale-95"
      enter-to-class="opacity-100 scale-100"
      leave-active-class="transition ease-in duration-150"
      leave-from-class="opacity-100 scale-100"
      leave-to-class="opacity-0 scale-95"
    >
      <div
        v-if="visible"
        :class="[
          'absolute z-50 px-3 py-2 text-sm text-white bg-slate-900 rounded-lg shadow-xl max-w-xs',
          positionClass
        ]"
        role="tooltip"
      >
        {{ text }}
        <div :class="arrowClass"></div>
      </div>
    </Transition>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'

const props = defineProps<{
  text: string
  position?: 'top' | 'bottom' | 'left' | 'right'
}>()

const visible = ref(false)
let hideTimeout: number | null = null

function show() {
  if (hideTimeout) {
    clearTimeout(hideTimeout)
    hideTimeout = null
  }
  visible.value = true
}

function hide() {
  hideTimeout = window.setTimeout(() => {
    visible.value = false
  }, 150)
}

function toggle() {
  visible.value = !visible.value
}

const positionClass = computed(() => {
  switch (props.position || 'top') {
    case 'bottom':
      return 'top-full mt-2 left-1/2 -translate-x-1/2'
    case 'left':
      return 'right-full mr-2 top-1/2 -translate-y-1/2'
    case 'right':
      return 'left-full ml-2 top-1/2 -translate-y-1/2'
    default: // 'top'
      return 'bottom-full mb-2 left-1/2 -translate-x-1/2'
  }
})

const arrowClass = computed(() => {
  const base = 'absolute w-2 h-2 bg-slate-900 transform rotate-45'
  switch (props.position || 'top') {
    case 'bottom':
      return `${base} -top-1 left-1/2 -translate-x-1/2`
    case 'left':
      return `${base} -right-1 top-1/2 -translate-y-1/2`
    case 'right':
      return `${base} -left-1 top-1/2 -translate-y-1/2`
    default: // 'top'
      return `${base} -bottom-1 left-1/2 -translate-x-1/2`
  }
})
</script>
