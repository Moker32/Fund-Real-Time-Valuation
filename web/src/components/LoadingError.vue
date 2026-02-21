<script setup lang="ts">
defineProps<{
  loading?: boolean
  error?: string | null
  empty?: boolean
  emptyText?: string
  loadingText?: string
  errorText?: string
}>()

const emit = defineEmits<{
  (e: 'retry'): void
}>()
</script>

<template>
  <div class="loading-error-container">
    <!-- Loading State -->
    <div v-if="loading" class="loading-state">
      <div class="loading-spinner"></div>
      <p class="loading-text">{{ loadingText || '加载中...' }}</p>
    </div>

    <!-- Error State -->
    <div v-else-if="error" class="error-state">
      <div class="error-icon">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="10"/>
          <line x1="12" y1="8" x2="12" y2="12"/>
          <line x1="12" y1="16" x2="12.01" y2="16"/>
        </svg>
      </div>
      <p class="error-message">{{ errorText || error }}</p>
      <button class="retry-button" @click="emit('retry')">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M23 4V6H19"/>
          <path d="M1 20V18H5"/>
          <path d="M3.5 14.5C3.5 10.5 6.5 7 10.5 7H14.5"/>
          <path d="M20.5 9.5C20.5 13.5 17.5 17 13.5 17H9.5"/>
        </svg>
        重试
      </button>
    </div>

    <!-- Empty State -->
    <div v-else-if="empty" class="empty-state">
      <div class="empty-icon">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/>
          <polyline points="13 2 13 9 20 9"/>
        </svg>
      </div>
      <p class="empty-text">{{ emptyText || '暂无数据' }}</p>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.loading-error-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  min-height: 200px;
}

.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;

  .loading-spinner {
    width: 40px;
    height: 40px;
    border: 3px solid #f3f3f3;
    border-top: 3px solid #1890ff;
    border-radius: 50%;
    animation: spin 1s linear infinite;
  }

  .loading-text {
    color: #666;
    font-size: 14px;
  }
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.error-state {
  display: flex;
  flex-direction: column;
  align-items: center;
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
    max-width: 300px;
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

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;

  .empty-icon {
    width: 48px;
    height: 48px;
    color: #999;

    svg {
      width: 100%;
      height: 100%;
    }
  }

  .empty-text {
    color: #999;
    font-size: 14px;
  }
}
</style>
