<template>
  <div class="settings-view">
    <h2 class="page-title">设置</h2>

    <div class="settings-section">
      <h3 class="section-title">显示设置</h3>

      <div class="setting-item">
        <div class="setting-info">
          <span class="setting-label">自动刷新</span>
          <span class="setting-description">自动获取最新数据</span>
        </div>
        <label class="toggle">
          <input type="checkbox" v-model="autoRefresh" />
          <span class="toggle-slider"></span>
        </label>
      </div>

      <div class="setting-item" v-if="autoRefresh">
        <div class="setting-info">
          <span class="setting-label">刷新间隔</span>
          <span class="setting-description">每隔 {{ refreshInterval }} 秒刷新数据</span>
        </div>
        <select v-model="refreshInterval" class="setting-select">
          <option :value="10">10 秒</option>
          <option :value="30">30 秒</option>
          <option :value="60">1 分钟</option>
          <option :value="300">5 分钟</option>
        </select>
      </div>
    </div>

    <div class="settings-section">
      <h3 class="section-title">数据设置</h3>

      <div class="setting-item">
        <div class="setting-info">
          <span class="setting-label">API 地址</span>
          <span class="setting-description">后端服务地址</span>
        </div>
        <input
          type="text"
          v-model="apiUrl"
          class="setting-input"
          placeholder="http://localhost:8000"
        />
      </div>
    </div>

    <div class="settings-section">
      <h3 class="section-title">关于</h3>

      <div class="about-info">
        <p class="app-name">FundVue</p>
        <p class="app-version">版本 1.0.0</p>
        <p class="app-description">基金实时估值监控 Web 前端</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue';
import { useFundStore } from '@/stores/fundStore';

const fundStore = useFundStore();

const autoRefresh = ref(fundStore.autoRefresh ?? true);
const refreshInterval = ref(fundStore.refreshInterval || 30);
const apiUrl = ref(import.meta.env.VITE_API_URL || 'http://localhost:8000');

watch(autoRefresh, (value) => {
  fundStore.setAutoRefresh?.(value);
});

watch(refreshInterval, (value) => {
  fundStore.setRefreshInterval?.(value);
});
</script>

<style lang="scss" scoped>
.settings-view {
  max-width: 600px;
  animation: fadeIn var(--transition-normal);
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

.page-title {
  font-size: var(--font-size-2xl);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
  margin-bottom: var(--spacing-xl);
}

.settings-section {
  background: var(--color-bg-secondary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: var(--spacing-lg);
  margin-bottom: var(--spacing-lg);
}

.section-title {
  font-size: var(--font-size-md);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
  margin-bottom: var(--spacing-md);
  padding-bottom: var(--spacing-sm);
  border-bottom: 1px solid var(--color-divider);
}

.setting-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--spacing-md) 0;
}

.setting-item:not(:last-child) {
  border-bottom: 1px solid var(--color-divider);
}

.setting-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.setting-label {
  font-size: var(--font-size-md);
  font-weight: var(--font-weight-medium);
  color: var(--color-text-primary);
}

.setting-description {
  font-size: var(--font-size-sm);
  color: var(--color-text-tertiary);
}

/* Toggle Switch */
.toggle {
  position: relative;
  display: inline-block;
  width: 48px;
  height: 28px;
}

.toggle input {
  opacity: 0;
  width: 0;
  height: 0;
}

.toggle-slider {
  position: absolute;
  cursor: pointer;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: var(--color-bg-tertiary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-full);
  transition: all var(--transition-fast);
}

.toggle-slider::before {
  position: absolute;
  content: "";
  height: 22px;
  width: 22px;
  left: 2px;
  bottom: 2px;
  background: var(--color-text-tertiary);
  border-radius: 50%;
  transition: all var(--transition-fast);
}

.toggle input:checked + .toggle-slider {
  background: var(--color-rise);
  border-color: var(--color-rise);
}

.toggle input:checked + .toggle-slider::before {
  transform: translateX(20px);
  background: white;
}

/* Select & Input */
.setting-select,
.setting-input {
  padding: var(--spacing-sm) var(--spacing-md);
  background: var(--color-bg-tertiary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  color: var(--color-text-primary);
  font-size: var(--font-size-sm);
  outline: none;
  transition: all var(--transition-fast);

  &:focus {
    border-color: var(--color-text-secondary);
  }
}

.setting-select {
  cursor: pointer;
  min-width: 100px;
}

.setting-input {
  min-width: 250px;
}

/* About Section */
.about-info {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
}

.app-name {
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}

.app-version {
  font-size: var(--font-size-sm);
  color: var(--color-text-tertiary);
}

.app-description {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  margin-top: var(--spacing-sm);
}
</style>
