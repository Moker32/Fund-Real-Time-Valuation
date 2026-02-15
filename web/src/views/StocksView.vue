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
      <div
        v-for="stock in stockStore.stocks"
        :key="stock.code"
        class="stock-card"
        :class="{ rising: stock.change_pct > 0, falling: stock.change_pct < 0 }"
      >
        <div class="stock-header">
          <div class="stock-info">
            <span class="stock-name">{{ stock.name }}</span>
            <span class="stock-code">{{ stock.code }}</span>
          </div>
          <button @click="removeStock(stock.code)" class="btn-remove">×</button>
        </div>
        <div class="stock-price">
          <span class="price">{{ stock.price.toFixed(2) }}</span>
          <span class="change" :class="{ positive: stock.change > 0, negative: stock.change < 0 }">
            {{ stock.change > 0 ? '+' : '' }}{{ stock.change.toFixed(2) }}
            ({{ stock.change_pct > 0 ? '+' : '' }}{{ stock.change_pct.toFixed(2) }}%)
          </span>
        </div>
        <div class="stock-details">
          <div class="detail-row">
            <span class="label">开盘</span>
            <span class="value">{{ stock.open.toFixed(2) }}</span>
          </div>
          <div class="detail-row">
            <span class="label">最高</span>
            <span class="value">{{ stock.high.toFixed(2) }}</span>
          </div>
          <div class="detail-row">
            <span class="label">最低</span>
            <span class="value">{{ stock.low.toFixed(2) }}</span>
          </div>
          <div class="detail-row">
            <span class="label">成交量</span>
            <span class="value">{{ stock.volume }}</span>
          </div>
        </div>
      </div>
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
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
}

.stock-card {
  background: var(--color-bg-secondary, #f9fafb);
  border-radius: 8px;
  padding: 16px;
  border: 1px solid var(--color-border, #e5e7eb);
}

.stock-card.rising {
  border-left: 3px solid #ef4444;
}

.stock-card.falling {
  border-left: 3px solid #22c55e;
}

.stock-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 12px;
}

.stock-info {
  display: flex;
  flex-direction: column;
}

.stock-name {
  font-weight: 600;
  font-size: 16px;
  color: var(--color-text, #1f2937);
}

.stock-code {
  font-size: 12px;
  color: var(--color-text-tertiary, #9ca3af);
}

.btn-remove {
  background: none;
  border: none;
  font-size: 20px;
  color: var(--color-text-tertiary, #9ca3af);
  cursor: pointer;
  padding: 0 4px;
}

.btn-remove:hover {
  color: #ef4444;
}

.stock-price {
  margin-bottom: 12px;
}

.price {
  font-size: 24px;
  font-weight: 700;
  color: var(--color-text, #1f2937);
}

.change {
  display: block;
  font-size: 14px;
  margin-top: 4px;
}

.change.positive {
  color: #ef4444;
}

.change.negative {
  color: #22c55e;
}

.stock-details {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8px;
}

.detail-row {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
}

.label {
  color: var(--color-text-tertiary, #9ca3af);
}

.value {
  color: var(--color-text, #1f2937);
  font-weight: 500;
}

.empty-state,
.loading {
  text-align: center;
  padding: 40px;
  color: var(--color-text-tertiary, #9ca3af);
}
</style>
