<template>
  <div class="staff-dash-module" :class="{ 'is-collapsed': collapsed }">
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
    <slot />
  </div>
</template>

<script setup lang="ts">
import { computed, inject, ref } from 'vue'
import { saveStaffPrefsKey, staffUserKey } from '../../staffContext'
import type { StaffUser } from '../../types'

const props = defineProps<{
  id: string
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
</script>
