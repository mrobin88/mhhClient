<template>
  <div class="min-h-screen bg-slate-100 text-slate-900">
    <header v-if="user" class="sticky top-0 z-10 bg-white border-b border-slate-200 px-4 py-3 flex items-center justify-between">
      <div>
        <p class="text-xs uppercase tracking-wide text-slate-500">Mission Hiring Hall</p>
        <p class="font-semibold text-sm">{{ user.display_name }}</p>
      </div>
      <button
        type="button"
        class="text-sm text-slate-600 underline"
        @click="logout"
      >
        Sign out
      </button>
    </header>

    <main class="max-w-lg mx-auto p-4">
      <StaffLogin v-if="!user" @logged-in="loadSession" />

      <template v-else>
        <StaffClientList
          v-if="!selectedClientId"
          @select="selectedClientId = $event"
        />
        <StaffClientDetail
          v-else
          :client-id="selectedClientId"
          @back="selectedClientId = null"
        />
      </template>
    </main>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { clearStaffSession, staffFetch } from './api'
import StaffLogin from './components/StaffLogin.vue'
import StaffClientList from './components/StaffClientList.vue'
import StaffClientDetail from './components/StaffClientDetail.vue'

interface StaffUser {
  id: number
  username: string
  display_name: string
  role: string
}

const user = ref<StaffUser | null>(null)
const selectedClientId = ref<number | null>(null)

async function loadSession() {
  const resp = await staffFetch('/api/staff/session/')
  if (!resp.ok) {
    user.value = null
    return
  }
  const body = await resp.json()
  user.value = body.authenticated ? body.user : null
}

async function logout() {
  await staffFetch('/api/staff/logout/', { method: 'POST' })
  clearStaffSession()
  user.value = null
  selectedClientId.value = null
}

onMounted(loadSession)
</script>
