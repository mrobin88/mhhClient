<template>
  <StaffShell :user="user" @logout="onLogout">
    <RouterView @logged-in="onLoggedIn" />
  </StaffShell>
</template>

<script setup lang="ts">
import { onMounted, provide, ref } from 'vue'
import { useRouter } from 'vue-router'
import { clearStaffSession, setSessionExpiredHandler, staffFetch } from './api'
import StaffShell from './components/StaffShell.vue'
import { setStaffUserKey, staffUserKey } from './staffContext'
import type { StaffUser } from './types'

const router = useRouter()
const user = ref<StaffUser | null>(null)

function setStaffUser(next: StaffUser | null) {
  user.value = next
}

provide(staffUserKey, user)
provide(setStaffUserKey, setStaffUser)

function onLoggedIn(loggedInUser: StaffUser) {
  setStaffUser(loggedInUser)
}

async function loadSession() {
  const resp = await staffFetch('/api/staff/session/')
  const body = await resp.json().catch(() => null)
  if (!resp.ok || !body?.authenticated) {
    setStaffUser(null)
    return false
  }
  setStaffUser(body.user)
  return true
}

function onLogout() {
  setStaffUser(null)
}

// A session can lapse while someone sits on a page, so the first thing they
// hear about it is a failed save. Take them to sign-in and back to their work.
setSessionExpiredHandler(() => {
  const current = router.currentRoute.value
  if (current.meta.guest) return
  setStaffUser(null)
  clearStaffSession()
  router.replace({ name: 'Login', query: { redirect: current.fullPath, expired: '1' } })
})

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
