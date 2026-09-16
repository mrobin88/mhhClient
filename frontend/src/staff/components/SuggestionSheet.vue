<template>
  <Teleport to="body">
    <div v-if="open" class="staff-suggest-root">
      <button type="button" class="staff-suggest-backdrop" aria-label="Close feedback" @click="close" />
      <section
        class="staff-suggest-sheet"
        role="dialog"
        aria-modal="true"
        aria-labelledby="staff-suggest-title"
      >
        <div class="staff-panel-header">
          <span class="material-symbols-outlined" aria-hidden="true">lightbulb</span>
          <h3 id="staff-suggest-title">Feedback</h3>
          <button type="button" class="staff-btn staff-btn-ghost staff-btn-sm shrink-0" @click="close">
            Close
          </button>
        </div>
        <p class="text-xs text-stone-500 mb-3">
          Idea, problem, or request. We see which screen you were on.
        </p>
        <form class="space-y-2" @submit.prevent="submit">
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
          <textarea
            ref="box"
            v-model="description"
            rows="4"
            class="staff-input"
            placeholder="What’s going on?"
          />
          <button type="submit" class="staff-btn staff-btn-primary w-full" :disabled="busy || !description.trim()">
            {{ busy ? 'Sending…' : 'Send' }}
          </button>
        </form>
        <RouterLink to="/suggestions" class="block text-center text-xs font-semibold staff-link pt-3" @click="close">
          Open the suggestion box →
        </RouterLink>
      </section>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import { staffFetch } from '../api'
import { friendlyError, networkErrorMessage } from '../utils/errors'
import { useToast } from '../composables/useToast'
import {
  SUGGESTION_KINDS,
  suggestionBodyWithContext,
  suggestionPriority,
  suggestionTitleFromBody,
  type SuggestionKind,
} from '../suggestions'

const props = defineProps<{
  open: boolean
  context: string
}>()

const emit = defineEmits<{ close: [] }>()

const toast = useToast()
const description = ref('')
const kind = ref<SuggestionKind>('problem')
const busy = ref(false)
const box = ref<HTMLTextAreaElement | null>(null)

watch(
  () => props.open,
  async (isOpen) => {
    if (!isOpen) return
    await nextTick()
    box.value?.focus()
  },
)

function close() {
  emit('close')
}

function onKey(e: KeyboardEvent) {
  if (e.key === 'Escape' && props.open) close()
}

onMounted(() => window.addEventListener('keydown', onKey))
onUnmounted(() => window.removeEventListener('keydown', onKey))

async function submit() {
  if (busy.value || !description.value.trim()) return
  busy.value = true
  try {
    const bodyText = suggestionBodyWithContext(description.value, props.context)
    const resp = await staffFetch('/api/staff/tickets/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        title: suggestionTitleFromBody(description.value),
        description: bodyText,
        priority: suggestionPriority(kind.value),
        tags: [kind.value],
      }),
    })
    const body = await resp.json().catch(() => null)
    if (!resp.ok) {
      toast.error(friendlyError(body, 'Could not send that.'))
      return
    }
    toast.success('Sent. Thank you.')
    description.value = ''
    kind.value = 'problem'
    close()
  } catch (e) {
    toast.error(networkErrorMessage(e))
  } finally {
    busy.value = false
  }
}
</script>
