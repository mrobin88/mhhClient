<template>
  <div class="staff-app">
    <ToastStack />
    <header
      v-if="showChrome"
      class="sticky top-0 z-40 bg-white border-b border-stone-200 px-4 py-3 flex items-center justify-between"
    >
      <div class="flex items-center gap-2 min-w-0">
        <span class="material-symbols-outlined text-orange-600" aria-hidden="true">badge</span>
        <div class="min-w-0">
          <p class="text-[10px] uppercase tracking-wider text-stone-500 font-semibold">MHH Staff</p>
          <p class="font-bold text-sm truncate">{{ user?.display_name }}</p>
        </div>
      </div>
      <button type="button" class="staff-btn staff-btn-ghost shrink-0" @click="logout">
        <span class="material-symbols-outlined" style="font-size: 18px;" aria-hidden="true">logout</span>
        Sign out
      </button>
    </header>

    <main :class="mainClass">
      <slot />
    </main>

    <nav v-if="showChrome" class="staff-nav">
      <RouterLink to="/dashboard">
        <span class="material-symbols-outlined" aria-hidden="true">dashboard</span>
        <span class="staff-nav-label">Dashboard</span>
        <StaffTip text="Home screen: recent clients, upcoming classes, search, and quick tools." />
      </RouterLink>
      <RouterLink to="/clients">
        <span class="material-symbols-outlined" aria-hidden="true">group</span>
        <span class="staff-nav-label">Clients</span>
        <StaffTip text="Find a person, open their page, update info, and sign them up for classes." />
      </RouterLink>
      <RouterLink to="/messages">
        <span class="material-symbols-outlined" aria-hidden="true">chat</span>
        <span class="staff-nav-label">Messages</span>
        <span v-if="unreadCount > 0" class="staff-nav-badge">{{ unreadCount }}</span>
        <StaffTip text="Text message threads with clients. The badge shows unread replies." />
      </RouterLink>
      <RouterLink to="/classes">
        <span class="material-symbols-outlined" aria-hidden="true">event</span>
        <span class="staff-nav-label">Classes</span>
        <StaffTip text="Create Orientation, JRT, and workshops. Set weekly/monthly schedules and mark attendance." />
      </RouterLink>
      <RouterLink to="/tickets">
        <span class="material-symbols-outlined" aria-hidden="true">confirmation_number</span>
        <span class="staff-nav-label">Tickets</span>
        <StaffTip text="Report bugs with screenshots, set urgency, and track what’s fixed." />
      </RouterLink>
      <RouterLink to="/create-skill">
        <span class="material-symbols-outlined" aria-hidden="true">school</span>
        <span class="staff-nav-label">Skill note</span>
        <StaffTip text="Log a skill or training note for a client when they complete something." />
      </RouterLink>
    </nav>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { clearStaffSession, staffFetch } from '../api'
import ToastStack from './ToastStack.vue'
import StaffTip from './StaffTip.vue'

import type { StaffUser } from '../types'

const props = defineProps<{
  user: StaffUser | null
}>()

const emit = defineEmits<{ (e: 'logout'): void }>()

const route = useRoute()
const router = useRouter()
const unreadCount = ref(0)
let pollTimer: ReturnType<typeof setInterval> | null = null

const showChrome = computed(() => {
  const guest = ['Login', 'ForgotPassword', 'ResetPassword']
  return Boolean(props.user) && !guest.includes(String(route.name))
})

const mainClass = computed(() => {
  if (!showChrome.value) return 'min-h-screen'
  const widthClass = ['Dashboard', 'Classes', 'ClientDetail', 'Tickets', 'TicketDetail', 'Messages'].includes(
    String(route.name),
  )
    ? 'staff-main-wide'
    : 'max-w-lg'
  return `staff-main-pad ${widthClass} mx-auto p-4`
})

async function refreshUnread() {
  if (!props.user) {
    unreadCount.value = 0
    return
  }
  try {
    const resp = await staffFetch('/api/staff/messages/unread-count/')
    if (resp.ok) {
      const body = await resp.json()
      unreadCount.value = Number(body.count) || 0
    }
  } catch {
    /* ignore badge errors */
  }
}

async function logout() {
  await staffFetch('/api/staff/logout/', { method: 'POST' })
  clearStaffSession()
  emit('logout')
  router.push({ name: 'Login' })
}

watch(
  () => props.user,
  (u) => {
    if (pollTimer) clearInterval(pollTimer)
    if (u) {
      refreshUnread()
      pollTimer = setInterval(refreshUnread, 30_000)
    }
  },
  { immediate: true },
)

onMounted(refreshUnread)
onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
})
</script>
