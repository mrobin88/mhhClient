<template>
  <div class="staff-app" :style="themeStyle">
    <ToastStack />
    <header
      v-if="showChrome"
      class="staff-chrome-bar sticky top-0 z-40 px-4 py-3 flex items-center justify-between"
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
        <button
          type="button"
          class="staff-btn staff-btn-ghost staff-chrome-feedback"
          title="Send feedback"
          @click="openFeedback"
        >
          <span class="material-symbols-outlined" style="font-size: 18px;" aria-hidden="true">lightbulb</span>
          Feedback
        </button>
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
      <div class="staff-nav-dock">
        <button
          type="button"
          class="staff-nav-feedback"
          title="Send feedback from this screen"
          @click="openFeedback"
        >
          <span class="material-symbols-outlined" aria-hidden="true">lightbulb</span>
          <span>Feedback</span>
        </button>
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
      </div>

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

    <SuggestionSheet
      :open="feedbackOpen"
      :context="feedbackContext"
      @close="feedbackOpen = false"
    />
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
import SuggestionSheet from './SuggestionSheet.vue'

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
const feedbackOpen = ref(false)
let pollTimer: ReturnType<typeof setInterval> | null = null

const feedbackContext = computed(() => {
  const screen = currentSection.value
  const path = String(route.fullPath || '')
  return `${screen} (${path})`
})

const navGroups: { title: string; items: NavItem[] }[] = [
  {
    title: 'Daily work',
    items: [
      {
        label: 'Home',
        hint: 'Search, today’s classes, and new signups',
        icon: 'home',
        to: '/dashboard',
        match: ['Dashboard'],
      },
      {
        label: 'Clients',
        hint: 'Everyone on the roster',
        icon: 'group',
        to: '/clients',
        match: ['Clients', 'ClientDetail'],
      },
      {
        label: 'Add a client',
        hint: 'For someone who did not use the public signup',
        icon: 'person_add',
        to: '/clients/new',
        match: ['ClientCreate'],
      },
      {
        label: 'Messages',
        hint: 'Texts with clients. The number is unread replies',
        icon: 'chat',
        to: '/messages',
        match: ['Messages'],
        badge: true,
      },
      {
        label: 'Pit Stop applications',
        hint: 'Applications waiting for a first review',
        icon: 'assignment_ind',
        to: '/pitstop-applications',
        match: ['PitStopApplications', 'PitStopApplicationDetail'],
      },
      {
        label: 'Classes',
        hint: 'Dates, rosters, and sign-in sheets',
        icon: 'event',
        to: '/classes',
        match: ['Classes'],
      },
      {
        label: 'Suggestions',
        hint: 'Ideas and problems from staff',
        icon: 'lightbulb',
        to: '/suggestions',
        match: ['Tickets', 'TicketDetail'],
      },
      {
        label: 'Training note',
        hint: 'Record a class someone finished',
        icon: 'school',
        to: '/create-skill',
        match: ['CreateSkill'],
      },
      {
        label: 'Guide',
        hint: 'What each screen is for',
        icon: 'menu_book',
        to: '/how-it-works',
        match: ['HowItWorks'],
      },
    ],
  },
  {
    title: 'Signups by program',
    items: [
      {
        label: 'Pit Stop signups',
        hint: 'Clients who chose Pit Stop',
        icon: 'badge',
        to: { name: 'Clients', query: { program: 'pit_stop' } },
        queryProgram: 'pit_stop',
      },
      {
        label: 'City Build signups',
        hint: 'Clients who chose City Build',
        icon: 'apartment',
        to: { name: 'Clients', query: { program: 'citybuild' } },
        queryProgram: 'citybuild',
      },
    ],
  },
  {
    title: 'Other screens',
    items: [
      {
        label: 'Public signup',
        hint: 'The page visitors use to sign up',
        icon: 'app_registration',
        href: '/',
      },
      {
        label: 'Lobby check-in',
        hint: 'Look someone up when they walk in',
        icon: 'front_hand',
        href: '/checkin/',
      },
      {
        label: 'Worker clock',
        hint: 'Where Pit Stop workers clock in and out',
        icon: 'schedule',
        href: '/worker/',
      },
    ],
  },
  {
    title: 'Office tools',
    items: [
      {
        label: 'Django admin',
        hint: 'Records, PINs, and work sites',
        icon: 'admin_panel_settings',
        href: getApiUrl('/admin/'),
        external: true,
      },
      {
        label: 'Impact report',
        hint: 'Counts for the funder. No client names',
        icon: 'table_chart',
        href: getApiUrl('/api/reports/'),
        external: true,
      },
    ],
  },
]

function openFeedback() {
  navOpen.value = false
  feedbackOpen.value = true
}

const currentSection = computed(() => {
  const name = String(route.name || '')
  if (name === 'Dashboard') return 'Home'
  if (name === 'ClientCreate') return 'Add a client'
  if (name === 'ClientDetail' || name === 'Clients') {
    if (route.query.program === 'citybuild') return 'City Build signups'
    if (route.query.program === 'pit_stop') return 'Pit Stop signups'
    return name === 'ClientDetail' ? 'Client' : 'Clients'
  }
  if (name === 'PitStopApplications' || name === 'PitStopApplicationDetail') return 'Pit Stop applications'
  if (name === 'TicketDetail') return 'Suggestions'
  if (name === 'CreateSkill') return 'Training note'
  if (name === 'HowItWorks') return 'Guide'
  if (name === 'Messages') return 'Messages'
  if (name === 'Classes') return 'Classes'
  if (name === 'Tickets') return 'Suggestions'
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
    'Clients',
    'ClientDetail',
    'Tickets',
    'TicketDetail',
    'Messages',
    'HowItWorks',
    'PitStopApplications',
    'PitStopApplicationDetail',
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
    feedbackOpen.value = false
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
