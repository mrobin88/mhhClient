<template>
  <div class="staff-app">
    <ToastStack />
    <header
      v-if="showChrome"
      class="sticky top-0 z-40 bg-white border-b border-stone-200 px-4 py-3 flex items-center justify-between"
    >
      <div class="flex items-center gap-2 min-w-0">
        <span class="text-xl" aria-hidden="true">⛑️</span>
        <div class="min-w-0">
          <p class="text-[10px] uppercase tracking-wider text-stone-500 font-semibold">Mission Hiring Hall</p>
          <p class="font-bold text-sm truncate">{{ user?.display_name }}</p>
        </div>
      </div>
      <button type="button" class="text-sm font-semibold text-stone-600 shrink-0" @click="logout">
        Sign out
      </button>
    </header>

    <main :class="showChrome ? 'staff-main-pad max-w-lg mx-auto p-4' : 'min-h-screen'">
      <slot />
    </main>

    <nav v-if="showChrome" class="staff-nav">
      <RouterLink to="/clients">Clients</RouterLink>
      <RouterLink to="/messages">
        Messages
        <span v-if="unreadCount > 0" class="staff-nav-badge">{{ unreadCount }}</span>
      </RouterLink>
      <RouterLink to="/create-skill">Skill note</RouterLink>
    </nav>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { clearStaffSession, staffFetch } from '../api'
import ToastStack from './ToastStack.vue'

export interface StaffUser {
  id: number
  username: string
  display_name: string
  role: string
}

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
