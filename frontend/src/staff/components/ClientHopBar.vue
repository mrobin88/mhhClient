<template>
  <div class="staff-client-hop">
    <RouterLink
      :to="{ name: 'ClientDetail', params: { id: clientId } }"
      class="staff-client-hop-name"
      :class="{ 'staff-client-hop-current': active === 'profile' }"
    >
      <span class="material-symbols-outlined" aria-hidden="true">person</span>
      <span class="truncate">{{ clientName }}</span>
      <span class="staff-client-hop-main-label">Main page</span>
    </RouterLink>

    <div class="staff-client-hop-links" aria-label="Other places for this client">
      <RouterLink
        v-for="link in links"
        :key="link.key"
        :to="link.to"
        class="staff-client-hop-chip"
        :class="{ 'staff-client-hop-chip-active': active === link.key }"
      >
        {{ link.label }}
      </RouterLink>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink } from 'vue-router'

const props = defineProps<{
  clientId: number
  clientName: string
  /** Which hop the user is currently on */
  active?: 'profile' | 'notes' | 'messages' | 'classes' | 'skill'
}>()

const links = computed(() => [
  {
    key: 'notes' as const,
    label: 'Notes',
    to: { name: 'ClientDetail', params: { id: props.clientId }, query: { focus: 'notes' } },
  },
  {
    key: 'classes' as const,
    label: 'Classes',
    to: { name: 'ClientDetail', params: { id: props.clientId }, query: { focus: 'classes' } },
  },
  {
    key: 'messages' as const,
    label: 'Messages',
    to: { name: 'Messages', query: { client: String(props.clientId) } },
  },
  {
    key: 'skill' as const,
    label: 'Skill note',
    to: { name: 'CreateSkill', query: { client: String(props.clientId) } },
  },
])
</script>
