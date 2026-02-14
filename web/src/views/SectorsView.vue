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
      </div>
    </div>

    <!-- Error State -->
    <div v-if="sectorStore.error" class="error-state">
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
    <div v-else-if="sectorStore.currentSectors.length === 0" class="empty-state">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <circle cx="12" cy="12" r="10"/>
        <path d="M12 6V12L16 14"/>
      </svg>
      <span>暂无板块数据</span>
      <p>行业板块数据将显示在这里</p>
    </div>

    <!-- Sectors Grid -->
    <div v-else class="sectors-grid">
      <SectorCard
        v-for="sector in sectorStore.sortedSectors"
        :key="sector.code"
        :sector="sector"
      />
    </div>

    <!-- Quick Stats -->
    <div v-if="sectorStore.currentSectors.length > 0" class="quick-stats">
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
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue';
import { useSectorStore, type SectorType } from '@/stores/sectorStore';
import SectorCard from '@/components/SectorCard.vue';
import type { Sector } from '@/types';

const sectorStore = useSectorStore();

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
  await sectorStore.switchSectorType(type);
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
}
</style>
