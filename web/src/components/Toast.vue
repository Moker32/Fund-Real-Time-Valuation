<script setup lang="ts">
import { ref, computed, watch } from 'vue'

export type ToastType = 'success' | 'error' | 'warning' | 'info'

export interface Toast {
  id: number
  type: ToastType
  message: string
  duration?: number
}

const props = defineProps<{
  toasts: Toast[]
}>()

const emit = defineEmits<{
  (e: 'close', id: number): void
}>()

const getIcon = (type: ToastType) => {
  const icons = {
    success: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>`,
    error: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>`,
    warning: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>`,
    info: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>`,
  }
  return icons[type]
}

const getTypeClass = (type: ToastType) => {
  return `toast-${type}`
}
</script>

<template>
  <div class="toast-container">
    <TransitionGroup name="toast">
      <div
        v-for="toast in toasts"
        :key="toast.id"
        :class="['toast', getTypeClass(toast.type)]"
        role="alert"
      >
        <span class="toast-icon" v-html="getIcon(toast.type)"></span>
        <span class="toast-message">{{ toast.message }}</span>
        <button class="toast-close" @click="emit('close', toast.id)" aria-label="关闭">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="18" y1="6" x2="6" y2="18"/>
            <line x1="6" y1="6" x2="18" y2="18"/>
          </svg>
        </button>
      </div>
    </TransitionGroup>
  </div>
</template>

<style lang="scss" scoped>
.toast-container {
  position: fixed;
  top: 20px;
  right: 20px;
  z-index: 9999;
  display: flex;
  flex-direction: column;
  gap: 10px;
  max-width: 400px;
}

.toast {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  background: #fff;
  min-width: 280px;

  .toast-icon {
    flex-shrink: 0;
    width: 20px;
    height: 20px;

    :deep(svg) {
      width: 100%;
      height: 100%;
    }
  }

  .toast-message {
    flex: 1;
    font-size: 14px;
    color: #333;
    line-height: 1.4;
  }

  .toast-close {
    flex-shrink: 0;
    width: 20px;
    height: 20px;
    padding: 0;
    border: none;
    background: transparent;
    cursor: pointer;
    color: #999;
    transition: color 0.2s;

    &:hover {
      color: #333;
    }

    svg {
      width: 100%;
      height: 100%;
    }
  }

  &.toast-success {
    border-left: 4px solid #52c41a;

    .toast-icon {
      color: #52c41a;
    }
  }

  &.toast-error {
    border-left: 4px solid #ff4d4f;

    .toast-icon {
      color: #ff4d4f;
    }
  }

  &.toast-warning {
    border-left: 4px solid #faad14;

    .toast-icon {
      color: #faad14;
    }
  }

  &.toast-info {
    border-left: 4px solid #1890ff;

    .toast-icon {
      color: #1890ff;
    }
  }
}

.toast-enter-active,
.toast-leave-active {
  transition: all 0.3s ease;
}

.toast-enter-from {
  opacity: 0;
  transform: translateX(100%);
}

.toast-leave-to {
  opacity: 0;
  transform: translateX(100%);
}
</style>
