<template>
  <div class="app-layout" :class="{ 'sidebar-collapsed': sidebarCollapsed, 'sidebar-mobile-open': sidebarMobileOpen }">
    <!-- Mobile Overlay -->
    <div class="sidebar-overlay" :class="{ open: sidebarMobileOpen }" @click="closeMobileSidebar"></div>

    <!-- Sidebar -->
    <aside class="sidebar">
      <div class="sidebar-header">
        <div class="logo">
          <svg class="logo-icon" viewBox="0 0 32 32" fill="none">
            <path d="M16 2L4 8V24L16 30L28 24V8L16 2Z" stroke="currentColor" stroke-width="2" fill="none"/>
            <path d="M16 2V30M4 8L28 24M28 8L4 24" stroke="currentColor" stroke-width="1.5" opacity="0.5"/>
          </svg>
          <span v-if="!sidebarCollapsed" class="logo-text">FundVue</span>
        </div>
      </div>

      <nav class="sidebar-nav">
        <router-link to="/" class="nav-item" :class="{ active: currentRoute === 'home' }">
          <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z"/>
            <polyline points="9,22 9,12 15,12 15,22"/>
          </svg>
          <span v-if="!sidebarCollapsed" class="nav-text">首页</span>
        </router-link>

        <router-link to="/funds" class="nav-item" :class="{ active: currentRoute === 'funds' }">
          <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <path d="M3 3V21H21"/>
            <path d="M7 14L11 10L15 12L21 6"/>
          </svg>
          <span v-if="!sidebarCollapsed" class="nav-text">基金自选</span>
        </router-link>

        <router-link to="/commodities" class="nav-item" :class="{ active: currentRoute === 'commodities' }">
          <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <circle cx="12" cy="12" r="10"/>
            <path d="M12 6V12L16 14"/>
          </svg>
          <span v-if="!sidebarCollapsed" class="nav-text">商品行情</span>
        </router-link>

        <router-link to="/indices" class="nav-item" :class="{ active: currentRoute === 'indices' }">
          <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <path d="M3 3V21H21"/>
            <path d="M7 14L11 10L15 12L21 6" stroke-width="1.5"/>
            <circle cx="12" cy="12" r="2" stroke-width="1.5"/>
          </svg>
          <span v-if="!sidebarCollapsed" class="nav-text">全球市场</span>
        </router-link>

        <router-link to="/sectors" class="nav-item" :class="{ active: currentRoute === 'sectors' }">
          <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <rect x="3" y="3" width="7" height="7" rx="1"/>
            <rect x="14" y="3" width="7" height="7" rx="1"/>
            <rect x="3" y="14" width="7" height="7" rx="1"/>
            <rect x="14" y="14" width="7" height="7" rx="1"/>
          </svg>
          <span v-if="!sidebarCollapsed" class="nav-text">行业板块</span>
        </router-link>


        <router-link to="/calendar" class="nav-item" :class="{ active: currentRoute === 'calendar' }">
          <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <rect x="3" y="4" width="18" height="18" rx="2"/>
            <path d="M16 2v4"/>
            <path d="M8 2v4"/>
            <path d="M3 10h18"/>
          </svg>
          <span v-if="!sidebarCollapsed" class="nav-text">财经日历</span>
        </router-link>

        <router-link to="/settings" class="nav-item" :class="{ active: currentRoute === 'settings' }">
          <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <circle cx="12" cy="12" r="3"/>
            <path d="M19.4 15A1.65 1.65 0 0 0 21 12A1.65 1.65 0 0 0 19.4 9"/>
            <path d="M4.6 9A1.65 1.65 0 0 0 3 12A1.65 1.65 0 0 0 4.6 15"/>
            <path d="M15 19.4A1.65 1.65 0 0 0 12 21A1.65 1.65 0 0 0 9 19.4"/>
            <path d="M9 4.6A1.65 1.65 0 0 0 12 3A1.65 1.65 0 0 0 15 4.6"/>
          </svg>
          <span v-if="!sidebarCollapsed" class="nav-text">设置</span>
        </router-link>
      </nav>

      <div class="sidebar-footer">
        <button class="collapse-btn" @click="toggleSidebar" :aria-label="sidebarCollapsed ? '展开侧边栏' : '收起侧边栏'">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true">
            <path d="M15 18L9 12L15 6"/>
          </svg>
        </button>
      </div>
    </aside>

    <!-- Main Content -->
    <main class="main-content">
      <!-- Header -->
      <header class="header">
        <div class="header-left">
          <button class="hamburger-btn" @click="toggleMobileSidebar" aria-label="Toggle menu">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M3 12h18M3 6h18M3 18h18"/>
            </svg>
          </button>
          <h1 class="page-title">{{ pageTitle }}</h1>
        </div>
        <div class="header-right">
          <div class="status-indicator" :class="healthStatus">
            <span class="status-dot"></span>
            <span class="status-text">{{ connectionStatus }}</span>
          </div>
          <button class="refresh-btn" @click="refresh" :disabled="refreshing" :aria-label="refreshing ? '刷新中' : '刷新数据'">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" :class="{ spinning: refreshing }" aria-hidden="true">
              <path d="M23 4V6H19"/>
              <path d="M1 20V18H5"/>
              <path d="M3.5 14.5C3.5 10.5 6.5 7 10.5 7H14.5"/>
              <path d="M20.5 9.5C20.5 13.5 17.5 17 13.5 17H9.5"/>
            </svg>
          </button>
          <span class="last-updated" v-if="lastUpdated">更新于 {{ lastUpdated }}</span>
        </div>
      </header>

      <!-- Page Content -->
      <div class="content">
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </div>

      <!-- Footer -->
      <footer class="footer">
        <span class="footer-text">FundVue &copy; 2024</span>
        <span class="footer-version">v1.0.0</span>
      </footer>
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue';
import { useRoute } from 'vue-router';
import { useFundStore } from '@/stores/fundStore';
import { useCommodityStore } from '@/stores/commodityStore';
import { useIndexStore } from '@/stores/indexStore';
import { useSectorStore } from '@/stores/sectorStore';
import { useWSStore } from '@/stores/wsStore';
import { healthApi } from '@/api';
import type { Fund, Commodity, MarketIndex } from '@/types';

const route = useRoute();
const fundStore = useFundStore();
const commodityStore = useCommodityStore();
const indexStore = useIndexStore();
const sectorStore = useSectorStore();
const wsStore = useWSStore();

const sidebarCollapsed = ref(false);
const sidebarMobileOpen = ref(false);
const healthStatus = ref<'healthy' | 'degraded' | 'unhealthy'>('healthy');
// eslint-disable-next-line no-useless-assignment
const connectionStatus = computed(() => {
  if (wsStore.isConnected) {
    return '实时';
  }
  if (healthStatus.value === 'healthy') {
    return '已连接';
  }
  if (healthStatus.value === 'degraded') {
    return '重连中...';
  }
  return '连接失败';
});
const refreshing = ref(false);
let healthTimer: number | null = null;

 
const currentRoute = computed(() => route.name as string || 'home');
// eslint-disable-next-line no-useless-assignment
const pageTitle = computed(() => {
  const titles: Record<string, string> = {
    home: '首页',
    funds: '基金自选',
    commodities: '商品行情',
    indices: '全球市场',
    calendar: '财经日历',
    settings: '设置',
  };
  return titles[currentRoute.value] || 'FundVue';
});

// eslint-disable-next-line no-useless-assignment
const lastUpdated = computed(() => fundStore.lastUpdated || commodityStore.lastUpdated || indexStore.lastUpdated);

function toggleSidebar() {
  sidebarCollapsed.value = !sidebarCollapsed.value;
}

function toggleMobileSidebar() {
  sidebarMobileOpen.value = !sidebarMobileOpen.value;
}

function closeMobileSidebar() {
  sidebarMobileOpen.value = false;
}

async function checkHealth() {
  try {
    const health = await healthApi.getSimpleHealth();
    healthStatus.value = health.status === 'healthy' ? 'healthy' : 'degraded';
  } catch {
    healthStatus.value = 'unhealthy';
  }
}

async function refresh() {
  if (refreshing.value) return;

  refreshing.value = true;
  try {
    await Promise.all([
      fundStore.fetchFunds(),
      commodityStore.fetchCategories(),
      indexStore.fetchIndices(),
      sectorStore.refresh(),
      checkHealth(),
    ]);
  } finally {
    refreshing.value = false;
  }
}

function setupWebSocketHandlers() {
  wsStore.on('fund_update', (data) => {
    const payload = data as { funds?: any[] };
    const funds = payload?.funds;
    if (funds && funds.length > 0) {
      funds.forEach((updatedFund) => {
        // WebSocket 推送的字段名需要映射到前端期望的字段名
        // fundCode -> code, unitNetValue -> netValue 等
        const fundCode = updatedFund.fundCode || updatedFund.code;
        // 防御性检查：确保 code 字段存在，否则静默失败
        if (!fundCode) {
          console.warn('WebSocket 推送的基金数据缺少 code 字段', updatedFund);
          return;
        }
        const normalizedFund: Partial<Fund> & { code: string } = {
          code: fundCode,
          name: updatedFund.name,
          netValue: updatedFund.unitNetValue ?? updatedFund.netValue,
          netValueDate: updatedFund.netValueDate,
          estimateValue: updatedFund.estimatedNetValue ?? updatedFund.estimateValue,
          estimateChangePercent: updatedFund.estimatedGrowthRate ?? updatedFund.estimateChangePercent,
          estimateTime: updatedFund.estimateTime,
          type: updatedFund.type,
          hasRealTimeEstimate: updatedFund.hasRealTimeEstimate ?? true,
        };
        fundStore.updateFund(normalizedFund);
      });
      fundStore.lastUpdated = new Date().toLocaleTimeString();
    }
  });

  wsStore.on('commodity_update', (data) => {
    const payload = data as { commodities?: Commodity[] };
    const commodities = payload?.commodities;
    if (commodities && commodities.length > 0) {
      // 合并数据到 commodityStore（保留本地状态）
      commodities.forEach((updatedCommodity) => {
        const index = commodityStore.commodities.findIndex(
          (c) => c.symbol === updatedCommodity.symbol
        );
        if (index !== -1) {
          // 保留原始字段，只更新价格相关字段
          const original = commodityStore.commodities[index];
          commodityStore.commodities[index] = {
            ...original,
            ...updatedCommodity,
          };
        }
      });
      commodityStore.lastUpdated = new Date().toLocaleTimeString();
    }
  });

  wsStore.on('index_update', (data) => {
    const payload = data as { indices?: MarketIndex[] };
    const indices = payload?.indices;
    if (indices && indices.length > 0) {
      // 合并数据到 indexStore
      indices.forEach((updatedIndex) => {
        const index = indexStore.indices.findIndex(
          (i) => i.symbol === updatedIndex.symbol
        );
        if (index !== -1) {
          indexStore.indices[index] = {
            ...indexStore.indices[index],
            ...updatedIndex,
          };
        }
      });
      indexStore.lastUpdated = new Date().toLocaleTimeString();
    }
  });
}

function startWebSocket() {
  wsStore.connect();
  wsStore.subscribe(['funds', 'commodities', 'indices']);
  setupWebSocketHandlers();
}

function stopWebSocket() {
  wsStore.disconnect();
}

watch(() => wsStore.isConnected, (connected) => {
  if (connected) {
    healthStatus.value = 'healthy';
  } else {
    healthStatus.value = 'degraded';
  }
});

watch(() => route.path, () => {
  sidebarMobileOpen.value = false;
});

function handleResize() {
  if (window.innerWidth >= 768) {
    sidebarMobileOpen.value = false;
  }
}

onMounted(async () => {
  await refresh();
  startWebSocket();
  healthTimer = window.setInterval(checkHealth, 30000);
  window.addEventListener('resize', handleResize);
});

onUnmounted(() => {
  stopWebSocket();
  if (healthTimer) {
    clearInterval(healthTimer);
  }
  window.removeEventListener('resize', handleResize);
});
</script>

<style lang="scss" scoped>
.app-layout {
  display: flex;
  min-height: 100vh;
  background: var(--color-bg-primary);
}

/* Sidebar - 使用 width 动画 */
.sidebar {
  width: var(--sidebar-width);
  background: var(--color-bg-secondary);
  border-right: 1px solid var(--color-divider);
  display: flex;
  flex-direction: column;
  position: fixed;
  left: 0;
  top: 0;
  bottom: 0;
  z-index: 100;
  /* 使用 width 过渡，确保图标区域始终可见 */
  transition: width var(--transition-normal);
  will-change: width;
  overflow: hidden;
}

/* 收起状态：缩小宽度到 72px，只显示图标区域 */
.sidebar-collapsed .sidebar {
  width: 72px;
}

.sidebar-header {
  padding: var(--spacing-lg);
  border-bottom: 1px solid var(--color-divider);
}

.logo {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  color: var(--color-text-primary);
}

.logo-icon {
  width: 32px;
  height: 32px;
  flex-shrink: 0;
}

.logo-text {
  font-size: var(--font-size-xl);
  font-weight: var(--font-weight-bold);
  letter-spacing: -0.5px;
}

.sidebar-nav {
  flex: 1;
  padding: var(--spacing-md);
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
}

.nav-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
  padding: var(--spacing-sm) var(--spacing-md);
  border-radius: var(--radius-md);
  color: var(--color-text-secondary);
  transition: all var(--transition-fast);
  position: relative;

  &:hover {
    color: var(--color-text-primary);
    background: var(--color-bg-card);
  }

  &.active {
    color: var(--color-text-primary);
    background: var(--color-bg-tertiary);

    &::before {
      content: '';
      position: absolute;
      left: 0;
      top: 50%;
      transform: translateY(-50%);
      width: 3px;
      height: 60%;
      background: var(--color-rise);
      border-radius: 0 2px 2px 0;
    }
  }
}

.nav-icon {
  width: 20px;
  height: 20px;
  flex-shrink: 0;
}

.nav-text {
  font-size: var(--font-size-md);
  font-weight: var(--font-weight-medium);
}

.sidebar-footer {
  padding: var(--spacing-md);
  border-top: 1px solid var(--color-divider);
}

.collapse-btn {
  width: 100%;
  padding: var(--spacing-sm);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-text-tertiary);
  border-radius: var(--radius-md);
  transition: all var(--transition-fast);

  &:hover {
    color: var(--color-text-primary);
    background: var(--color-bg-card);
  }

  svg {
    width: 20px;
    height: 20px;
    transition: transform var(--transition-normal);
  }
}

.sidebar-collapsed .collapse-btn svg {
  transform: rotate(180deg);
}

/* Main Content - 固定 margin-left，无过渡动画 */
.main-content {
  flex: 1;
  margin-left: var(--sidebar-width);
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  /* 移除 margin-left 过渡，避免重排 */
}

.sidebar-collapsed .main-content {
  margin-left: 72px;
}

/* Header */
.header {
  height: var(--header-height);
  padding: 0 var(--spacing-xl);
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: var(--color-bg-primary);
  border-bottom: 1px solid var(--color-divider);
  position: sticky;
  top: 0;
  z-index: 50;
}

.header-left {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
}

.page-title {
  font-size: var(--font-size-xl);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}

.header-right {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
  padding: var(--spacing-xs) var(--spacing-sm);
  border-radius: var(--radius-full);
  }

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--color-fall);
}

.status-indicator.healthy .status-dot {
  background: var(--color-fall);
  box-shadow: 0 0 8px var(--color-fall);
}

.status-indicator.degraded .status-dot {
  background: #FBBF24;
}

.status-indicator.unhealthy .status-dot {
  background: var(--color-rise);
  animation: pulse 1s infinite;
}

.status-text {
  font-size: var(--font-size-xs);
  color: var(--color-text-secondary);
}

.refresh-btn {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-md);
  color: var(--color-text-secondary);
  transition: all var(--transition-fast);

  &:hover:not(:disabled) {
    color: var(--color-text-primary);
    background: var(--color-bg-card);
  }

  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  svg {
    width: 20px;
    height: 20px;
  }

  svg.spinning {
    animation: spin 1s linear infinite;
  }
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.last-updated {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
}

/* Content */
.content {
  flex: 1;
  padding: var(--spacing-xl);
  overflow-y: auto;
}

/* Footer */
.footer {
  padding: var(--spacing-md) var(--spacing-xl);
  border-top: 1px solid var(--color-divider);
  display: flex;
  align-items: center;
  justify-content: space-between;
  color: var(--color-text-tertiary);
}

.footer-text {
  font-size: var(--font-size-sm);
}

.footer-version {
  font-size: var(--font-size-xs);
}

/* Transitions */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

/* Responsive Styles */
@media (max-width: 768px) {
  /* Hamburger Button */
  .hamburger-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 56px;
    height: 40px;
    padding: 0;
    background: var(--color-bg-card);
    display: flex;
    align-items: center;
    justify-content: center;
    width: 56px;
    height: 40px;
    padding: 0;
    background: var(--color-bg-card);
    display: flex;
    align-items: center;
    justify-content: center;
    width: 56px;
    width: 40px;
    height: 40px;
    padding: 0;
    background: var(--color-bg-card);
    background: transparent;
    border: none;
    border-radius: var(--radius-md);
    color: var(--color-text-secondary);
    cursor: pointer;
    transition: all var(--transition-fast);

    &:hover {
      color: var(--color-text-primary);
      background: var(--color-bg-card);
    }

    svg {
      width: 24px;
      height: 24px;
    }
  }

  /* Sidebar Overlay */
  .sidebar-overlay {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.5);
    opacity: 0;
    visibility: hidden;
    transition: all var(--transition-normal);
    z-index: 99;

    &.open {
      opacity: 1;
      visibility: visible;
    }
  }

  /* Mobile Sidebar - 使用 transform 动画 */
  .sidebar {
    /* 重置桌面端的 transform */
    transform: translateX(-100%);
    transition: transform var(--transition-normal);
    will-change: transform;
  }

  /* 移动端展开状态 */
  .sidebar-mobile-open .sidebar {
    transform: translateX(0);
  }

  /* 移动端收起按钮状态 - 重置桌面端的旋转 */
  .sidebar-mobile-open.sidebar-collapsed .sidebar {
    transform: translateX(0);
  }

  /* Main Content - No margin on mobile */
  .main-content {
    margin-left: 0;
  }

  .sidebar-collapsed .main-content {
    margin-left: 0;
  }

  /* Header */
  .header {
    padding: 0 var(--spacing-md);
  }

  .header-left {
    gap: var(--spacing-sm);
  }

  .page-title {
    font-size: var(--font-size-lg);
  }

  /* Header Right - Hide less important elements */
  .header-right {
    gap: var(--spacing-sm);
  }

  .ws-status,
  .status-indicator,
  .last-updated {
    display: none;
  }

  /* Content */
  .content {
    padding: var(--spacing-md);
  }

  /* Footer */
  .footer {
    padding: var(--spacing-sm) var(--spacing-md);
  }
}
</style>
