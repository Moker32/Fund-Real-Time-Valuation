<template>
  <div class="commodities-view">
    <!-- Header -->
    <div class="view-header">
      <h2 class="section-title">大宗商品行情</h2>
    </div>

    <!-- Commodity View with Categories -->
    <CommodityView />

    <!-- Quick Stats (保留原有统计) -->
    <div v-if="commodityStore.commodities.length > 0" class="quick-stats">
      <div class="stats-card">
        <span class="stats-label">上涨</span>
        <span class="stats-value rising">{{ commodityStore.risingCommodities.length }}</span>
      </div>
      <div class="stats-card">
        <span class="stats-label">下跌</span>
        <span class="stats-value falling">{{ commodityStore.fallingCommodities.length }}</span>
      </div>
      <div class="stats-card">
        <span class="stats-label">持平</span>
        <span class="stats-value neutral">{{ commodityStore.commodities.length - commodityStore.risingCommodities.length - commodityStore.fallingCommodities.length }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue';
import { useCommodityStore } from '@/stores/commodityStore';
import CommodityView from '@/components/CommodityView.vue';

const commodityStore = useCommodityStore();

onMounted(() => {
  // 只在数据为空时强制加载
  if (commodityStore.categories.length === 0) {
    commodityStore.fetchCategories({ force: true });
  }
});
</script>

<style lang="scss" scoped>
.commodities-view {
  animation: fadeIn var(--transition-normal);
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

.view-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--spacing-lg);
}

.section-title {
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}

.quick-stats {
  display: flex;
  gap: var(--spacing-md);
  margin-top: var(--spacing-xl);
  padding-top: var(--spacing-lg);
  border-top: 1px solid var(--color-divider);
}

.stats-card {
  flex: 1;
  background: var(--color-bg-secondary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: var(--spacing-md);
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.stats-label {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

.stats-value {
  font-size: var(--font-size-xl);
  font-weight: var(--font-weight-bold);
  font-family: var(--font-mono);

  &.rising {
    color: var(--color-rise);
  }

  &.falling {
    color: var(--color-fall);
  }

  &.neutral {
    color: var(--color-neutral);
  }
}
</style>
