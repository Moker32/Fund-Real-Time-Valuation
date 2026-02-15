<script setup lang="ts">
import { ref, onMounted, computed } from 'vue';
import BondCard from '@/components/BondCard.vue';

interface Bond {
  code: string;
  name: string | null;
  price: number | null;
  change: number | null;
  change_pct: number | null;
  volume: number | null;
  amount: number | null;
}

const bonds = ref<Bond[]>([]);
const loading = ref(false);
const error = ref<string | null>(null);
const searchKeyword = ref('');
const selectedType = ref('cbond');

const bondTypes = [
  { value: 'cbond', label: '可转债' },
  { value: 'bond_china', label: '中国债券' },
];

const filteredBonds = computed(() => {
  if (!searchKeyword.value) return bonds.value;
  const keyword = searchKeyword.value.toUpperCase();
  return bonds.value.filter(
    (bond) =>
      bond.code.toUpperCase().includes(keyword) ||
      (bond.name && bond.name.toUpperCase().includes(keyword))
  );
});

async function fetchBonds() {
  loading.value = true;
  error.value = null;

  try {
    const response = await fetch(`/api/bonds?bond_type=${selectedType.value}`);
    if (!response.ok) {
      throw new Error('获取债券数据失败');
    }
    const data = await response.json();
    bonds.value = data.bonds || [];
  } catch (e) {
    error.value = e instanceof Error ? e.message : '未知错误';
    console.error('获取债券数据失败:', e);
  } finally {
    loading.value = false;
  }
}

function handleSearch() {
  // 搜索通过 computed 属性自动过滤
}

onMounted(() => {
  fetchBonds();
});
</script>

<template>
  <div class="bonds-view">
    <div class="page-header">
      <h1 class="page-title">债券行情</h1>
      <div class="header-actions">
        <select v-model="selectedType" class="type-select" @change="fetchBonds">
          <option v-for="type in bondTypes" :key="type.value" :value="type.value">
            {{ type.label }}
          </option>
        </select>
        <button class="refresh-btn" :disabled="loading" @click="fetchBonds">
          <svg v-if="!loading" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M23 4v6h-6M1 20v-6h6M3.51 9a9 9 0 0114.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0020.49 15"/>
          </svg>
          <span v-if="loading" class="spinner-small"></span>
          {{ loading ? '加载中...' : '刷新' }}
        </button>
      </div>
    </div>

    <div class="search-bar">
      <div class="search-input-wrapper">
        <svg class="search-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="11" cy="11" r="8"/>
          <path d="M21 21l-4.35-4.35"/>
        </svg>
        <input
          v-model="searchKeyword"
          type="text"
          placeholder="搜索债券代码或名称..."
          class="search-input"
          @input="handleSearch"
        />
      </div>
    </div>

    <div v-if="error" class="error-message">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="12" cy="12" r="10"/>
        <path d="M12 8v4M12 16h.01"/>
      </svg>
      <span>{{ error }}</span>
      <button @click="fetchBonds">重试</button>
    </div>

    <div v-if="loading" class="loading">
      <div class="spinner"></div>
      <span>加载中...</span>
    </div>

    <div v-else-if="filteredBonds.length === 0" class="empty-state">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <path d="M3 3V21H21"/>
        <path d="M7 14L11 10L15 12L21 6"/>
      </svg>
      <p>暂无债券数据</p>
    </div>

    <div v-else class="bonds-grid">
      <BondCard
        v-for="bond in filteredBonds"
        :key="bond.code"
        :code="bond.code"
        :name="bond.name || undefined"
        :price="bond.price ?? undefined"
        :change="bond.change ?? undefined"
        :change-pct="bond.change_pct ?? undefined"
        :volume="bond.volume ?? undefined"
        :amount="bond.amount ?? undefined"
      />
    </div>
  </div>
</template>

<style scoped>
.bonds-view {
  padding: var(--spacing-lg);
  max-width: 1400px;
  margin: 0 auto;
  animation: fadeIn var(--transition-normal);
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-lg);
}

.page-title {
  font-size: var(--font-size-xl);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
  margin: 0;
}

.header-actions {
  display: flex;
  gap: var(--spacing-md);
}

.type-select {
  padding: var(--spacing-sm) var(--spacing-md);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  font-size: var(--font-size-md);
  background: var(--color-bg-card);
  color: var(--color-text-primary);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.type-select:hover {
  border-color: var(--color-border-light);
}

.type-select:focus {
  outline: none;
  border-color: var(--color-primary, #1890ff);
}

.refresh-btn {
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
  padding: var(--spacing-sm) var(--spacing-md);
  background: var(--color-primary, #1890ff);
  color: #fff;
  border: none;
  border-radius: var(--radius-md);
  font-size: var(--font-size-md);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.refresh-btn:hover:not(:disabled) {
  opacity: 0.9;
  transform: translateY(-1px);
}

.refresh-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.refresh-btn svg {
  width: 16px;
  height: 16px;
}

.spinner-small {
  width: 14px;
  height: 14px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.search-bar {
  margin-bottom: var(--spacing-lg);
}

.search-input-wrapper {
  position: relative;
  max-width: 400px;
}

.search-icon {
  position: absolute;
  left: var(--spacing-md);
  top: 50%;
  transform: translateY(-50%);
  width: 18px;
  height: 18px;
  color: var(--color-text-tertiary);
  pointer-events: none;
}

.search-input {
  width: 100%;
  padding: var(--spacing-sm) var(--spacing-md);
  padding-left: 44px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  font-size: var(--font-size-md);
  background: var(--color-bg-card);
  color: var(--color-text-primary);
  outline: none;
  transition: all var(--transition-fast);
}

.search-input::placeholder {
  color: var(--color-text-tertiary);
}

.search-input:focus {
  border-color: var(--color-primary, #1890ff);
  box-shadow: 0 0 0 2px rgba(24, 144, 255, 0.1);
}

.error-message {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-md);
  background: var(--color-fall-bg);
  border: 1px solid var(--color-fall);
  border-radius: var(--radius-md);
  color: var(--color-fall);
  margin-bottom: var(--spacing-lg);
}

.error-message svg {
  width: 20px;
  height: 20px;
  flex-shrink: 0;
}

.error-message button {
  margin-left: auto;
  padding: var(--spacing-xs) var(--spacing-md);
  background: var(--color-fall);
  color: #fff;
  border: none;
  border-radius: var(--radius-sm);
  cursor: pointer;
}

.loading {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--spacing-md);
  padding: var(--spacing-2xl);
  color: var(--color-text-secondary);
}

.spinner {
  width: 24px;
  height: 24px;
  border: 3px solid var(--color-bg-tertiary);
  border-top-color: var(--color-primary, #1890ff);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--spacing-2xl);
  color: var(--color-text-tertiary);
}

.empty-state svg {
  width: 48px;
  height: 48px;
  opacity: 0.5;
  margin-bottom: var(--spacing-md);
}

.bonds-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: var(--spacing-md);
}
</style>
