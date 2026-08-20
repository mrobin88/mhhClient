<template>
  <section class="staff-card p-4" :class="{ 'is-color-collapsed': !open }">
    <div class="staff-panel-header">
      <span class="material-symbols-outlined" aria-hidden="true">palette</span>
      <h3>Desk color</h3>
      <StaffTip text="Match outlines and buttons to your desk. Saved on your staff account." />
      <span class="staff-color-swatch" :style="{ background: hex }" aria-hidden="true" />
      <button
        type="button"
        class="staff-collapse-btn staff-collapse-btn-inline"
        :aria-expanded="open"
        :title="open ? 'Hide color wheel' : 'Show color wheel'"
        @click="open = !open"
      >
        <span class="material-symbols-outlined" aria-hidden="true">
          {{ open ? 'expand_less' : 'expand_more' }}
        </span>
      </button>
    </div>

    <div v-show="open" class="staff-color-picker">
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
          @change="commitSave"
        />
      </label>

      <div class="staff-color-hex-row">
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
          @click="applyHex(preset.hex, true)"
        />
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, inject, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { saveStaffPrefsKey, staffUserKey } from '../../staffContext'
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

const WHEEL_SIZE = 108
const staffUser = inject(staffUserKey)
const saveStaffPrefs = inject(saveStaffPrefsKey)

const open = ref(false)
const wheelEl = ref<HTMLCanvasElement | null>(null)
const committedHex = ref(DEFAULT_ACCENT)
const hue = ref(24)
const sat = ref(0.94)
const valuePct = ref(92)
const hexDraft = ref(DEFAULT_ACCENT)
const error = ref('')
const saveState = ref<'idle' | 'saving' | 'saved'>('idle')
let dragging = false
let wheelDrawn = false
let wheelBitmap: ImageData | null = null
let pendingHex = ''

const hsv = computed<Hsv>(() => ({
  h: hue.value,
  s: sat.value,
  v: valuePct.value / 100,
}))

const hex = computed(() => (dragging ? hsvToHex(hsv.value) : committedHex.value))

const brightnessGradient = computed(() => {
  const rgb = hsvToRgb(hue.value, sat.value, 1)
  return `linear-gradient(90deg, #1c1917, ${rgbToHex(rgb.r, rgb.g, rgb.b)})`
})

const knobStyle = computed(() => {
  const radius = WHEEL_SIZE / 2
  const angle = (hue.value * Math.PI) / 180
  const dist = sat.value * (radius - 6)
  return {
    left: `${radius + Math.cos(angle) * dist}px`,
    top: `${radius + Math.sin(angle) * dist}px`,
    background: hex.value,
  }
})

const statusText = computed(() => {
  if (error.value) return error.value
  if (saveState.value === 'saving') return 'Saving to your account…'
  if (saveState.value === 'saved') return 'Saved to your account'
  return hex.value
})

function setHsvFromHex(nextHex: string) {
  const next = hexToHsv(nextHex)
  hue.value = next.h
  sat.value = next.s
  valuePct.value = Math.round(next.v * 100)
  committedHex.value = nextHex
  hexDraft.value = nextHex
}

function applyHex(nextHex: string, persist: boolean) {
  const normalized = normalizeHex(nextHex)
  if (!normalized) return
  setHsvFromHex(normalized)
  if (persist) void persistHex(normalized)
}

function onHexCommit() {
  const normalized = normalizeHex(hexDraft.value)
  if (!normalized) {
    hexDraft.value = committedHex.value
    return
  }
  applyHex(normalized, true)
}

function onBrightnessInput() {
  const nextHex = hsvToHex(hsv.value)
  committedHex.value = nextHex
  hexDraft.value = nextHex
  pendingHex = nextHex
  if (saveStaffPrefs) void saveStaffPrefs({ accent_color: nextHex }, { persist: false })
}

function commitSave() {
  void persistHex(committedHex.value)
}

async function persistHex(nextHex: string) {
  pendingHex = ''
  error.value = ''
  saveState.value = 'saving'
  if (!saveStaffPrefs) {
    error.value = 'Could not save color.'
    saveState.value = 'idle'
    return
  }
  const ok = await saveStaffPrefs({ accent_color: nextHex })
  if (ok) {
    saveState.value = 'saved'
  } else {
    error.value = 'Could not save color to your account.'
    saveState.value = 'idle'
  }
}

function drawWheel() {
  const canvas = wheelEl.value
  if (!canvas || wheelDrawn) return
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
        const rgb = hsvToRgb(wheelHue, dist / radius, 1)
        image.data[i] = Math.round(rgb.r)
        image.data[i + 1] = Math.round(rgb.g)
        image.data[i + 2] = Math.round(rgb.b)
        image.data[i + 3] = 255
      }
    }
    wheelBitmap = image
  }

  ctx.putImageData(wheelBitmap, 0, 0)
  wheelDrawn = true
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
  hue.value = (nextHue + 360) % 360
  sat.value = Math.min(1, dist / radius)
  const nextHex = hsvToHex(hsv.value)
  committedHex.value = nextHex
  hexDraft.value = nextHex
  pendingHex = nextHex
  if (saveStaffPrefs) void saveStaffPrefs({ accent_color: nextHex }, { persist: false })
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
  if (pendingHex) void persistHex(pendingHex)
}

function syncFromProfile(accent: string | undefined) {
  const normalized = normalizeHex(accent)
  if (!normalized || normalized === committedHex.value) return
  setHsvFromHex(normalized)
}

watch(open, async (isOpen) => {
  if (!isOpen) return
  await nextTick()
  wheelDrawn = false
  drawWheel()
})

onMounted(() => {
  syncFromProfile(staffUser?.value?.accent_color || DEFAULT_ACCENT)
})

watch(
  () => staffUser?.value?.accent_color,
  (next) => syncFromProfile(next),
)

onBeforeUnmount(() => {
  if (pendingHex) void persistHex(pendingHex)
})
</script>
