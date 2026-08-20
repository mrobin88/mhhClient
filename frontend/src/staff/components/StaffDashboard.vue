<template>
  <div class="space-y-4">
    <DashboardHeader :user="user" />

    <div class="staff-dashboard-layout">
      <div class="staff-dashboard-grid">
        <UsageStatsCard />
        <RecentClientsCard />
        <NewPitStopApplicationsCard />
        <UpcomingClassesCard />
        <ProgramDistributionChart />
        <ActivityFeedCard />
        <FeedbackCard />
        <DocumentUploadCard />
      </div>

      <div class="staff-dashboard-sidebar">
        <RouterLink :to="{ name: 'ClientCreate' }" class="staff-btn staff-btn-primary w-full">
          <span class="material-symbols-outlined" aria-hidden="true">person_add</span>
          Add a client
        </RouterLink>
        <ClientSearchPanel />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { staffFetch } from '../api'
import type { StaffUser } from '../types'
import DashboardHeader from './dashboard/DashboardHeader.vue'
import UsageStatsCard from './dashboard/UsageStatsCard.vue'
import RecentClientsCard from './dashboard/RecentClientsCard.vue'
import NewPitStopApplicationsCard from './dashboard/NewPitStopApplicationsCard.vue'
import UpcomingClassesCard from './dashboard/UpcomingClassesCard.vue'
import ProgramDistributionChart from './dashboard/ProgramDistributionChart.vue'
import ActivityFeedCard from './dashboard/ActivityFeedCard.vue'
import FeedbackCard from './dashboard/FeedbackCard.vue'
import DocumentUploadCard from './dashboard/DocumentUploadCard.vue'
import ClientSearchPanel from './dashboard/ClientSearchPanel.vue'

const user = ref<StaffUser | null>(null)

async function loadUser() {
  try {
    const resp = await staffFetch('/api/staff/session/')
    if (!resp.ok) return
    const body = await resp.json()
    if (body?.authenticated) user.value = body.user
  } catch {
    /* header falls back to generic greeting */
  }
}

onMounted(loadUser)
</script>
