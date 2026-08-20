<template>
  <section class="staff-card p-4">
    <div class="staff-panel-header">
      <span class="material-symbols-outlined" aria-hidden="true">palette</span>
      <h3>Desk color</h3>
      <StaffTip text="Match buttons and highlights to the color of your desk. The choice is saved on your staff profile." />
    </div>
    <p class="staff-panel-note">
      Spin the wheel until it matches the desk you sit at. We save it to your profile so it comes back next time.
    </p>

    <div class="staff-color-picker">
      <div class="staff-color-wheel-wrap">
        <canvas
          ref="wheelEl"
          class="staff-color-wheel"
          aria-label="Color wheel"
          @pointerdown="onWheelPointer"
          @pointermove="onWheelPointer"
          @pointerup="endPointer"
          @pointercancel="endPointer"
        />
        <div class="staff-color-wheel-knob" :style="knobStyle" aria-hidden="true" />
      </div>

      <label class="staff-color-slider-label">
        Brightness
        <input
          v-model.number="valuePct"
          class="staff-color-slider"
          type="range"
          min="18"
          max="100"
          :style="{ '--staff-slider-fill': brightnessGradient }"
          @input="onBrightnessInput"
        />
      </label>

      <div class="staff-color-hex-row">
        <span class="staff-color-swatch" :style="{ background: hex }" aria-hidden="true" />
        <input
          v-model="hexDraft"
          class="staff-input staff-color-hex-input"
          type="text"
          maxlength="7"
          spellcheck="false"
          aria-label="Hex color"
          @change="onHexCommit"
          @keyup.enter="onHexCommit"
        />
        <span class="staff-color-save-status" :class="{ 'is-error': Boolean(error) }">{{ statusText }}</span>
      </div>

      <div class="staff-color-presets" role="list">
        <button
          v-for="preset in DESK_PRESETS"
          :key="preset.hex"
          type="button"
          class="staff-color-preset"
          :class="{ 'is-active': hex === preset.hex }"
          :style="{ background: preset.hex }"
          :title="preset.label"
          :aria-label="preset.label"
          @click="applyHex(preset.hex)"
        />
      </div>

      <button type="button" class="staff-btn staff-btn-ghost staff-color-reset" @click="resetToHall">
        Reset to Hall orange
      </button>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, inject, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { staffFetch } from '../../api'
import { setStaffUserKey, staffUserKey } from '../../staffContext'
import {
  DEFAULT_ACCENT,
  DESK_PRESETS,
  hexToHsv,
  hsvToHex,
  hsvToRgb,
  normalizeHex,
  rgbToHex,
  type Hsv,
} from '../../theme'
import StaffTip from '../StaffTip.vue'

const WHEEL_SIZE = 188
const staffUser = inject(staffUserKey)
const setStaffUser = inject(setStaffUserKey)

const wheelEl = ref<HTMLCanvasElement | null>(null)
const hue = ref(24)
const sat = ref(0.94)
const valuePct = ref(92)
const hexDraft = ref(DEFAULT_ACCENT)
const error = ref('')
const saveState = ref<'idle' | 'saving' | 'saved'>('idle')
let dragging = false
let saveTimer: ReturnType<typeof setTimeout> | null = null
let wheelBitmap: ImageData | null = null

const hsv = computed<Hsv>(() => ({
  h: hue.value,
  s: sat.value,
  v: valuePct.value / 100,
}))

const hex = computed(() => hsvToHex(hsv.value))

const brightnessGradient = computed(() => {
  const rgb = hsvToRgb(hue.value, sat.value, 1)
  return `linear-gradient(90deg, #1c1917, ${rgbToHex(rgb.r, rgb.g, rgb.b)})`
})

const knobStyle = computed(() => {
  const radius = WHEEL_SIZE / 2
  const angle = (hue.value * Math.PI) / 180
  const dist = sat.value * (radius - 8)
  return {
    left: `${radius + Math.cos(angle) * dist}px`,
    top: `${radius + Math.sin(angle) * dist}px`,
    background: hex.value,
  }
})

const statusText = computed(() => {
  if (error.value) return error.value
  if (saveState.value === 'saving') return 'Saving…'
  if (saveState.value === 'saved') return 'Saved to your profile'
  return hex.value
})

function applyLocal(nextHex: string) {
  const current = staffUser?.value
  if (current && setStaffUser) {
    setStaffUser({ ...current, accent_color: nextHex })
  }
}

function setFromHsv(next: Hsv, persist: boolean) {
  hue.value = next.h
  sat.value = next.s
  valuePct.value = Math.round(next.v * 100)
  const nextHex = hsvToHex(next)
  hexDraft.value = nextHex
  applyLocal(nextHex)
  if (persist) queueSave(nextHex)
}

function applyHex(nextHex: string, persist = true) {
  const normalized = normalizeHex(nextHex)
  if (!normalized) return
  setFromHsv(hexToHsv(normalized), persist)
}

function onHexCommit() {
  const normalized = normalizeHex(hexDraft.value)
  if (!normalized) {
    hexDraft.value = hex.value
    return
  }
  applyHex(normalized)
}

function onBrightnessInput() {
  setFromHsv(hsv.value, true)
}

function queueSave(nextHex: string) {
  error.value = ''
  saveState.value = 'saving'
  if (saveTimer) clearTimeout(saveTimer)
  saveTimer = setTimeout(() => {
    void save(nextHex)
  }, 650)
}

async function save(nextHex: string) {
  try {
    const resp = await staffFetch('/api/staff/profile/', {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ accent_color: nextHex }),
    })
    const body = await resp.json().catch(() => null)
    if (!resp.ok) {
      error.value = body?.error || 'Could not save color.'
      saveState.value = 'idle'
      return
    }
    if (body?.user && setStaffUser) setStaffUser(body.user)
    saveState.value = 'saved'
  } catch {
    error.value = 'Could not save color.'
    saveState.value = 'idle'
  }
}

function resetToHall() {
  applyHex(DEFAULT_ACCENT)
}

function drawWheel() {
  const canvas = wheelEl.value
  if (!canvas) return
  const dpr = Math.min(window.devicePixelRatio || 1, 2)
  const pixelSize = Math.round(WHEEL_SIZE * dpr)
  canvas.width = pixelSize
  canvas.height = pixelSize
  canvas.style.width = `${WHEEL_SIZE}px`
  canvas.style.height = `${WHEEL_SIZE}px`
  const ctx = canvas.getContext('2d')
  if (!ctx) return

  if (!wheelBitmap || wheelBitmap.width !== pixelSize) {
    const image = ctx.createImageData(pixelSize, pixelSize)
    const cx = pixelSize / 2
    const cy = pixelSize / 2
    const radius = pixelSize / 2 - 2 * dpr
    for (let y = 0; y < pixelSize; y += 1) {
      for (let x = 0; x < pixelSize; x += 1) {
        const dx = x - cx
        const dy = y - cy
        const dist = Math.sqrt(dx * dx + dy * dy)
        const i = (y * pixelSize + x) * 4
        if (dist > radius) {
          image.data[i + 3] = 0
          continue
        }
        const angle = (Math.atan2(dy, dx) * 180) / Math.PI
        const wheelHue = (angle + 360) % 360
        const wheelSat = dist / radius
        const rgb = hsvToRgb(wheelHue, wheelSat, 1)
        image.data[i] = Math.round(rgb.r)
        image.data[i + 1] = Math.round(rgb.g)
        image.data[i + 2] = Math.round(rgb.b)
        image.data[i + 3] = 255
      }
    }
    wheelBitmap = image
  }

  ctx.putImageData(wheelBitmap, 0, 0)
}

function colorFromPointer(event: PointerEvent) {
  const canvas = wheelEl.value
  if (!canvas) return
  const rect = canvas.getBoundingClientRect()
  const x = event.clientX - rect.left
  const y = event.clientY - rect.top
  const cx = rect.width / 2
  const cy = rect.height / 2
  const dx = x - cx
  const dy = y - cy
  const radius = Math.min(cx, cy) - 4
  const dist = Math.sqrt(dx * dx + dy * dy)
  const nextHue = (Math.atan2(dy, dx) * 180) / Math.PI
  setFromHsv(
    {
      h: (nextHue + 360) % 360,
      s: Math.min(1, dist / radius),
      v: valuePct.value / 100,
    },
    true,
  )
}

function onWheelPointer(event: PointerEvent) {
  if (event.type === 'pointerdown') {
    dragging = true
    wheelEl.value?.setPointerCapture(event.pointerId)
  }
  if (!dragging && event.type === 'pointermove') return
  event.preventDefault()
  colorFromPointer(event)
}

function endPointer() {
  dragging = false
}

function syncFromProfile(accent: string | undefined, persist: boolean) {
  applyHex(normalizeHex(accent) || DEFAULT_ACCENT, persist)
}

onMounted(() => {
  drawWheel()
  syncFromProfile(staffUser?.value?.accent_color, false)
})

watch(
  () => staffUser?.value?.accent_color,
  (next) => {
    const normalized = normalizeHex(next) || DEFAULT_ACCENT
    if (normalized === hex.value) return
    syncFromProfile(next, false)
  },
)

onBeforeUnmount(() => {
  if (saveTimer) clearTimeout(saveTimer)
})
</script>
