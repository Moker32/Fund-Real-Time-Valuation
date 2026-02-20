<template>
  <div class="app-layout" :class="{ 'sidebar-collapsed': sidebarCollapsed }">
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

        <router-link to="/news" class="nav-item" :class="{ active: currentRoute === 'news' }">
          <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <path d="M4 22h16a2 2 0 0 0 2-2V4a2 2 0 0 0-2-2H8a2 2 0 0 0-2 2v16a2 2 0 0 1-2 2zm0 0a2 2 0 0 1-2-2v-9c0-1.1.9-2 2-2h2"/>
            <path d="M18 14h-8"/>
            <path d="M15 18h-5"/>
            <path d="M10 6h8v4h-8z"/>
          </svg>
          <span v-if="!sidebarCollapsed" class="nav-text">7×24快讯</span>
        </router-link>

        <router-link to="/bonds" class="nav-item" :class="{ active: currentRoute === 'bonds' }">
          <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <rect x="3" y="4" width="18" height="16" rx="2"/>
            <path d="M7 8h10"/>
            <path d="M7 12h6"/>
            <path d="M7 16h4"/>
          </svg>
          <span v-if="!sidebarCollapsed" class="nav-text">债券行情</span>
        </router-link>

        <router-link to="/stocks" class="nav-item" :class="{ active: currentRoute === 'stocks' }">
          <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <path d="M3 3v18h18"/>
            <path d="M7 14l4-4 4 4 5-5"/>
          </svg>
          <span v-if="!sidebarCollapsed" class="nav-text">股票行情</span>
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
          <h1 class="page-title">{{ pageTitle }}</h1>
        </div>
        <div class="header-right">
          <div class="status-indicator" :class="healthStatus">
            <span class="status-dot"></span>
            <span class="status-text">{{ statusText }}</span>
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
import { healthApi } from '@/api';

const route = useRoute();
const fundStore = useFundStore();
const commodityStore = useCommodityStore();
const indexStore = useIndexStore();
const sectorStore = useSectorStore();

const sidebarCollapsed = ref(false);
const healthStatus = ref<'healthy' | 'degraded' | 'unhealthy'>('healthy');
const statusText = ref('已连接');
const refreshing = ref(false);
let fundTimer: number | null = null;
let commodityTimer: number | null = null;
let indexTimer: number | null = null;
let healthTimer: number | null = null;

const currentRoute = computed(() => route.name as string || 'home');
const pageTitle = computed(() => {
  const titles: Record<string, string> = {
    home: '首页',
    funds: '基金自选',
    commodities: '商品行情',
    indices: '全球市场',
    sectors: '行业板块',
    news: '7×24快讯',
    settings: '设置',
  };
  return titles[currentRoute.value] || 'FundVue';
});

const lastUpdated = computed(() => fundStore.lastUpdated || commodityStore.lastUpdated || indexStore.lastUpdated);

function toggleSidebar() {
  sidebarCollapsed.value = !sidebarCollapsed.value;
}

async function checkHealth() {
  try {
    const health = await healthApi.getSimpleHealth();
    healthStatus.value = health.status === 'healthy' ? 'healthy' : 'degraded';
    statusText.value = health.status === 'healthy' ? '已连接' : '重连中...';
  } catch {
    healthStatus.value = 'unhealthy';
    statusText.value = '连接失败';
  }
}

async function refresh() {
  if (refreshing.value) return;

  refreshing.value = true;
  try {
    // 分布刷新，避免同时请求造成阻塞
    fundStore.fetchFunds();
    await new Promise(resolve => setTimeout(resolve, 2000)); // 2秒后刷新商品
    commodityStore.fetchCategories();
    await new Promise(resolve => setTimeout(resolve, 2000)); // 再过2秒后刷新指数
    indexStore.fetchIndices();
    sectorStore.refresh();
    await checkHealth();
  } finally {
    setTimeout(() => {
      refreshing.value = false;
    }, 500);
  }
}

function startAutoRefresh() {
  if (!fundStore.autoRefresh) return;

  const baseInterval = (fundStore.refreshInterval || 30) * 1000;

  // 分布刷新：每个数据源间隔几秒，避免同时请求
  // 基金：基准间隔
  fundTimer = window.setInterval(() => {
    if (fundStore.autoRefresh) {
      fundStore.fetchFunds();
    }
  }, baseInterval);

  // 商品：基准间隔 + 5秒
  commodityTimer = window.setInterval(() => {
    if (fundStore.autoRefresh) {
      commodityStore.fetchCategories();
    }
  }, baseInterval + 5000);

  // 指数：基准间隔 + 10秒
  indexTimer = window.setInterval(() => {
    if (fundStore.autoRefresh) {
      indexStore.fetchIndices();
    }
  }, baseInterval + 10000);
}

function stopAutoRefresh() {
  if (fundTimer) {
    clearInterval(fundTimer);
    fundTimer = null;
  }
  if (commodityTimer) {
    clearInterval(commodityTimer);
    commodityTimer = null;
  }
  if (indexTimer) {
    clearInterval(indexTimer);
    indexTimer = null;
  }
}

// 监听自动刷新设置变化
watch(() => fundStore.autoRefresh, (enabled) => {
  if (enabled) {
    startAutoRefresh();
  } else {
    stopAutoRefresh();
  }
});

watch(() => fundStore.refreshInterval, () => {
  stopAutoRefresh();
  startAutoRefresh();
});

onMounted(async () => {
  await refresh();
  startAutoRefresh();
  healthTimer = window.setInterval(checkHealth, 30000);
});

onUnmounted(() => {
  stopAutoRefresh();
  if (healthTimer) {
    clearInterval(healthTimer);
  }
});
</script>

<style lang="scss" scoped>
.app-layout {
  display: flex;
  min-height: 100vh;
  background: var(--color-bg-primary);
}

/* Sidebar */
.sidebar {
  width: var(--sidebar-width);
  background: var(--color-bg-secondary);
  border-right: 1px solid var(--color-divider);
  display: flex;
  flex-direction: column;
  transition: width var(--transition-normal);
  position: fixed;
  left: 0;
  top: 0;
  bottom: 0;
  z-index: 100;
}

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

/* Main Content */
.main-content {
  flex: 1;
  margin-left: var(--sidebar-width);
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  transition: margin-left var(--transition-normal);
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
  background: var(--color-bg-card);
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
</style>
