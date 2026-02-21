import { ref, readonly } from 'vue'
import type { Toast, ToastType } from '@/components/Toast.vue'

const toasts = ref<Toast[]>([])
let nextId = 0

export function useToast() {
  const addToast = (type: ToastType, message: string, duration = 3000) => {
    const id = nextId++
    const toast: Toast = { id, type, message, duration }
    toasts.value.push(toast)

    if (duration > 0) {
      setTimeout(() => {
        removeToast(id)
      }, duration)
    }

    return id
  }

  const removeToast = (id: number) => {
    const index = toasts.value.findIndex(t => t.id === id)
    if (index > -1) {
      toasts.value.splice(index, 1)
    }
  }

  const success = (message: string, duration?: number) => {
    return addToast('success', message, duration)
  }

  const error = (message: string, duration?: number) => {
    return addToast('error', message, duration ?? 5000)
  }

  const warning = (message: string, duration?: number) => {
    return addToast('warning', message, duration)
  }

  const info = (message: string, duration?: number) => {
    return addToast('info', message, duration)
  }

  const clear = () => {
    toasts.value = []
  }

  return {
    toasts: readonly(toasts),
    addToast,
    removeToast,
    success,
    error,
    warning,
    info,
    clear,
  }
}
