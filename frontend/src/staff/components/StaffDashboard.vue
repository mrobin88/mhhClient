<template>
  <div class="space-y-4">
    <DashboardHeader :user="user" />

    <div class="staff-layout-bar">
      <p>Drag a card or use the arrows to arrange your home screen. Saved to your account.</p>
      <button
        v-if="canResetOrder"
        type="button"
        class="staff-link text-xs font-semibold"
        @click="resetOrder"
      >
        Reset layout
      </button>
    </div>

    <div class="staff-dashboard-layout">
      <div class="staff-dashboard-grid">
        <DashboardModule
          v-for="id in orderedIds"
          :key="id"
          :id="id"
          reorderable
          :can-move-prev="canMove(id, -1)"
          :can-move-next="canMove(id, 1)"
          :dragging="draggingId === id"
          :drop-target="dropTargetId === id"
          @move="move"
          @drag-start="onDragStart"
          @drag-over="dropTargetId = $event"
          @drag-end="clearDrag"
          @drop="onDrop"
        >
          <component :is="gridModules[id as keyof typeof gridModules]" />
        </DashboardModule>
      </div>

      <div class="staff-dashboard-sidebar">
        <RouterLink :to="{ name: 'ClientCreate' }" class="staff-btn staff-btn-primary w-full">
          <span class="material-symbols-outlined" aria-hidden="true">person_add</span>
          Add a client
        </RouterLink>
        <ColorThemePicker />
        <DashboardModule id="search">
          <ClientSearchPanel />
        </DashboardModule>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, inject, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { staffUserKey, saveStaffPrefsKey } from '../staffContext'
import type { StaffUser } from '../types'
import {
  DEFAULT_DASHBOARD_ORDER,
  normalizeDashboardOrder,
  ordersMatch,
} from '../dashboardLayout'
import DashboardHeader from './dashboard/DashboardHeader.vue'
import DashboardModule from './dashboard/DashboardModule.vue'
import UsageStatsCard from './dashboard/UsageStatsCard.vue'
import RecentClientsCard from './dashboard/RecentClientsCard.vue'
import NewPitStopApplicationsCard from './dashboard/NewPitStopApplicationsCard.vue'
import NewCityBuildInterestCard from './dashboard/NewCityBuildInterestCard.vue'
import UpcomingClassesCard from './dashboard/UpcomingClassesCard.vue'
import ProgramDistributionChart from './dashboard/ProgramDistributionChart.vue'
import ActivityFeedCard from './dashboard/ActivityFeedCard.vue'
import FeedbackCard from './dashboard/FeedbackCard.vue'
import DocumentUploadCard from './dashboard/DocumentUploadCard.vue'
import ClientSearchPanel from './dashboard/ClientSearchPanel.vue'
import ColorThemePicker from './dashboard/ColorThemePicker.vue'

const user = inject(staffUserKey, ref<StaffUser | null>(null))
const saveStaffPrefs = inject(saveStaffPrefsKey)
const draggingId = ref('')
const dropTargetId = ref('')

const gridModules = {
  usage: UsageStatsCard,
  'recent-clients': RecentClientsCard,
  pitstop: NewPitStopApplicationsCard,
  citybuild: NewCityBuildInterestCard,
  classes: UpcomingClassesCard,
  programs: ProgramDistributionChart,
  activity: ActivityFeedCard,
  tickets: FeedbackCard,
  documents: DocumentUploadCard,
} as const

const orderedIds = computed(() => normalizeDashboardOrder(user.value?.dashboard_order))
const canResetOrder = computed(() => !ordersMatch(orderedIds.value, DEFAULT_DASHBOARD_ORDER))

function canMove(id: string, dir: -1 | 1) {
  const index = orderedIds.value.indexOf(id)
  const next = index + dir
  return index >= 0 && next >= 0 && next < orderedIds.value.length
}

async function saveOrder(next: string[]) {
  if (saveStaffPrefs) await saveStaffPrefs({ dashboard_order: next })
}

async function move(id: string, dir: -1 | 1) {
  if (!canMove(id, dir)) return
  const next = [...orderedIds.value]
  const index = next.indexOf(id)
  const swap = index + dir
  ;[next[index], next[swap]] = [next[swap], next[index]]
  await saveOrder(next)
}

function onDragStart(id: string, event: DragEvent) {
  draggingId.value = id
  dropTargetId.value = id
  event.dataTransfer?.setData('text/plain', id)
  if (event.dataTransfer) event.dataTransfer.effectAllowed = 'move'
}

function clearDrag() {
  draggingId.value = ''
  dropTargetId.value = ''
}

async function onDrop(targetId: string, event: DragEvent) {
  const fromId = event.dataTransfer?.getData('text/plain') || draggingId.value
  clearDrag()
  if (!fromId || fromId === targetId) return
  const next = [...orderedIds.value]
  const from = next.indexOf(fromId)
  const to = next.indexOf(targetId)
  if (from < 0 || to < 0) return
  next.splice(from, 1)
  next.splice(to, 0, fromId)
  await saveOrder(next)
}

async function resetOrder() {
  await saveOrder([...DEFAULT_DASHBOARD_ORDER])
}
</script>
