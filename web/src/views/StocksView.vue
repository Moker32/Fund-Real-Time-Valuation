<template>
  <div class="stocks-view">
    <div class="page-header">
      <h1 class="page-title">股票行情</h1>
      <div class="header-actions">
        <button @click="refresh" class="btn btn-primary" :disabled="stockStore.loading">
          {{ stockStore.loading ? '加载中...' : '刷新' }}
        </button>
      </div>
    </div>

    <!-- 添加自选股 -->
    <div class="add-stock">
      <input
        v-model="newStockCode"
        type="text"
        placeholder="输入股票代码 (如: sh600519, AAPL)"
        class="input"
        @keyup.enter="addStock"
      />
      <button @click="addStock" class="btn btn-secondary">添加</button>
    </div>

    <!-- 错误提示 -->
    <div v-if="stockStore.error" class="error-message">
      {{ stockStore.error }}
    </div>

    <!-- 股票列表 -->
    <div class="stock-list" v-if="stockStore.stocks.length > 0">
      <StockCard
        v-for="stock in stockStore.stocks"
        :key="stock.code"
        :stock="stock"
        @remove="removeStock"
      />
    </div>

    <!-- 空状态 -->
    <div v-else-if="!stockStore.loading" class="empty-state">
      <p>暂无自选股，请添加股票代码</p>
    </div>

    <!-- 加载中 -->
    <div v-if="stockStore.loading" class="loading">
      加载中...
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { useStockStore } from '@/stores/stockStore';
import StockCard from '@/components/StockCard.vue';

const stockStore = useStockStore();
const newStockCode = ref('');

onMounted(() => {
  stockStore.fetchStocks();
});

async function refresh() {
  await stockStore.fetchStocks();
}

function addStock() {
  const code = newStockCode.value.trim().toUpperCase();
  if (code) {
    stockStore.addToWatchlist(code);
    newStockCode.value = '';
    stockStore.fetchStocks();
  }
}

function removeStock(code: string) {
  stockStore.removeFromWatchlist(code);
}
</script>

<style scoped>
.stocks-view {
  padding: 16px;
  max-width: 1200px;
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
  margin: 0;
}

.header-actions {
  display: flex;
  gap: 8px;
}

.btn {
  padding: 8px 16px;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  transition: opacity 0.2s;
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-primary {
  background: var(--color-primary, #3b82f6);
  color: white;
}

.btn-secondary {
  background: var(--color-secondary, #6b7280);
  color: white;
}

.add-stock {
  display: flex;
  gap: 8px;
  margin-bottom: 20px;
}

.input {
  flex: 1;
  padding: 10px 14px;
  border: 1px solid var(--color-border, #e5e7eb);
  border-radius: 6px;
  font-size: 14px;
  background: var(--color-bg, #fff);
  color: var(--color-text, #1f2937);
}

.input:focus {
  outline: none;
  border-color: var(--color-primary, #3b82f6);
}

.error-message {
  padding: 12px;
  background: #fee2e2;
  color: #dc2626;
  border-radius: 6px;
  margin-bottom: 16px;
}

.stock-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 16px;
}

.empty-state,
.loading {
  text-align: center;
  padding: 40px;
  color: var(--color-text-tertiary, #9ca3af);
}
</style>
