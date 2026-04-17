<script setup lang="ts">
import { ref, onErrorCaptured } from 'vue'

interface Props {
  fallbackMessage?: string
  showDetails?: boolean
}

withDefaults(defineProps<Props>(), {
  fallbackMessage: '组件加载失败',
  showDetails: false,
})

const hasError = ref(false)
const errorMessage = ref('')
const errorInfo = ref('')

onErrorCaptured((err, instance, info) => {
  hasError.value = true
  errorMessage.value = err.message || String(err)
  errorInfo.value = info

  console.error('[ErrorBoundary] Caught error:', err)
  console.error('[ErrorBoundary] Component:', instance)
  console.error('[ErrorBoundary] Info:', info)

  return false // 阻止错误继续传播
})

const handleRetry = () => {
  hasError.value = false
  errorMessage.value = ''
  errorInfo.value = ''
}
</script>

<template>
  <!-- 正常状态：渲染 slot 内容 -->
  <slot v-if="!hasError"></slot>

  <!-- 错误状态：渲染 fallback -->
  <div v-else class="error-fallback">
    <div class="error-icon">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="12" cy="12" r="10"/>
        <line x1="12" y1="8" x2="12" y2="12"/>
        <line x1="12" y1="16" x2="12.01" y2="16"/>
      </svg>
    </div>
    <p class="error-message">{{ fallbackMessage }}</p>
    <p v-if="showDetails && errorMessage" class="error-details">
      {{ errorMessage }}
    </p>
    <button class="retry-button" @click="handleRetry">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M23 4V6H19"/>
        <path d="M1 20V18H5"/>
        <path d="M3.5 14.5C3.5 10.5 6.5 7 10.5 7H14.5"/>
        <path d="M20.5 9.5C20.5 13.5 17.5 17 13.5 17H9.5"/>
      </svg>
      重试
    </button>
  </div>
</template>

<style lang="scss" scoped>
.error-fallback {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  min-height: 200px;
  gap: 16px;

  .error-icon {
    width: 48px;
    height: 48px;
    color: #ff4d4f;

    svg {
      width: 100%;
      height: 100%;
    }
  }

  .error-message {
    color: #666;
    font-size: 14px;
    text-align: center;
  }

  .error-details {
    color: #999;
    font-size: 12px;
    text-align: center;
    max-width: 300px;
    word-break: break-all;
  }

  .retry-button {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 8px 16px;
    background: #1890ff;
    color: #fff;
    border: none;
    border-radius: 6px;
    cursor: pointer;
    font-size: 14px;
    transition: background 0.2s;

    &:hover {
      background: #40a9ff;
    }

    svg {
      width: 16px;
      height: 16px;
    }
  }
}
</style>
