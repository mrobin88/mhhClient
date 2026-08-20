export const DEFAULT_ACCENT = '#EA580C'

export const DESK_PRESETS = [
  { hex: '#EA580C', label: 'Hall orange' },
  { hex: '#CA8A04', label: 'Safety yellow' },
  { hex: '#166534', label: 'Forest' },
  { hex: '#0F766E', label: 'Teal' },
  { hex: '#1E3A8A', label: 'Navy' },
  { hex: '#9D174D', label: 'Berry' },
  { hex: '#7C2D12', label: 'Walnut' },
  { hex: '#44403C', label: 'Slate' },
] as const

export type Hsv = { h: number; s: number; v: number }
export type Rgb = { r: number; g: number; b: number }

export function normalizeHex(value: string | null | undefined): string {
  const raw = String(value || '').trim()
  if (/^#[0-9A-Fa-f]{6}$/.test(raw)) return `#${raw.slice(1).toUpperCase()}`
  if (/^[0-9A-Fa-f]{6}$/.test(raw)) return `#${raw.toUpperCase()}`
  return ''
}

export function parseHex(hex: string): Rgb | null {
  const normalized = normalizeHex(hex)
  if (!normalized) return null
  return {
    r: parseInt(normalized.slice(1, 3), 16),
    g: parseInt(normalized.slice(3, 5), 16),
    b: parseInt(normalized.slice(5, 7), 16),
  }
}

export function rgbToHex(r: number, g: number, b: number): string {
  const toByte = (channel: number) =>
    Math.max(0, Math.min(255, Math.round(channel)))
      .toString(16)
      .padStart(2, '0')
  return `#${toByte(r)}${toByte(g)}${toByte(b)}`.toUpperCase()
}

export function hsvToRgb(h: number, s: number, v: number): Rgb {
  const chroma = v * s
  const x = chroma * (1 - Math.abs(((h / 60) % 2) - 1))
  const match = v - chroma
  let r = 0
  let g = 0
  let b = 0
  if (h < 60) [r, g, b] = [chroma, x, 0]
  else if (h < 120) [r, g, b] = [x, chroma, 0]
  else if (h < 180) [r, g, b] = [0, chroma, x]
  else if (h < 240) [r, g, b] = [0, x, chroma]
  else if (h < 300) [r, g, b] = [x, 0, chroma]
  else [r, g, b] = [chroma, 0, x]
  return {
    r: (r + match) * 255,
    g: (g + match) * 255,
    b: (b + match) * 255,
  }
}

export function rgbToHsv(r: number, g: number, b: number): Hsv {
  const red = r / 255
  const green = g / 255
  const blue = b / 255
  const max = Math.max(red, green, blue)
  const min = Math.min(red, green, blue)
  const delta = max - min
  let h = 0
  if (delta !== 0) {
    if (max === red) h = ((green - blue) / delta) % 6
    else if (max === green) h = (blue - red) / delta + 2
    else h = (red - green) / delta + 4
    h *= 60
    if (h < 0) h += 360
  }
  return { h, s: max === 0 ? 0 : delta / max, v: max }
}

export function hexToHsv(hex: string): Hsv {
  const rgb = parseHex(hex) || parseHex(DEFAULT_ACCENT)!
  return rgbToHsv(rgb.r, rgb.g, rgb.b)
}

export function hsvToHex(hsv: Hsv): string {
  const rgb = hsvToRgb(hsv.h, hsv.s, hsv.v)
  return rgbToHex(rgb.r, rgb.g, rgb.b)
}

export function darkenHex(hex: string, amount = 0.18): string {
  const rgb = parseHex(hex)
  if (!rgb) return DEFAULT_ACCENT
  return rgbToHex(rgb.r * (1 - amount), rgb.g * (1 - amount), rgb.b * (1 - amount))
}

export function mixWithWhite(hex: string, whiteAmount = 0.9): string {
  const rgb = parseHex(hex)
  if (!rgb) return '#FFF7ED'
  return rgbToHex(
    rgb.r + (255 - rgb.r) * whiteAmount,
    rgb.g + (255 - rgb.g) * whiteAmount,
    rgb.b + (255 - rgb.b) * whiteAmount,
  )
}

function relativeLuminance(hex: string): number {
  const rgb = parseHex(hex)
  if (!rgb) return 0
  const toLinear = (channel: number) => {
    const value = channel / 255
    return value <= 0.03928 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4
  }
  return 0.2126 * toLinear(rgb.r) + 0.7152 * toLinear(rgb.g) + 0.0722 * toLinear(rgb.b)
}

export function contrastText(hex: string): string {
  return relativeLuminance(hex) > 0.55 ? '#1C1917' : '#FFFFFF'
}

export function accentThemeVars(hex: string | null | undefined): Record<string, string> {
  const color = normalizeHex(hex) || DEFAULT_ACCENT
  const rgb = parseHex(color)!
  return {
    '--staff-accent': color,
    '--staff-accent-dark': darkenHex(color),
    '--staff-accent-soft': mixWithWhite(color, 0.9),
    '--staff-accent-rgb': `${rgb.r}, ${rgb.g}, ${rgb.b}`,
    '--staff-on-accent': contrastText(color),
  }
}
