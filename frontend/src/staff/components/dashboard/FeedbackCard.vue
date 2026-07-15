<template>
  <section class="staff-card p-4">
    <div class="staff-panel-header">
      <span class="material-symbols-outlined" aria-hidden="true">forum</span>
      <h3>Feedback for the team</h3>
    </div>
    <p class="text-xs text-stone-500 mb-2">
      Only superusers can read submissions in Django admin — not shown to other staff.
    </p>

    <textarea
      v-model="message"
      rows="3"
      class="staff-input mb-3"
      placeholder="What would make this dashboard or your day-to-day work better?"
      maxlength="4000"
    />

    <button
      type="button"
      class="staff-btn staff-btn-primary w-full"
      :disabled="busy || !message.trim()"
      @click="submit"
    >
      {{ busy ? 'Sending…' : 'Send feedback' }}
    </button>
  </section>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { staffFetch } from '../../api'
import { friendlyError, networkErrorMessage } from '../../utils/errors'
import { useToast } from '../../composables/useToast'

const message = ref('')
const busy = ref(false)
const toast = useToast()

async function submit() {
  if (busy.value || !message.value.trim()) return
  busy.value = true
  try {
    const resp = await staffFetch('/api/staff/feedback/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: message.value.trim() }),
    })
    const body = await resp.json().catch(() => null)
    if (!resp.ok) {
      toast.error(friendlyError(body, 'Could not send feedback.'))
      return
    }
    message.value = ''
    toast.success('Thanks for the feedback!')
  } catch (err) {
    toast.error(networkErrorMessage(err))
  } finally {
    busy.value = false
  }
}
</script>
