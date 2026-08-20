<template>
  <section class="staff-card p-4">
    <div class="staff-panel-header">
      <span class="material-symbols-outlined" aria-hidden="true">confirmation_number</span>
      <h3>Tickets</h3>
      <StaffTip text="Report bugs with screenshots, set urgency, and track status. Open Your tickets or All tickets for the full list." />
      <RouterLink to="/tickets" class="text-xs font-semibold staff-link shrink-0">All →</RouterLink>
    </div>

    <form class="space-y-2 mb-3" @submit.prevent="quickCreate">
      <input
        v-model="title"
        type="text"
        class="staff-input"
        placeholder="Short title — what’s broken or needed?"
        maxlength="200"
      />
      <textarea
        v-model="description"
        rows="2"
        class="staff-input"
        placeholder="Details / steps. You can add screenshots on the next screen."
      />
      <div class="staff-seg mb-1">
        <button
          v-for="p in priorities"
          :key="p"
          type="button"
          class="staff-seg-btn"
          :class="{ 'staff-seg-btn-active': priority === p }"
          @click="priority = p"
        >
          {{ p.toUpperCase() }}
        </button>
      </div>
      <button type="submit" class="staff-btn staff-btn-primary w-full" :disabled="busy || !title.trim() || !description.trim()">
        {{ busy ? 'Creating…' : 'Open ticket' }}
      </button>
    </form>

    <p class="text-xs font-semibold text-stone-500 uppercase tracking-wide mb-1.5">Your open tickets</p>
    <CardSkeleton v-if="loading" variant="list" :count="3" />
    <p v-else-if="mine.length === 0" class="text-sm text-stone-500">None open — nice.</p>
    <ul v-else class="space-y-1.5 staff-fade-in">
      <li v-for="t in mine" :key="t.id">
        <RouterLink
          :to="{ name: 'TicketDetail', params: { id: t.id } }"
          class="flex items-center justify-between gap-2 border-t border-stone-100 pt-1.5 first:border-0 first:pt-0"
        >
          <span class="text-sm font-medium truncate">#{{ t.id }} {{ t.title }}</span>
          <span class="text-[10px] uppercase font-bold text-stone-500 shrink-0">{{ t.priority }}</span>
        </RouterLink>
      </li>
    </ul>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { staffFetch } from '../../api'
import { friendlyError, networkErrorMessage } from '../../utils/errors'
import { useToast } from '../../composables/useToast'
import CardSkeleton from './CardSkeleton.vue'
import StaffTip from '../StaffTip.vue'

interface TicketRow {
  id: number
  title: string
  status: string
  priority: string
}

const router = useRouter()
const toast = useToast()
const title = ref('')
const description = ref('')
const priority = ref('p2')
const priorities = ['p0', 'p1', 'p2', 'p3', 'p4']
const busy = ref(false)
const loading = ref(true)
const mine = ref<TicketRow[]>([])

async function loadMine() {
  loading.value = true
  try {
    const resp = await staffFetch('/api/staff/tickets/?scope=mine&status=open&limit=5')
    if (!resp.ok) return
    const body = await resp.json()
    mine.value = body.results || []
  } catch {
    /* ignore */
  } finally {
    loading.value = false
  }
}

async function quickCreate() {
  if (busy.value || !title.value.trim() || !description.value.trim()) return
  busy.value = true
  try {
    const resp = await staffFetch('/api/staff/tickets/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        title: title.value.trim(),
        description: description.value.trim(),
        priority: priority.value,
        tags: ['other'],
      }),
    })
    const body = await resp.json().catch(() => null)
    if (!resp.ok) {
      toast.error(friendlyError(body, 'Could not create ticket.'))
      return
    }
    toast.success('Ticket opened — add screenshots on the next page.')
    title.value = ''
    description.value = ''
    priority.value = 'p2'
    router.push({ name: 'TicketDetail', params: { id: body.id } })
  } catch (e) {
    toast.error(networkErrorMessage(e))
  } finally {
    busy.value = false
  }
}

onMounted(loadMine)
</script>
