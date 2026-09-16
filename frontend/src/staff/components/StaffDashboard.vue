<template>
  <div class="space-y-4">
    <DashboardHeader :user="user" />

    <ClientSearchPanel />

    <div class="staff-home-actions">
      <RouterLink :to="{ name: 'ClientCreate' }" class="staff-btn staff-btn-primary">
        <span class="material-symbols-outlined" aria-hidden="true">person_add</span>
        Add a client
      </RouterLink>
      <RouterLink :to="{ name: 'Classes' }" class="staff-btn staff-btn-secondary">
        <span class="material-symbols-outlined" aria-hidden="true">event</span>
        Classes
      </RouterLink>
    </div>

    <div class="staff-dashboard-grid">
      <UpcomingClassesCard />
      <RecentClientsCard />
      <NewPitStopApplicationsCard />
      <NewCityBuildInterestCard />
      <DocumentUploadCard />
    </div>

    <ColorThemePicker />
  </div>
</template>

<script setup lang="ts">
import { inject, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { staffUserKey } from '../staffContext'
import type { StaffUser } from '../types'
import DashboardHeader from './dashboard/DashboardHeader.vue'
import RecentClientsCard from './dashboard/RecentClientsCard.vue'
import NewPitStopApplicationsCard from './dashboard/NewPitStopApplicationsCard.vue'
import NewCityBuildInterestCard from './dashboard/NewCityBuildInterestCard.vue'
import UpcomingClassesCard from './dashboard/UpcomingClassesCard.vue'
import DocumentUploadCard from './dashboard/DocumentUploadCard.vue'
import ClientSearchPanel from './dashboard/ClientSearchPanel.vue'
import ColorThemePicker from './dashboard/ColorThemePicker.vue'

const user = inject(staffUserKey, ref<StaffUser | null>(null))
</script>
