<template>
  <section class="space-y-3">
    <div class="staff-card p-4">
      <div class="staff-panel-header">
        <span class="material-symbols-outlined" aria-hidden="true">person_add</span>
        <h3>Add a client</h3>
        <StaffTip text="Use this for a referral or outside interest form. Add only what you know; the client can securely upload requested documents afterward." />
      </div>

      <form class="space-y-3" @submit.prevent="submit(false)">
        <div class="staff-field-grid">
          <label class="staff-field">
            <span>First name</span>
            <input v-model.trim="form.first_name" required class="staff-input" />
          </label>
          <label class="staff-field">
            <span>Last name</span>
            <input v-model.trim="form.last_name" required class="staff-input" />
          </label>
          <label class="staff-field">
            <span>Phone</span>
            <input v-model.trim="form.phone" required type="tel" class="staff-input" />
          </label>
          <label class="staff-field">
            <span>Email (optional)</span>
            <input v-model.trim="form.email" type="email" class="staff-input" />
          </label>
          <label class="staff-field">
            <span>Date of birth (optional)</span>
            <input v-model="form.dob" type="date" class="staff-input" />
          </label>
          <label class="staff-field">
            <span>Gender</span>
            <select v-model="form.gender" required class="staff-input">
              <option value="P">Prefer not to say</option>
              <option value="M">Male</option>
              <option value="F">Female</option>
              <option value="NB">Non-binary</option>
              <option value="O">Other</option>
            </select>
          </label>
          <label class="staff-field">
            <span>Program interest</span>
            <select v-model="form.training_interest" class="staff-input">
              <option value="citybuild">City Build Academy</option>
              <option value="capsa">CAPSA</option>
              <option value="pit_stop">Pit Stop</option>
              <option value="guard_card">Guard Card</option>
              <option value="general">General services</option>
            </select>
          </label>
          <label class="staff-field">
            <span>Referral source</span>
            <select v-model="form.referral_source" class="staff-input">
              <option value="community_org">Community organization / outside form</option>
              <option value="website">Website</option>
              <option value="walk_in">Walk-in</option>
              <option value="job_center">Job center</option>
              <option value="friend">Friend or family</option>
              <option value="social_media">Social media</option>
              <option value="other">Other</option>
            </select>
          </label>
        </div>
        <label class="staff-field">
          <span>Referral or outreach notes (optional)</span>
          <textarea v-model.trim="form.additional_notes" rows="3" class="staff-input"></textarea>
        </label>
        <button type="submit" class="staff-btn staff-btn-primary w-full" :disabled="saving">
          {{ saving ? 'Checking…' : 'Add client' }}
        </button>
      </form>
    </div>

    <div v-if="duplicates.length" class="staff-card p-4 border-amber-300 space-y-3">
      <h4 class="font-semibold text-amber-900">Possible duplicate</h4>
      <p class="text-sm text-stone-600">Open the existing person, or confirm that this is a different client.</p>
      <RouterLink
        v-for="client in duplicates"
        :key="client.id"
        :to="{ name: 'ClientDetail', params: { id: client.id } }"
        class="block staff-stat-tile text-sm font-semibold"
      >
        {{ client.full_name }} · {{ client.phone }}
      </RouterLink>
      <button type="button" class="staff-btn staff-btn-secondary w-full" :disabled="saving" @click="submit(true)">
        Create a separate client anyway
      </button>
    </div>
  </section>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { staffFetch } from '../api'
import { friendlyError, networkErrorMessage } from '../utils/errors'
import { useToast } from '../composables/useToast'
import StaffTip from './StaffTip.vue'

const router = useRouter()
const toast = useToast()
const saving = ref(false)
const duplicates = ref<Array<{ id: number; full_name: string; phone: string }>>([])
const form = reactive({
  first_name: '',
  last_name: '',
  phone: '',
  email: '',
  dob: '',
  gender: 'P',
  training_interest: 'citybuild',
  referral_source: 'community_org',
  additional_notes: '',
})

async function submit(confirmDuplicate: boolean) {
  if (saving.value) return
  saving.value = true
  try {
    const payload = Object.fromEntries(
      Object.entries(form).filter(([, value]) => value !== ''),
    )
    const resp = await staffFetch('/api/staff/clients/create/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ...payload, confirm_duplicate: confirmDuplicate }),
    })
    const body = await resp.json().catch(() => null)
    if (resp.status === 409) {
      duplicates.value = body?.duplicates || []
      toast.error('Check the possible duplicate before creating another client.')
      return
    }
    if (!resp.ok) {
      toast.error(friendlyError(body, 'Could not add that client.'))
      return
    }
    toast.success('Client added.')
    await router.push({ name: 'ClientDetail', params: { id: body.id } })
  } catch (error) {
    toast.error(networkErrorMessage(error))
  } finally {
    saving.value = false
  }
}
</script>
