<template>
  <div class="staff-ticket-qa space-y-3">
    <div class="staff-field">
      <label>Status</label>
      <select v-model="local.status" class="staff-input" :disabled="busy" @change="maybeSave">
        <option v-for="opt in statuses" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
      </select>
    </div>

    <div v-if="needsResolution" class="staff-field">
      <label>Resolution code</label>
      <select v-model="local.resolution" class="staff-input" :disabled="busy" @change="maybeSave">
        <option value="">Choose resolution…</option>
        <option v-for="opt in resolutions" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
      </select>
    </div>

    <div class="staff-field">
      <label>Priority</label>
      <div class="staff-seg">
        <button
          v-for="opt in priorities"
          :key="opt.value"
          type="button"
          class="staff-seg-btn"
          :class="{ 'staff-seg-btn-active': local.priority === opt.value }"
          :disabled="busy"
          @click="setPriority(opt.value)"
        >
          {{ opt.value.toUpperCase() }}
        </button>
      </div>
    </div>

    <div class="staff-field">
      <label>Assignee</label>
      <input
        v-model="assigneeQuery"
        type="search"
        class="staff-input"
        placeholder="Search staff…"
        :disabled="busy"
        @input="searchAssignees"
      />
      <p v-if="local.assignee_name" class="text-xs text-stone-500 mt-1">
        Assigned to <strong>{{ local.assignee_name }}</strong>
        <button type="button" class="text-orange-600 font-semibold ml-2" :disabled="busy" @click="clearAssignee">
          Clear
        </button>
      </p>
      <ul v-if="assigneeOptions.length" class="mt-1 border border-stone-200 rounded-lg overflow-hidden">
        <li v-for="u in assigneeOptions" :key="u.id">
          <button
            type="button"
            class="w-full text-left px-3 py-2 text-sm hover:bg-orange-50"
            @click="pickAssignee(u)"
          >
            {{ u.name }}
          </button>
        </li>
      </ul>
    </div>

    <div class="staff-field">
      <label>Tags</label>
      <div class="staff-chip-row" style="margin-bottom: 0;">
        <button
          v-for="opt in tags"
          :key="opt.value"
          type="button"
          class="staff-chip"
          :class="{ 'staff-chip-active': local.tags.includes(opt.value) }"
          :disabled="busy"
          @click="toggleTag(opt.value)"
        >
          {{ opt.label }}
        </button>
      </div>
    </div>

    <div class="flex gap-2">
      <button
        type="button"
        class="staff-btn staff-btn-primary flex-1"
        :disabled="busy || !dirty"
        @click="save"
      >
        {{ busy ? 'Saving…' : 'Save updates' }}
      </button>
      <RouterLink
        v-if="showDeepLink"
        :to="{ name: 'TicketDetail', params: { id: ticketId } }"
        class="staff-btn staff-btn-secondary shrink-0"
      >
        Full ticket
      </RouterLink>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import { staffFetch } from '../api'
import { friendlyError, networkErrorMessage } from '../utils/errors'
import { useToast } from '../composables/useToast'

export interface TicketMetaOpt {
  value: string
  label: string
}

export interface TicketQuickModel {
  id: number
  status: string
  resolution: string
  priority: string
  tags: string[]
  assignee_id: number | null
  assignee_name: string | null
}

const props = withDefaults(
  defineProps<{
    ticketId: number
    ticket: TicketQuickModel
    statuses: TicketMetaOpt[]
    resolutions: TicketMetaOpt[]
    priorities: TicketMetaOpt[]
    tags: TicketMetaOpt[]
    showDeepLink?: boolean
    autosave?: boolean
  }>(),
  { showDeepLink: true, autosave: false },
)

const emit = defineEmits<{ (e: 'updated', ticket: any): void }>()

const toast = useToast()
const busy = ref(false)
const assigneeQuery = ref('')
const assigneeOptions = ref<{ id: number; name: string }[]>([])
let searchTimer: ReturnType<typeof setTimeout> | null = null

const local = reactive({
  status: props.ticket.status,
  resolution: props.ticket.resolution || '',
  priority: props.ticket.priority,
  tags: [...(props.ticket.tags || [])],
  assignee_id: props.ticket.assignee_id,
  assignee_name: props.ticket.assignee_name,
})

const snapshot = ref('')

function snap() {
  snapshot.value = JSON.stringify({
    status: local.status,
    resolution: local.resolution,
    priority: local.priority,
    tags: [...local.tags].sort(),
    assignee_id: local.assignee_id,
  })
}

snap()

watch(
  () => props.ticket,
  (t) => {
    local.status = t.status
    local.resolution = t.resolution || ''
    local.priority = t.priority
    local.tags = [...(t.tags || [])]
    local.assignee_id = t.assignee_id
    local.assignee_name = t.assignee_name
    snap()
  },
  { deep: true },
)

const dirty = computed(() => {
  const now = JSON.stringify({
    status: local.status,
    resolution: local.resolution,
    priority: local.priority,
    tags: [...local.tags].sort(),
    assignee_id: local.assignee_id,
  })
  return now !== snapshot.value
})

const needsResolution = computed(() =>
  local.status === 'resolved' || local.status === 'closed',
)

function setPriority(value: string) {
  local.priority = value
  if (props.autosave) maybeSave()
}

function toggleTag(value: string) {
  const i = local.tags.indexOf(value)
  if (i >= 0) local.tags.splice(i, 1)
  else local.tags.push(value)
  if (props.autosave) maybeSave()
}

function clearAssignee() {
  local.assignee_id = null
  local.assignee_name = null
  assigneeQuery.value = ''
  if (props.autosave) maybeSave()
}

function pickAssignee(u: { id: number; name: string }) {
  local.assignee_id = u.id
  local.assignee_name = u.name
  assigneeQuery.value = u.name
  assigneeOptions.value = []
  if (props.autosave) maybeSave()
}

function searchAssignees() {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(async () => {
    const q = assigneeQuery.value.trim()
    if (q.length < 1) {
      assigneeOptions.value = []
      return
    }
    const resp = await staffFetch(`/api/staff/tickets/assignees/?q=${encodeURIComponent(q)}`)
    if (resp.ok) {
      const body = await resp.json()
      assigneeOptions.value = body.results || []
    }
  }, 200)
}

async function maybeSave() {
  if (props.autosave && dirty.value) await save()
}

async function save() {
  if (busy.value || !dirty.value) return
  if (needsResolution.value && !local.resolution) {
    toast.error('Pick a resolution code for Resolved/Closed.')
    return
  }
  busy.value = true
  try {
    const resp = await staffFetch(`/api/staff/tickets/${props.ticketId}/`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        status: local.status,
        resolution: needsResolution.value ? local.resolution : '',
        priority: local.priority,
        tags: local.tags,
        assignee_id: local.assignee_id,
      }),
    })
    const body = await resp.json().catch(() => null)
    if (!resp.ok) {
      toast.error(friendlyError(body, 'Could not update ticket.'))
      return
    }
    local.assignee_name = body.assignee_name
    snap()
    emit('updated', body)
    toast.success('Ticket updated.')
  } catch (e) {
    toast.error(networkErrorMessage(e))
  } finally {
    busy.value = false
  }
}

defineExpose({ save })
</script>
