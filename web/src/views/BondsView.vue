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
        <button class="refresh-btn" @click="fetchBonds" :disabled="loading">
          {{ loading ? '加载中...' : '刷新' }}
        </button>
      </div>
    </div>

    <div class="search-bar">
      <input
        v-model="searchKeyword"
        type="text"
        placeholder="搜索债券代码或名称..."
        class="search-input"
        @input="handleSearch"
      />
    </div>

    <div v-if="error" class="error-message">
      {{ error }}
    </div>

    <div v-if="loading" class="loading">
      <div class="spinner"></div>
      <span>加载中...</span>
    </div>

    <div v-else-if="filteredBonds.length === 0" class="empty-state">
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
  padding: 20px;
  max-width: 1400px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.page-title {
  font-size: 24px;
  font-weight: 600;
  color: var(--text-primary, #333);
  margin: 0;
}

.header-actions {
  display: flex;
  gap: 12px;
}

.type-select {
  padding: 8px 12px;
  border: 1px solid #d9d9d9;
  border-radius: 6px;
  font-size: 14px;
  background: #fff;
  cursor: pointer;
}

.refresh-btn {
  padding: 8px 16px;
  background: #1890ff;
  color: #fff;
  border: none;
  border-radius: 6px;
  font-size: 14px;
  cursor: pointer;
  transition: background 0.2s;
}

.refresh-btn:hover:not(:disabled) {
  background: #40a9ff;
}

.refresh-btn:disabled {
  background: #ccc;
  cursor: not-allowed;
}

.search-bar {
  margin-bottom: 20px;
}

.search-input {
  width: 100%;
  max-width: 400px;
  padding: 10px 16px;
  border: 1px solid #d9d9d9;
  border-radius: 8px;
  font-size: 14px;
  outline: none;
  transition: border-color 0.2s;
}

.search-input:focus {
  border-color: #1890ff;
}

.error-message {
  padding: 16px;
  background: #fff2f0;
  border: 1px solid #ffccc7;
  border-radius: 8px;
  color: #ff4d4f;
  margin-bottom: 20px;
}

.loading {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 40px;
  color: #666;
}

.spinner {
  width: 24px;
  height: 24px;
  border: 3px solid #f3f3f3;
  border-top: 3px solid #1890ff;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.empty-state {
  text-align: center;
  padding: 60px 20px;
  color: #999;
}

.bonds-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
}
</style>
