<template>
  <div class="sectors-view">
    <!-- Header -->
    <div class="view-header">
      <h2 class="section-title">行业板块</h2>
      <div class="header-actions">
        <div class="tab-switcher">
          <button
            class="tab-btn"
            :class="{ active: sectorStore.currentType === 'industry' }"
            @click="switchType('industry')"
          >
            行业板块
          </button>
          <button
            class="tab-btn"
            :class="{ active: sectorStore.currentType === 'concept' }"
            @click="switchType('concept')"
          >
            概念板块
          </button>
        </div>
        <button 
          class="view-toggle"
          :class="{ active: showFlowView }"
          @click="showFlowView = !showFlowView"
          title="资金流向视图"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M12 2v20M17 5H9.5a3.5 3.5 0 000 7h5a3.5 3.5 0 010 7H6"/>
          </svg>
          资金流向
        </button>
      </div>
    </div>

    <!-- 资金流向概览 -->
    <div v-if="showFlowView && sectorStore.currentSectors.length > 0" class="flow-section">
      <FlowSummary :sectors="sectorStore.currentSectors" />
      
      <div class="flow-content">
        <div class="flow-rank">
          <CapitalFlowRank 
            :sectors="sectorStore.currentSectors" 
            title="主力净流入排行"
            :maxItems="10"
            @select="handleSelectSector"
          />
        </div>
      </div>
    </div>

    <!-- Error State -->
    <div v-else-if="sectorStore.error && sectorStore.currentSectors.length === 0" class="error-state">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <circle cx="12" cy="12" r="10"/>
        <path d="M12 8V12M12 16H12.01"/>
      </svg>
      <span>{{ sectorStore.error }}</span>
      <button @click="sectorStore.retry">重试</button>
    </div>

    <!-- Loading State -->
    <div v-else-if="sectorStore.loading && sectorStore.currentSectors.length === 0" class="loading-state">
      <div class="loading-grid">
        <SectorCard
          v-for="i in 12"
          :key="i"
          :sector="emptySector"
          :loading="true"
        />
      </div>
    </div>

    <!-- Empty State -->
    <div v-else-if="!showFlowView && sectorStore.currentSectors.length === 0" class="empty-state">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <circle cx="12" cy="12" r="10"/>
        <path d="M12 6V12L16 14"/>
      </svg>
      <span>暂无板块数据</span>
      <p>行业板块数据将显示在这里</p>
    </div>

    <!-- Sectors Grid (Default View) -->
    <div v-else-if="!showFlowView" class="sectors-grid">
      <SectorCard
        v-for="sector in sectorStore.sortedSectors"
        :key="sector.code"
        :sector="sector"
        @click="handleSelectSector(sector)"
      />
    </div>

    <!-- Quick Stats -->
    <div v-if="!showFlowView && sectorStore.currentSectors.length > 0" class="quick-stats">
      <div class="stats-card">
        <span class="stats-label">上涨</span>
        <span class="stats-value rising">{{ sectorStore.risingSectors.length }}</span>
      </div>
      <div class="stats-card">
        <span class="stats-label">下跌</span>
        <span class="stats-value falling">{{ sectorStore.fallingSectors.length }}</span>
      </div>
      <div class="stats-card">
        <span class="stats-label">板块总数</span>
        <span class="stats-value">{{ sectorStore.currentSectors.length }}</span>
      </div>
      <div class="stats-card" v-if="hasFlowData">
        <span class="stats-label">有资金数据</span>
        <span class="stats-value primary">{{ flowDataCount }}</span>
      </div>
    </div>

    <!-- Sector Detail Drawer -->
    <div v-if="showDetail" class="detail-drawer-overlay" @click="closeDetail">
      <div class="detail-drawer" @click.stop>
        <div class="drawer-header">
          <h3>{{ selectedSectorData?.name }}</h3>
          <button class="close-btn" @click="closeDetail">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M18 6L6 18M6 6l12 12"/>
            </svg>
          </button>
        </div>
        <div class="drawer-content">
          <div class="detail-stats" v-if="selectedSectorData">
            <div class="detail-stat">
              <span class="label">涨跌幅</span>
              <span class="value" :class="getChangeClass(selectedSectorData.changePercent)">
                {{ formatPercent(selectedSectorData.changePercent) }}
              </span>
            </div>
            <div class="detail-stat" v-if="selectedSectorData.mainInflow !== undefined">
              <span class="label">主力净流入</span>
              <span class="value" :class="selectedSectorData.mainInflow > 0 ? 'rise' : selectedSectorData.mainInflow < 0 ? 'fall' : ''">
                {{ formatFlow(selectedSectorData.mainInflow) }}
              </span>
            </div>
            <div class="detail-stat" v-if="selectedSectorData.mainInflowPct !== undefined">
              <span class="label">主力净流入占比</span>
              <span class="value">{{ formatPercent(selectedSectorData.mainInflowPct) }}</span>
            </div>
            <div class="detail-stat" v-if="selectedSectorData.upCount !== undefined">
              <span class="label">上涨/下跌</span>
              <span class="value">
                <span class="rise">{{ selectedSectorData.upCount }}</span> / 
                <span class="fall">{{ selectedSectorData.downCount }}</span>
              </span>
            </div>
          </div>
          
          <div class="detail-loading" v-if="sectorStore.detailLoading">
            <span>加载中...</span>
          </div>
          
          <div class="detail-stocks" v-else-if="sectorStore.sectorDetail.length > 0">
            <h4>成份股</h4>
            <div class="stocks-list">
              <div 
                v-for="stock in sectorStore.sectorDetail" 
                :key="stock.code"
                class="stock-item"
              >
                <span class="stock-rank">{{ stock.rank }}</span>
                <span class="stock-name">{{ stock.name }}</span>
                <span class="stock-code">{{ stock.code }}</span>
                <span class="stock-change" :class="getChangeClass(stock.changePercent)">
                  {{ formatPercent(stock.changePercent) }}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import { useSectorStore, type SectorType } from '@/stores/sectorStore';
import SectorCard from '@/components/SectorCard.vue';
import FlowSummary from '@/components/FlowSummary.vue';
import CapitalFlowRank from '@/components/CapitalFlowRank.vue';
import type { Sector } from '@/types';

const sectorStore = useSectorStore();

// 视图切换
const showFlowView = ref(false);
const showDetail = ref(false);
const selectedSectorData = ref<Sector | null>(null);

// 检查是否有资金流向数据
const hasFlowData = computed(() => {
  return sectorStore.currentSectors.some(s => s.mainInflow !== undefined);
});

const flowDataCount = computed(() => {
  return sectorStore.currentSectors.filter(s => s.mainInflow !== undefined).length;
});

// Empty sector for loading skeleton
const emptySector: Sector = {
  rank: 0,
  name: '加载中...',
  code: '---',
  price: 0,
  change: 0,
  changePercent: 0,
  upCount: 0,
  downCount: 0,
  leadStock: '',
  leadChange: 0,
};

async function switchType(type: SectorType) {
  showFlowView.value = false;
  await sectorStore.switchSectorType(type);
}

function handleSelectSector(sector: Sector) {
  selectedSectorData.value = sector;
  showDetail.value = true;
  sectorStore.fetchSectorDetail(sector.name, sectorStore.currentType);
}

function closeDetail() {
  showDetail.value = false;
  selectedSectorData.value = null;
  sectorStore.clearDetail();
}

function getChangeClass(value: number | undefined): string {
  if (value === undefined) return 'neutral';
  if (value > 0) return 'rising';
  if (value < 0) return 'falling';
  return 'neutral';
}

function formatPercent(value: number | undefined): string {
  if (value === undefined || isNaN(value)) return '--';
  const sign = value >= 0 ? '+' : '';
  return `${sign}${value.toFixed(2)}%`;
}

function formatFlow(value: number | undefined): string {
  if (value === undefined || isNaN(value)) return '--';
  const sign = value >= 0 ? '+' : '';
  return `${sign}${value.toFixed(2)}亿`;
}

onMounted(async () => {
  await sectorStore.fetchIndustrySectors({ showError: true });
});
</script>

<style lang="scss" scoped>
.sectors-view {
  padding: var(--spacing-lg);
}

.view-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--spacing-lg);
  flex-wrap: wrap;
  gap: var(--spacing-md);
}

.section-title {
  font-size: var(--font-size-xl);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}

.header-actions {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
}

.tab-switcher {
  display: flex;
  background: var(--color-bg-secondary);
  border-radius: var(--radius-lg);
  padding: 4px;
}

.tab-btn {
  padding: 8px 16px;
  border: none;
  background: transparent;
  border-radius: var(--radius-md);
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: all var(--transition-fast);

  &:hover {
    color: var(--color-text-primary);
  }

  &.active {
    background: var(--color-bg-card);
    color: var(--color-text-primary);
    box-shadow: var(--shadow-sm);
  }
}

.view-toggle {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  border: 1px solid var(--color-border);
  background: var(--color-bg-card);
  border-radius: var(--radius-md);
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: all var(--transition-fast);

  svg {
    width: 16px;
    height: 16px;
  }

  &:hover {
    border-color: var(--color-primary);
    color: var(--color-primary);
  }

  &.active {
    background: var(--color-primary);
    border-color: var(--color-primary);
    color: white;
  }
}

// 资金流向视图样式
.flow-section {
  margin-bottom: var(--spacing-lg);
}

.flow-content {
  display: grid;
  grid-template-columns: 1fr;
  gap: var(--spacing-lg);
  margin-top: var(--spacing-lg);
}

@media (min-width: 768px) {
  .flow-content {
    grid-template-columns: repeat(2, 1fr);
  }
}

.last-updated {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
}

.error-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--spacing-md);
  padding: var(--spacing-xl);
  color: var(--color-fall);
  text-align: center;

  svg {
    width: 48px;
    height: 48px;
  }

  button {
    padding: 8px 24px;
    border: none;
    border-radius: var(--radius-md);
    background: var(--color-fall);
    color: white;
    cursor: pointer;
    transition: opacity var(--transition-fast);

    &:hover {
      opacity: 0.9;
    }
  }
}

.loading-state, .empty-state {
  padding: var(--spacing-xl);
}

.loading-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: var(--spacing-md);
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--spacing-md);
  color: var(--color-text-tertiary);
  text-align: center;

  svg {
    width: 48px;
    height: 48px;
    opacity: 0.5;
  }

  p {
    font-size: var(--font-size-sm);
  }
}

.sectors-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: var(--spacing-md);
  margin-bottom: var(--spacing-lg);
}

.quick-stats {
  display: flex;
  gap: var(--spacing-md);
  flex-wrap: wrap;
}

.stats-card {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-md) var(--spacing-lg);
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
}

.stats-label {
  font-size: var(--font-size-sm);
  color: var(--color-text-tertiary);
}

.stats-value {
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-bold);
  color: var(--color-text-primary);

  &.rising {
    color: var(--color-rise);
  }

  &.falling {
    color: var(--color-fall);
  }

  &.primary {
    color: var(--color-primary);
  }
}

// 板块详情抽屉
.detail-drawer-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  z-index: 1000;
  display: flex;
  justify-content: flex-end;
}

.detail-drawer {
  width: 100%;
  max-width: 480px;
  height: 100%;
  background: var(--color-bg-card);
  box-shadow: var(--shadow-xl);
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.drawer-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--spacing-lg);
  border-bottom: 1px solid var(--color-border);

  h3 {
    font-size: var(--font-size-lg);
    font-weight: var(--font-weight-semibold);
    margin: 0;
    color: var(--color-text-primary);
  }
}

.close-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border: none;
  background: var(--color-bg-secondary);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all var(--transition-fast);

  svg {
    width: 20px;
    height: 20px;
    color: var(--color-text-secondary);
  }

  &:hover {
    background: var(--color-bg-tertiary);

    svg {
      color: var(--color-text-primary);
    }
  }
}

.drawer-content {
  flex: 1;
  overflow-y: auto;
  padding: var(--spacing-lg);
}

.detail-stats {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--spacing-md);
  margin-bottom: var(--spacing-lg);
}

.detail-stat {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: var(--spacing-md);
  background: var(--color-bg-secondary);
  border-radius: var(--radius-md);

  .label {
    font-size: var(--font-size-xs);
    color: var(--color-text-tertiary);
  }

  .value {
    font-size: var(--font-size-base);
    font-weight: var(--font-weight-semibold);
    color: var(--color-text-primary);

    &.rising {
      color: var(--color-rise);
    }

    &.falling {
      color: var(--color-fall);
    }

    &.rise {
      color: var(--color-rise);
    }

    &.fall {
      color: var(--color-fall);
    }
  }
}

.detail-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--spacing-xl);
  color: var(--color-text-tertiary);
}

.detail-stocks {
  h4 {
    font-size: var(--font-size-base);
    font-weight: var(--font-weight-semibold);
    margin: 0 0 var(--spacing-md) 0;
    color: var(--color-text-primary);
  }
}

.stocks-list {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
}

.stock-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-sm);
  background: var(--color-bg-secondary);
  border-radius: var(--radius-md);

  .stock-rank {
    display: flex;
    align-items: center;
    justify-content: center;
    min-width: 24px;
    height: 24px;
    font-size: var(--font-size-xs);
    font-weight: var(--font-weight-semibold);
    color: var(--color-text-tertiary);
    background: var(--color-bg-tertiary);
    border-radius: var(--radius-sm);
  }

  .stock-name {
    flex: 1;
    font-size: var(--font-size-sm);
    font-weight: var(--font-weight-medium);
    color: var(--color-text-primary);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .stock-code {
    font-size: var(--font-size-xs);
    color: var(--color-text-tertiary);
    font-family: var(--font-mono);
  }

  .stock-change {
    font-size: var(--font-size-sm);
    font-weight: var(--font-weight-semibold);
    min-width: 60px;
    text-align: right;

    &.rising {
      color: var(--color-rise);
    }

    &.falling {
      color: var(--color-fall);
    }

    &.neutral {
      color: var(--color-text-tertiary);
    }
  }
}
</style>
