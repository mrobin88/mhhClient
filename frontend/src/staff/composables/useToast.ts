import { ref } from 'vue'

export type ToastKind = 'success' | 'error' | 'info'

export interface ToastItem {
  id: number
  message: string
  kind: ToastKind
}

const toasts = ref<ToastItem[]>([])
let nextId = 1

export function useToast() {
  function push(message: string, kind: ToastKind = 'info', ms = 4500) {
    const id = nextId++
    toasts.value = [...toasts.value, { id, message, kind }]
    window.setTimeout(() => {
      toasts.value = toasts.value.filter((t) => t.id !== id)
    }, ms)
  }

  function success(message: string) {
    push(message, 'success')
  }

  function error(message: string) {
    push(message, 'error', 6000)
  }

  return { toasts, push, success, error }
}
