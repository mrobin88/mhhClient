<template>
  <StaffShell :user="user" @logout="onLogout">
    <RouterView @logged-in="loadSession" />
  </StaffShell>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { staffFetch } from './api'
import StaffShell, { type StaffUser } from './components/StaffShell.vue'

const router = useRouter()
const user = ref<StaffUser | null>(null)

async function loadSession() {
  const resp = await staffFetch('/api/staff/session/')
  if (!resp.ok) {
    user.value = null
    return false
  }
  const body = await resp.json()
  user.value = body.authenticated ? body.user : null
  return Boolean(user.value)
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
