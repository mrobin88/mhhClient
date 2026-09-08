<template>
  <div
    class="staff-dash-module"
    :class="{
      'is-collapsed': collapsed,
      'is-dragging': dragging,
      'is-drop-target': dropTarget,
      'is-reorderable': reorderable,
    }"
    @dragover.prevent="onDragOver"
    @drop.prevent="onDrop"
  >
    <div v-if="reorderable" class="staff-dash-tools">
      <span
        class="staff-collapse-btn staff-drag-handle"
        title="Drag to rearrange"
        aria-label="Drag to rearrange this card"
        draggable="true"
        @dragstart="onDragStart"
        @dragend="$emit('drag-end')"
      >
        <span class="material-symbols-outlined" aria-hidden="true">drag_indicator</span>
      </span>
      <button
        type="button"
        class="staff-collapse-btn"
        :disabled="!canMovePrev"
        title="Move earlier"
        aria-label="Move this card earlier"
        @click="$emit('move', id, -1)"
      >
        <span class="material-symbols-outlined" aria-hidden="true">arrow_upward</span>
      </button>
      <button
        type="button"
        class="staff-collapse-btn"
        :disabled="!canMoveNext"
        title="Move later"
        aria-label="Move this card later"
        @click="$emit('move', id, 1)"
      >
        <span class="material-symbols-outlined" aria-hidden="true">arrow_downward</span>
      </button>
      <button
        type="button"
        class="staff-collapse-btn"
        :aria-expanded="!collapsed"
        :title="collapsed ? 'Show this card' : 'Minimize this card'"
        :aria-label="collapsed ? 'Show this card' : 'Minimize this card'"
        @click="toggle"
      >
        <span class="material-symbols-outlined" aria-hidden="true">
          {{ collapsed ? 'expand_more' : 'expand_less' }}
        </span>
      </button>
    </div>
    <button
      v-else
      type="button"
      class="staff-collapse-btn"
      :aria-expanded="!collapsed"
      :title="collapsed ? 'Show this card' : 'Minimize this card'"
      :aria-label="collapsed ? 'Show this card' : 'Minimize this card'"
      @click="toggle"
    >
      <span class="material-symbols-outlined" aria-hidden="true">
        {{ collapsed ? 'expand_more' : 'expand_less' }}
      </span>
    </button>
    <slot />
  </div>
</template>

<script setup lang="ts">
import { computed, inject, ref } from 'vue'
import { saveStaffPrefsKey, staffUserKey } from '../../staffContext'
import type { StaffUser } from '../../types'

const props = defineProps<{
  id: string
  canMovePrev?: boolean
  canMoveNext?: boolean
  dragging?: boolean
  dropTarget?: boolean
  reorderable?: boolean
}>()

const emit = defineEmits<{
  move: [id: string, dir: -1 | 1]
  'drag-start': [id: string, event: DragEvent]
  'drag-end': []
  drop: [id: string, event: DragEvent]
  'drag-over': [id: string]
}>()

const user = inject(staffUserKey, ref<StaffUser | null>(null))
const saveStaffPrefs = inject(saveStaffPrefsKey)

const collapsed = computed(() => {
  const ids = user.value?.dashboard_collapsed
  return Array.isArray(ids) && ids.includes(props.id)
})

async function toggle() {
  const current = Array.isArray(user.value?.dashboard_collapsed)
    ? [...user.value.dashboard_collapsed]
    : []
  const next = collapsed.value
    ? current.filter((id) => id !== props.id)
    : [...current.filter((id) => id !== props.id), props.id]
  if (saveStaffPrefs) await saveStaffPrefs({ dashboard_collapsed: next })
}

function onDragStart(event: DragEvent) {
  emit('drag-start', props.id, event)
}

function onDragOver() {
  emit('drag-over', props.id)
}

function onDrop(event: DragEvent) {
  emit('drop', props.id, event)
}
</script>
