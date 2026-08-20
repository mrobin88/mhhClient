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
import { saveStaffPrefsKey, setStaffUserKey, staffUserKey, type StaffPrefsPatch } from './staffContext'
import { hydrateStaffUser, writeLocalPrefs } from './prefs'
import { normalizeHex } from './theme'
import type { StaffUser } from './types'

const router = useRouter()
const user = ref<StaffUser | null>(null)

function setStaffUser(next: StaffUser | null) {
  user.value = next
}

async function saveStaffPrefs(patch: StaffPrefsPatch, options: { persist?: boolean } = {}): Promise<boolean> {
  const current = user.value
  if (!current) return false
  const next: StaffUser = { ...current, ...patch }
  setStaffUser(next)
  writeLocalPrefs(current.id, {
    accent_color: next.accent_color,
    dashboard_collapsed: next.dashboard_collapsed,
  })
  if (options.persist === false) return true

  try {
    const resp = await staffFetch('/api/staff/profile/', {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(patch),
    })
    const body = await resp.json().catch(() => null)
    if (!resp.ok) return false
    if (body?.user) {
      const saved = hydrateStaffUser(body.user)
      setStaffUser(saved)
    }
    return true
  } catch {
    return false
  }
}

provide(staffUserKey, user)
provide(setStaffUserKey, setStaffUser)
provide(saveStaffPrefsKey, saveStaffPrefs)

function onLoggedIn(loggedInUser: StaffUser) {
  setStaffUser(hydrateStaffUser(loggedInUser))
}

async function loadSession() {
  const resp = await staffFetch('/api/staff/session/')
  const body = await resp.json().catch(() => null)
  if (!resp.ok || !body?.authenticated) {
    setStaffUser(null)
    return false
  }
  const hydrated = hydrateStaffUser(body.user)
  setStaffUser(hydrated)
  const serverColor = normalizeHex(body.user?.accent_color)
  if (hydrated.accent_color && hydrated.accent_color !== serverColor) {
    void saveStaffPrefs({ accent_color: hydrated.accent_color })
  }
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
