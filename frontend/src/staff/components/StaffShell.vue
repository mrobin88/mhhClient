<template>
  <div class="staff-app" :style="themeStyle">
    <ToastStack />
    <header
      v-if="showChrome"
      class="sticky top-0 z-40 bg-white border-b border-stone-200 px-4 py-3 flex items-center justify-between"
    >
      <RouterLink
        to="/dashboard"
        class="staff-home-link flex items-center gap-2 min-w-0 rounded-lg pr-2 -ml-1 pl-1 py-0.5"
        title="Go to staff home"
      >
        <span class="material-symbols-outlined staff-accent-icon" aria-hidden="true">badge</span>
        <div class="min-w-0">
          <p class="text-[10px] uppercase tracking-wider text-stone-500 font-semibold">MHH Staff</p>
          <p class="font-bold text-sm truncate">{{ user?.display_name }}</p>
        </div>
      </RouterLink>
      <div class="flex items-center gap-1 shrink-0">
        <RouterLink to="/how-it-works" class="staff-btn staff-btn-ghost" title="How everything works">
          <span class="material-symbols-outlined" style="font-size: 18px;" aria-hidden="true">menu_book</span>
          Guide
        </RouterLink>
        <button type="button" class="staff-btn staff-btn-ghost" @click="logout">
          <span class="material-symbols-outlined" style="font-size: 18px;" aria-hidden="true">logout</span>
          Sign out
        </button>
      </div>
    </header>

    <main :class="mainClass">
      <slot />
    </main>

    <div
      v-if="showChrome && navOpen"
      class="staff-nav-backdrop"
      @click="navOpen = false"
    />

    <nav v-if="showChrome" class="staff-nav" :class="{ 'is-open': navOpen }">
      <button
        type="button"
        class="staff-nav-toggle"
        :aria-expanded="navOpen"
        aria-controls="staff-nav-panel"
        @click="navOpen = !navOpen"
      >
        <span class="material-symbols-outlined" aria-hidden="true">menu</span>
        <span class="staff-nav-toggle-copy">
          <span class="staff-nav-toggle-kicker">Menu</span>
          <span class="staff-nav-toggle-title">{{ currentSection }}</span>
        </span>
        <span v-if="unreadCount > 0" class="staff-nav-badge">{{ unreadCount }}</span>
        <span class="material-symbols-outlined staff-nav-chevron" aria-hidden="true">
          {{ navOpen ? 'expand_more' : 'expand_less' }}
        </span>
      </button>

      <div v-show="navOpen" id="staff-nav-panel" class="staff-nav-panel">
        <section v-for="group in navGroups" :key="group.title" class="staff-nav-group">
          <h3 class="staff-nav-group-title">{{ group.title }}</h3>
          <ul class="staff-nav-list">
            <li v-for="item in group.items" :key="item.label">
              <RouterLink
                v-if="item.to"
                :to="item.to"
                class="staff-nav-item"
                active-class=""
                exact-active-class=""
                :class="{ 'is-active': isItemActive(item) }"
                @click="navOpen = false"
              >
                <span class="material-symbols-outlined" aria-hidden="true">{{ item.icon }}</span>
                <span class="staff-nav-item-copy">
                  <span class="staff-nav-item-label">{{ item.label }}</span>
                  <span class="staff-nav-item-hint">{{ item.hint }}</span>
                </span>
                <span v-if="item.badge && unreadCount > 0" class="staff-nav-badge is-inline">
                  {{ unreadCount }}
                </span>
              </RouterLink>
              <a
                v-else-if="item.href"
                :href="item.href"
                class="staff-nav-item"
                :target="item.external ? '_blank' : undefined"
                :rel="item.external ? 'noopener' : undefined"
              >
                <span class="material-symbols-outlined" aria-hidden="true">{{ item.icon }}</span>
                <span class="staff-nav-item-copy">
                  <span class="staff-nav-item-label">{{ item.label }}</span>
                  <span class="staff-nav-item-hint">{{ item.hint }}</span>
                </span>
                <span
                  v-if="item.external"
                  class="material-symbols-outlined staff-nav-external"
                  aria-hidden="true"
                >open_in_new</span>
              </a>
            </li>
          </ul>
        </section>
      </div>
    </nav>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import type { RouteLocationRaw } from 'vue-router'
import { getApiUrl } from '../../config/api'
import { clearStaffSession, staffFetch } from '../api'
import { readLastAccent } from '../prefs'
import { accentThemeVars } from '../theme'
import ToastStack from './ToastStack.vue'

import type { StaffUser } from '../types'

interface NavItem {
  label: string
  hint: string
  icon: string
  to?: RouteLocationRaw
  href?: string
  external?: boolean
  badge?: boolean
  match?: string[]
  queryProgram?: string
}

const props = defineProps<{
  user: StaffUser | null
}>()

const emit = defineEmits<{ (e: 'logout'): void }>()

const route = useRoute()
const router = useRouter()
const unreadCount = ref(0)
const navOpen = ref(false)
let pollTimer: ReturnType<typeof setInterval> | null = null

const navGroups: { title: string; items: NavItem[] }[] = [
  {
    title: 'This workspace',
    items: [
      {
        label: 'Home',
        hint: 'New signups, classes, and search',
        icon: 'home',
        to: '/dashboard',
        match: ['Dashboard'],
      },
      {
        label: 'Clients',
        hint: 'Find someone and open their page',
        icon: 'group',
        to: '/clients',
        match: ['Clients', 'ClientDetail'],
      },
      {
        label: 'Add a client',
        hint: 'Outside referral, not public signup',
        icon: 'person_add',
        to: '/clients/new',
        match: ['ClientCreate'],
      },
      {
        label: 'Messages',
        hint: 'Text threads. Badge is unread replies',
        icon: 'chat',
        to: '/messages',
        match: ['Messages'],
        badge: true,
      },
      {
        label: 'Classes',
        hint: 'Orientation, JRT, attendance',
        icon: 'event',
        to: '/classes',
        match: ['Classes'],
      },
      {
        label: 'Tickets',
        hint: 'Bugs and change requests',
        icon: 'confirmation_number',
        to: '/tickets',
        match: ['Tickets', 'TicketDetail'],
      },
      {
        label: 'Skill note',
        hint: 'Log a completed training',
        icon: 'school',
        to: '/create-skill',
        match: ['CreateSkill'],
      },
      {
        label: 'Guide',
        hint: 'How the screens and programs fit',
        icon: 'menu_book',
        to: '/how-it-works',
        match: ['HowItWorks'],
      },
    ],
  },
  {
    title: "What's going on",
    items: [
      {
        label: 'Pit Stop signups',
        hint: 'Filter clients to Pit Stop applicants',
        icon: 'badge',
        to: { name: 'Clients', query: { program: 'pit_stop' } },
        queryProgram: 'pit_stop',
      },
      {
        label: 'City Build signups',
        hint: 'Filter clients to City Build interest',
        icon: 'apartment',
        to: { name: 'Clients', query: { program: 'citybuild' } },
        queryProgram: 'citybuild',
      },
    ],
  },
  {
    title: 'Other apps',
    items: [
      {
        label: 'Public signup',
        hint: 'The form new clients fill out',
        icon: 'app_registration',
        href: '/',
      },
      {
        label: 'Lobby check-in',
        hint: 'Phone lookup when they arrive',
        icon: 'front_hand',
        href: '/checkin',
      },
      {
        label: 'Worker portal',
        hint: 'Pit Stop clock in and out',
        icon: 'schedule',
        href: '/worker/',
      },
    ],
  },
  {
    title: 'Admin & reports',
    items: [
      {
        label: 'Django admin',
        hint: 'PINs, work sites, one-off repairs',
        icon: 'admin_panel_settings',
        href: getApiUrl('/admin/'),
        external: true,
      },
      {
        label: 'Reports hub',
        hint: 'Downloadable spreadsheets',
        icon: 'table_chart',
        href: getApiUrl('/api/reports/'),
        external: true,
      },
      {
        label: 'Pit Stop applications',
        hint: 'Interview decisions in admin',
        icon: 'fact_check',
        href: getApiUrl('/admin/clients/pitstopapplication/'),
        external: true,
      },
    ],
  },
]

const currentSection = computed(() => {
  const name = String(route.name || '')
  if (name === 'Dashboard') return 'Home'
  if (name === 'ClientCreate') return 'Add a client'
  if (name === 'ClientDetail' || name === 'Clients') {
    if (route.query.program === 'citybuild') return 'City Build signups'
    if (route.query.program === 'pit_stop') return 'Pit Stop signups'
    return name === 'ClientDetail' ? 'Client' : 'Clients'
  }
  if (name === 'TicketDetail') return 'Tickets'
  if (name === 'CreateSkill') return 'Skill note'
  if (name === 'HowItWorks') return 'Guide'
  if (name === 'Messages') return 'Messages'
  if (name === 'Classes') return 'Classes'
  if (name === 'Tickets') return 'Tickets'
  return 'Staff'
})

function isItemActive(item: NavItem) {
  if (item.queryProgram) {
    return route.name === 'Clients' && String(route.query.program || '') === item.queryProgram
  }
  if (item.match?.length) {
    if (item.match.includes('Clients') && route.name === 'Clients' && route.query.program) {
      return false
    }
    return item.match.includes(String(route.name || ''))
  }
  return false
}

const themeStyle = computed(() =>
  accentThemeVars(props.user?.accent_color || readLastAccent()),
)

const showChrome = computed(() => {
  const guest = ['Login', 'ForgotPassword', 'ResetPassword']
  return Boolean(props.user) && !guest.includes(String(route.name))
})

const mainClass = computed(() => {
  if (!showChrome.value) return 'min-h-screen'
  const widthClass = [
    'Dashboard',
    'Classes',
    'ClientDetail',
    'Tickets',
    'TicketDetail',
    'Messages',
    'HowItWorks',
  ].includes(String(route.name))
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
  () => route.fullPath,
  () => {
    navOpen.value = false
  },
)

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
