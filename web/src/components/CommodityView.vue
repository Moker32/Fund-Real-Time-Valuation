<template>
  <div class="commodity-view">
    <!-- 折线图（选中商品时显示） -->
    <CommodityChart
      v-if="selectedChart"
      :symbol="selectedChart.symbol"
      :name="selectedChart.name"
      :current-price="selectedChart.price"
      :change="selectedChart.change"
      :change-percent="selectedChart.changePercent"
      :high="selectedChart.high"
      :low="selectedChart.low"
      :chart-history="store.selectedChartHistory"
      :chart-height="160"
      @close="store.selectChartSymbol(null)"
    />

    <!-- 分类 Tab -->
    <CommodityTabs
      :categories="categoryList"
      :active-category="store.activeCategory"
      @category-select="handleCategorySelect"
    />

    <!-- 商品列表 -->
    <div class="commodity-content">
      <div v-if="store.loading" class="loading-state">
        <div class="loading-spinner"></div>
        <span>加载中...</span>
      </div>

      <div v-else-if="store.error" class="error-state">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="10"/>
          <path d="M12 8v4M12 16h.01"/>
        </svg>
        <span>{{ store.error }}</span>
        <button class="retry-button" @click="store.retry()">
          重试
        </button>
      </div>

      <div v-else-if="activeCategoryData && activeCategoryData.commodities.length === 0" class="empty-state">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="10"/>
          <path d="M8 15s1.5-2 4-2 4 2 4 2M9 9h.01M15 9h.01"/>
        </svg>
        <span>该分类暂无数据</span>
      </div>

      <div v-else-if="activeCommodities.length === 0" class="empty-state">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="10"/>
          <path d="M8 15s1.5-2 4-2 4 2 4 2M9 9h.01M15 9h.01"/>
        </svg>
        <span>暂无商品数据</span>
      </div>

      <div v-else class="commodity-grid">
        <CommodityCard
          v-for="commodity in activeCommodities"
          :key="commodity.symbol"
          :commodity="commodity"
          @click="store.selectChartSymbol(commodity.symbol)"
        />
      </div>
    </div>

    <!-- 更新时间 -->
    <div v-if="store.lastUpdated" class="last-updated">
      更新时间: {{ store.lastUpdated }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useCommodityStore } from '@/stores/commodityStore';
import CommodityTabs from './CommodityTabs.vue';
import CommodityCard from './CommodityCard.vue';
import CommodityChart from './CommodityChart.vue';

const store = useCommodityStore();

// 当前选中显示折线图的商品
const selectedChart = computed(() => {
  if (!store.selectedChartSymbol) return null;
  return store.commodities.find(c => c.symbol === store.selectedChartSymbol) || null;
});

// eslint-disable-next-line no-useless-assignment
const categoryList = computed(() => store.categoryList);

// eslint-disable-next-line no-useless-assignment
const activeCategoryData = computed(() => store.activeCategoryData);

// eslint-disable-next-line no-useless-assignment
const activeCommodities = computed(() => store.activeCommodities);

function handleCategorySelect(categoryId: string) {
  store.setActiveCategory(categoryId);
}
</script>

<style lang="scss" scoped>
.commodity-view {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
  width: 100%;
}

.commodity-content {
  min-height: 200px;
}

.loading-state,
.error-state,
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--spacing-md);
  padding: var(--spacing-xl);
  color: var(--color-text-tertiary);

  svg {
    width: 48px;
    height: 48px;
    opacity: 0.5;
  }
}

.loading-spinner {
  width: 32px;
  height: 32px;
  border: 3px solid var(--color-border);
  border-top-color: var(--color-primary);
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.error-state {
  color: var(--color-fall);

  svg {
    color: var(--color-fall);
  }
}

.retry-button {
  padding: var(--spacing-xs) var(--spacing-md);
  background: var(--color-primary);
  border: none;
  border-radius: var(--radius-md);
  color: white;
  font-size: var(--font-size-sm);
  cursor: pointer;
  transition: background var(--transition-fast);

  &:hover {
    background: var(--color-primary-hover);
  }
}

.commodity-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: var(--spacing-md);

  @media (min-width: 640px) {
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  }
}

/* Responsive */
@media (max-width: 768px) {
  .commodity-view {
    gap: var(--spacing-sm);
  }

  .loading-state,
  .error-state,
  .empty-state {
    padding: var(--spacing-lg);
  }

  .last-updated {
    text-align: left;
    font-size: var(--font-size-xs);
  }
}

.last-updated {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
  text-align: right;
  padding-top: var(--spacing-sm);
}
</style>
