<template>
  <StaffShell :user="user" @logout="onLogout">
    <RouterView @logged-in="onLoggedIn" />
  </StaffShell>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { staffFetch } from './api'
import StaffShell from './components/StaffShell.vue'
import type { StaffUser } from './types'

const router = useRouter()
const user = ref<StaffUser | null>(null)

function onLoggedIn(loggedInUser: StaffUser) {
  user.value = loggedInUser
}

async function loadSession() {
  const resp = await staffFetch('/api/staff/session/')
  const body = await resp.json().catch(() => null)
  if (!resp.ok || !body?.authenticated) {
    user.value = null
    return false
  }
  user.value = body.user
  return true
}

function onLogout() {
  user.value = null
}

onMounted(async () => {
  const authed = await loadSession()
  const guest = router.currentRoute.value.meta.guest
  if (!authed && !guest) {
    router.replace({ name: 'Login' })
  }
})

router.beforeEach(async (to) => {
  if (to.meta.guest) return true
  if (user.value) return true
  const authed = await loadSession()
  if (authed) return true
  return { name: 'Login', query: { redirect: to.fullPath } }
})
</script>
