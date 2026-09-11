<template>
  <section class="staff-card p-4">
    <div class="staff-panel-header">
      <span class="material-symbols-outlined" aria-hidden="true">lightbulb</span>
      <h3>Suggestion box</h3>
      <StaffTip text="Drop an idea, a problem, or a request. It stays in the box so we can follow up — no priority codes needed." />
      <RouterLink to="/suggestions" class="text-xs font-semibold staff-link shrink-0">All →</RouterLink>
    </div>

    <form class="space-y-2 mb-3" @submit.prevent="quickCreate">
      <div class="staff-chip-row" style="margin-bottom: 0;">
        <button
          v-for="k in SUGGESTION_KINDS"
          :key="k.value"
          type="button"
          class="staff-chip"
          :class="{ 'staff-chip-active': kind === k.value }"
          @click="kind = k.value"
        >
          {{ k.label }}
        </button>
      </div>
      <p class="text-xs text-stone-500">{{ kindHint }}</p>
      <textarea
        v-model="description"
        rows="3"
        class="staff-input"
        placeholder="What’s the idea, problem, or request?"
      />
      <button type="submit" class="staff-btn staff-btn-primary w-full" :disabled="busy || !description.trim()">
        {{ busy ? 'Sending…' : 'Drop in the box' }}
      </button>
    </form>

    <p class="text-xs font-semibold text-stone-500 uppercase tracking-wide mb-1.5">Your open notes</p>
    <CardSkeleton v-if="loading" variant="list" :count="3" />
    <p v-else-if="mine.length === 0" class="text-sm text-stone-500">Nothing waiting — drop one anytime.</p>
    <ul v-else class="space-y-1.5 staff-fade-in">
      <li v-for="t in mine" :key="t.id">
        <RouterLink
          :to="{ name: 'TicketDetail', params: { id: t.id } }"
          class="flex items-center justify-between gap-2 border-t border-stone-100 pt-1.5 first:border-0 first:pt-0"
        >
          <span class="text-sm font-medium truncate">{{ t.title }}</span>
          <span class="text-[10px] uppercase font-bold text-stone-500 shrink-0">
            {{ suggestionKindLabel(t.tags) || t.status }}
          </span>
        </RouterLink>
      </li>
    </ul>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { staffFetch } from '../../api'
import { friendlyError, networkErrorMessage } from '../../utils/errors'
import { useToast } from '../../composables/useToast'
import {
  SUGGESTION_KINDS,
  suggestionKindLabel,
  suggestionPriority,
  suggestionTitleFromBody,
  type SuggestionKind,
} from '../../suggestions'
import CardSkeleton from './CardSkeleton.vue'
import StaffTip from '../StaffTip.vue'

interface TicketRow {
  id: number
  title: string
  status: string
  tags?: string[]
}

const toast = useToast()
const description = ref('')
const kind = ref<SuggestionKind>('idea')
const busy = ref(false)
const loading = ref(true)
const mine = ref<TicketRow[]>([])

const kindHint = computed(
  () => SUGGESTION_KINDS.find((k) => k.value === kind.value)?.hint || '',
)

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
  if (busy.value || !description.value.trim()) return
  busy.value = true
  try {
    const bodyText = description.value.trim()
    const resp = await staffFetch('/api/staff/tickets/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        title: suggestionTitleFromBody(bodyText),
        description: bodyText,
        priority: suggestionPriority(kind.value),
        tags: [kind.value],
      }),
    })
    const body = await resp.json().catch(() => null)
    if (!resp.ok) {
      toast.error(friendlyError(body, 'Could not send that suggestion.'))
      return
    }
    toast.success('In the suggestion box.')
    description.value = ''
    kind.value = 'idea'
    await loadMine()
  } catch (e) {
    toast.error(networkErrorMessage(e))
  } finally {
    busy.value = false
  }
}

onMounted(loadMine)
</script>
