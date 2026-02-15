<script setup lang="ts">
import { computed, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { useFundStore } from '@/stores/fundStore';
import { useCommodityStore } from '@/stores/commodityStore';
import { useIndexStore } from '@/stores/indexStore';

const router = useRouter();
const fundStore = useFundStore();
const commodityStore = useCommodityStore();
const indexStore = useIndexStore();

// 计算属性
const hasFunds = computed(() => fundStore.funds.length > 0);

const overviewData = computed(() => {
  if (fundStore.funds.length === 0) return null;
  
  const totalValue = fundStore.funds.reduce((sum, f) => {
    return sum + (f.estimateValue || f.netValue || 0);
  }, 0);
  
  const avgChange = fundStore.averageChange ?? 0;
  
  return {
    totalValue,
    totalChange: totalValue * (avgChange / 100),
    totalChangePercent: avgChange,
    fundCount: fundStore.funds.length,
  };
});

const topGainers = computed(() => fundStore.topGainers.slice(0, 3));
const topLosers = computed(() => fundStore.topLosers.slice(0, 3));

function formatValue(value: number | undefined | null): string {
  if (value == null) return '--';
  if (value >= 10000) {
    return (value / 10000).toFixed(2) + '万';
  }
  return value.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function formatPercent(value: number | undefined | null): string {
  if (value == null) return '--';
  const sign = value >= 0 ? '+' : '';
  return `${sign}${value.toFixed(2)}%`;
}

function navigateTo(path: string) {
  router.push(path);
}

onMounted(async () => {
  // 预加载数据以显示仪表盘
  if (fundStore.funds.length === 0) {
    await fundStore.fetchFunds();
  }
  if (commodityStore.categories.length === 0) {
    await commodityStore.fetchCategories({ showError: false });
  }
  if (indexStore.indices.length === 0) {
    await indexStore.fetchIndices({ showError: false });
  }
});
</script>

<template>
  <div class="home">
    <!-- Hero Section -->
    <div class="hero-section">
      <div class="hero-content">
        <h1 class="hero-title">FundVue</h1>
        <p class="hero-subtitle">实时基金估值监控</p>
      </div>
      <div class="hero-stats">
        <div class="stat-item">
          <span class="stat-value">{{ fundStore.funds.length }}</span>
          <span class="stat-label">自选基金</span>
        </div>
        <div class="stat-divider"></div>
        <div class="stat-item">
          <span class="stat-value">{{ commodityStore.commodities.length }}</span>
          <span class="stat-label">关注商品</span>
        </div>
        <div class="stat-divider"></div>
        <div class="stat-item">
          <span class="stat-value">{{ indexStore.indices.length }}</span>
          <span class="stat-label">全球指数</span>
        </div>
      </div>
    </div>

    <!-- Portfolio Overview -->
    <div v-if="hasFunds && overviewData" class="overview-section">
      <h2 class="section-title">持仓概览</h2>
      <div class="overview-grid">
        <div class="overview-card total-value">
          <span class="card-label">持仓总值</span>
          <span class="card-value">¥{{ formatValue(overviewData.totalValue) }}</span>
        </div>
        <div class="overview-card" :class="overviewData.totalChangePercent >= 0 ? 'rising' : 'falling'">
          <span class="card-label">今日涨跌</span>
          <div class="card-change">
            <svg v-if="overviewData.totalChangePercent > 0" viewBox="0 0 24 24" fill="none">
              <path d="M12 19V5M5 12L12 5L19 12" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
            </svg>
            <svg v-else-if="overviewData.totalChangePercent < 0" viewBox="0 0 24 24" fill="none">
              <path d="M12 5V19M19 12L12 19L5 12" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
            </svg>
            <span class="card-value">{{ formatPercent(overviewData.totalChangePercent) }}</span>
          </div>
        </div>
        <div class="overview-card">
          <span class="card-label">基金数量</span>
          <span class="card-value">{{ overviewData.fundCount }} 只</span>
        </div>
      </div>
    </div>

    <!-- Quick Actions -->
    <div class="actions-section">
      <h2 class="section-title">快速访问</h2>
      <div class="actions-grid">
        <div class="action-card" @click="navigateTo('/funds')">
          <div class="action-icon funds">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <path d="M3 3V21H21"/>
              <path d="M7 14L11 10L15 12L21 6"/>
            </svg>
          </div>
          <div class="action-content">
            <span class="action-title">基金自选</span>
            <span class="action-desc">管理您的基金自选</span>
          </div>
          <svg class="action-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M9 18L15 12L9 6"/>
          </svg>
        </div>

        <div class="action-card" @click="navigateTo('/commodities')">
          <div class="action-icon commodities">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <circle cx="12" cy="12" r="10"/>
              <path d="M12 6V12L16 14"/>
            </svg>
          </div>
          <div class="action-content">
            <span class="action-title">商品行情</span>
            <span class="action-desc">黄金、原油等大宗商品</span>
          </div>
          <svg class="action-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M9 18L15 12L9 6"/>
          </svg>
        </div>

        <div class="action-card" @click="navigateTo('/indices')">
          <div class="action-icon indices">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <path d="M3 3V21H21"/>
              <path d="M7 14L11 10L15 12L21 6"/>
              <circle cx="12" cy="12" r="2"/>
            </svg>
          </div>
          <div class="action-content">
            <span class="action-title">全球市场</span>
            <span class="action-desc">A股、港股、美股指数</span>
          </div>
          <svg class="action-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M9 18L15 12L9 6"/>
          </svg>
        </div>

        <div class="action-card" @click="navigateTo('/sectors')">
          <div class="action-icon sectors">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <rect x="3" y="3" width="7" height="7" rx="1"/>
              <rect x="14" y="3" width="7" height="7" rx="1"/>
              <rect x="3" y="14" width="7" height="7" rx="1"/>
              <rect x="14" y="14" width="7" height="7" rx="1"/>
            </svg>
          </div>
          <div class="action-content">
            <span class="action-title">行业板块</span>
            <span class="action-desc">板块资金流向分析</span>
          </div>
          <svg class="action-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M9 18L15 12L9 6"/>
          </svg>
        </div>
      </div>
    </div>

    <!-- Market Rankings -->
    <div v-if="fundStore.funds.length > 0 && (topGainers.length > 0 || topLosers.length > 0)" class="rankings-section">
      <div class="rankings-grid">
        <!-- Top Gainers -->
        <div class="ranking-card rising">
          <div class="ranking-header">
            <svg viewBox="0 0 24 24" fill="none">
              <path d="M12 19V5M5 12L12 5L19 12" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
            </svg>
            <span>涨幅排行</span>
          </div>
          <div class="ranking-list">
            <div v-for="fund in topGainers" :key="fund.code" class="ranking-item">
              <div class="ranking-info">
                <span class="ranking-code">{{ fund.code }}</span>
                <span class="ranking-name">{{ fund.name }}</span>
              </div>
              <span class="ranking-value">{{ formatPercent(fund.estimateChangePercent) }}</span>
            </div>
            <div v-if="topGainers.length === 0" class="ranking-empty">暂无数据</div>
          </div>
        </div>

        <!-- Top Losers -->
        <div class="ranking-card falling">
          <div class="ranking-header">
            <svg viewBox="0 0 24 24" fill="none">
              <path d="M12 5V19M19 12L12 19L5 12" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
            </svg>
            <span>跌幅排行</span>
          </div>
          <div class="ranking-list">
            <div v-for="fund in topLosers" :key="fund.code" class="ranking-item">
              <div class="ranking-info">
                <span class="ranking-code">{{ fund.code }}</span>
                <span class="ranking-name">{{ fund.name }}</span>
              </div>
              <span class="ranking-value">{{ formatPercent(fund.estimateChangePercent) }}</span>
            </div>
            <div v-if="topLosers.length === 0" class="ranking-empty">暂无数据</div>
          </div>
        </div>
      </div>
    </div>

    <!-- Empty State -->
    <div v-if="!hasFunds && !fundStore.loading" class="empty-state">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <path d="M3 3V21H21"/>
        <path d="M7 14L11 10L15 12L21 6"/>
      </svg>
      <span>暂无基金数据</span>
      <p>点击下方按钮添加自选基金开始监控</p>
      <button class="btn-primary" @click="navigateTo('/funds')">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M12 5V19M5 12H19"/>
        </svg>
        添加基金
      </button>
    </div>

    <!-- Loading State -->
    <div v-if="fundStore.loading && !hasFunds" class="loading-state">
      <div class="loading-grid">
        <div v-for="i in 4" :key="i" class="skeleton-card">
          <div class="skeleton skeleton-title"></div>
          <div class="skeleton skeleton-value"></div>
        </div>
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.home {
  max-width: 1200px;
  margin: 0 auto;
}

/* Hero Section */
.hero-section {
  background: var(--color-bg-secondary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: var(--spacing-xl);
  margin-bottom: var(--spacing-xl);
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.hero-content {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
}

.hero-title {
  font-size: var(--font-size-3xl);
  font-weight: var(--font-weight-bold);
  color: var(--color-text-primary);
  margin: 0;
}

.hero-subtitle {
  font-size: var(--font-size-md);
  color: var(--color-text-secondary);
  margin: 0;
}

.hero-stats {
  display: flex;
  align-items: center;
  gap: var(--spacing-lg);
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--spacing-xs);
}

.stat-value {
  font-size: var(--font-size-2xl);
  font-weight: var(--font-weight-bold);
  font-family: var(--font-mono);
  color: var(--color-text-primary);
}

.stat-label {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
}

.stat-divider {
  width: 1px;
  height: 40px;
  background: var(--color-divider);
}

/* Section Title */
.section-title {
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
  margin: 0 0 var(--spacing-lg) 0;
}

/* Overview Section */
.overview-section {
  margin-bottom: var(--spacing-xl);
}

.overview-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--spacing-md);
}

.overview-card {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: var(--spacing-lg);
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);

  &.rising {
    background: var(--color-rise-bg);
    border-color: var(--color-rise);
    
    .card-value {
      color: var(--color-rise);
    }
  }

  &.falling {
    background: var(--color-fall-bg);
    border-color: var(--color-fall);
    
    .card-value {
      color: var(--color-fall);
    }
  }
}

.card-label {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

.card-value {
  font-size: var(--font-size-xl);
  font-weight: var(--font-weight-bold);
  font-family: var(--font-mono);
  color: var(--color-text-primary);
}

.card-change {
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);

  svg {
    width: 20px;
    height: 20px;
  }
}

/* Actions Section */
.actions-section {
  margin-bottom: var(--spacing-xl);
}

.actions-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--spacing-md);
}

.action-card {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: var(--spacing-lg);
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
  cursor: pointer;
  transition: all var(--transition-fast);

  &:hover {
    background: var(--color-bg-card-hover);
    border-color: var(--color-border-light);
    transform: translateY(-2px);
  }
}

.action-icon {
  width: 48px;
  height: 48px;
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;

  svg {
    width: 24px;
    height: 24px;
  }

  &.funds {
    background: rgba(255, 107, 107, 0.15);
    color: var(--color-rise);
  }

  &.commodities {
    background: rgba(250, 173, 20, 0.15);
    color: var(--color-warning);
  }

  &.indices {
    background: rgba(96, 165, 250, 0.15);
    color: #60A5FA;
  }

  &.sectors {
    background: rgba(167, 139, 250, 0.15);
    color: #A78BFA;
  }
}

.action-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.action-title {
  font-size: var(--font-size-md);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}

.action-desc {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
}

.action-arrow {
  width: 20px;
  height: 20px;
  color: var(--color-text-tertiary);
  transition: transform var(--transition-fast);
}

.action-card:hover .action-arrow {
  transform: translateX(4px);
}

/* Rankings Section */
.rankings-section {
  margin-bottom: var(--spacing-xl);
}

.rankings-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--spacing-md);
}

.ranking-card {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: var(--spacing-lg);

  &.rising {
    .ranking-header {
      color: var(--color-rise);
    }
    .ranking-value {
      color: var(--color-rise);
    }
  }

  &.falling {
    .ranking-header {
      color: var(--color-fall);
    }
    .ranking-value {
      color: var(--color-fall);
    }
  }
}

.ranking-header {
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
  font-size: var(--font-size-md);
  font-weight: var(--font-weight-semibold);
  margin-bottom: var(--spacing-md);
  color: var(--color-text-secondary);

  svg {
    width: 18px;
    height: 18px;
  }
}

.ranking-list {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
}

.ranking-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--spacing-sm);
  border-radius: var(--radius-md);
  transition: background var(--transition-fast);

  &:hover {
    background: var(--color-bg-tertiary);
  }
}

.ranking-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
  flex: 1;
}

.ranking-code {
  font-size: var(--font-size-xs);
  font-family: var(--font-mono);
  color: var(--color-text-tertiary);
}

.ranking-name {
  font-size: var(--font-size-sm);
  color: var(--color-text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.ranking-value {
  font-size: var(--font-size-md);
  font-weight: var(--font-weight-semibold);
  font-family: var(--font-mono);
  flex-shrink: 0;
}

.ranking-empty {
  text-align: center;
  padding: var(--spacing-lg);
  color: var(--color-text-tertiary);
  font-size: var(--font-size-sm);
}

/* Empty State */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--spacing-2xl);
  gap: var(--spacing-md);
  color: var(--color-text-secondary);

  svg {
    width: 64px;
    height: 64px;
    opacity: 0.5;
  }

  span {
    font-size: var(--font-size-lg);
  }

  p {
    font-size: var(--font-size-sm);
    opacity: 0.7;
    margin: 0;
  }
}

/* Loading State */
.loading-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--spacing-md);
}

.skeleton-card {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: var(--spacing-lg);
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
}

.skeleton {
  height: 16px;
  border-radius: var(--radius-sm);

  &.skeleton-title {
    width: 60%;
  }

  &.skeleton-value {
    width: 80%;
    height: 24px;
  }
}

/* Button */
.btn {
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
  padding: var(--spacing-sm) var(--spacing-md);
  border-radius: var(--radius-md);
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  cursor: pointer;
  transition: all var(--transition-fast);

  svg {
    width: 16px;
    height: 16px;
  }
}

.btn-primary {
  @extend .btn;
  background: var(--color-primary);
  border: 1px solid var(--color-primary);
  color: white;

  &:hover {
    opacity: 0.9;
  }
}

/* Responsive */
@media (max-width: 768px) {
  .hero-section {
    flex-direction: column;
    gap: var(--spacing-lg);
    text-align: center;
  }

  .hero-stats {
    justify-content: center;
  }

  .overview-grid {
    grid-template-columns: 1fr;
  }

  .actions-grid {
    grid-template-columns: 1fr;
  }

  .rankings-grid {
    grid-template-columns: 1fr;
  }
}
</style>
