<template>
  <Teleport to="body">
    <Transition name="modal">
      <div v-if="visible" class="search-dialog-overlay" @click.self="handleClose">
        <div class="search-dialog">
          <!-- Header -->
          <div class="dialog-header">
            <h3 class="dialog-title">添加关注商品</h3>
            <button class="close-button" @click="handleClose">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M18 6L6 18M6 6l12 12"/>
              </svg>
            </button>
          </div>

          <!-- Search Input -->
          <div class="search-section">
            <div class="search-input-wrapper" :class="{ 'has-error': localError }">
              <svg class="search-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="11" cy="11" r="8"/>
                <path d="M21 21l-4.35-4.35"/>
              </svg>
              <input
                ref="searchInputRef"
                v-model="searchQuery"
                type="text"
                class="search-input"
                placeholder="搜索商品代码或名称（如：黄金、GC）"
                :disabled="isLoading"
                @input="handleSearchInput"
                @keydown.enter="handleSearch"
              />
              <button v-if="searchQuery && !isLoading" class="clear-button" @click="clearSearch">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <circle cx="12" cy="12" r="10"/>
                  <path d="M15 9l-6 6M9 9l6 6"/>
                </svg>
              </button>
              <div v-if="isLoading" class="input-spinner">
                <div class="spinner"></div>
              </div>
            </div>
            <!-- 输入错误提示 -->
            <div v-if="localError" class="input-error">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="12" cy="12" r="10"/>
                <path d="M12 8v4M12 16h.01"/>
              </svg>
              <span>{{ localError }}</span>
            </div>
          </div>

          <!-- Loading State -->
          <div v-if="isLoading && !hasResults" class="loading-state">
            <div class="loading-spinner"></div>
            <span>搜索中...</span>
          </div>

          <!-- Error State -->
          <div v-else-if="displayError" class="error-state">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10"/>
              <path d="M12 8v4M12 16h.01"/>
            </svg>
            <span>{{ displayError }}</span>
            <div class="error-actions">
              <button class="retry-button" @click="handleRetry">重试</button>
              <button v-if="canUseOfflineData" class="offline-button" @click="useOfflineData">
                使用离线数据
              </button>
            </div>
          </div>

          <!-- Empty State -->
          <div v-else-if="!searchQuery && !hasSearched" class="empty-state">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="11" cy="11" r="8"/>
              <path d="M21 21l-4.35-4.35"/>
            </svg>
            <span>输入关键词搜索商品</span>
            <span class="hint">支持代码（如 GC=F）或名称（如 黄金）</span>
          </div>

          <!-- No Results State -->
          <div v-else-if="hasSearched && results.length === 0 && !isLoading" class="empty-state">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10"/>
              <path d="M8 15s1.5-2 4-2 4 2 4 2M9 9h.01M15 9h.01"/>
            </svg>
            <span>未找到相关商品</span>
            <span class="hint">请尝试其他关键词</span>
          </div>

          <!-- Results List -->
          <div v-else-if="results.length > 0" class="results-section">
            <div class="results-header">
              <span class="results-count">找到 {{ results.length }} 个商品</span>
              <span v-if="isLoading" class="updating-hint">更新中...</span>
            </div>
            <div class="results-list">
              <div
                v-for="result in results"
                :key="result.symbol"
                class="result-item"
                :class="{ 'is-adding': addingSymbol === result.symbol }"
                @click="handleSelect(result)"
              >
                <div class="result-info">
                  <span class="result-symbol">{{ result.symbol }}</span>
                  <span class="result-name">{{ result.name }}</span>
                </div>
                <div class="result-meta">
                  <span class="result-exchange">{{ result.exchange }}</span>
                  <span class="result-category">{{ formatCategory(result.category) }}</span>
                </div>
                <button
                  v-if="isInWatchlist(result.symbol)"
                  class="added-badge"
                  disabled
                >
                  已关注
                </button>
                <button
                  v-else-if="addingSymbol === result.symbol"
                  class="add-button loading"
                  disabled
                >
                  <span class="btn-spinner"></span>
                  添加中...
                </button>
                <button
                  v-else
                  class="add-button"
                  @click.stop="handleSelect(result)"
                >
                  添加
                </button>
              </div>
            </div>
          </div>

          <!-- Footer -->
          <div v-if="results.length > 0" class="dialog-footer">
            <span class="results-count">找到 {{ results.length }} 个商品</span>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, watch, nextTick, computed } from 'vue';
import { useCommodityStore } from '@/stores/commodityStore';
import type { CommoditySearchResult } from '@/types';

// 定义 clearTimeout 类型
declare function clearTimeout(id: ReturnType<typeof setTimeout>): void;

const props = defineProps<{
  visible: boolean;
}>();

const emit = defineEmits<{
  close: [];
  added: [symbol: string, name: string];
  error: [message: string];
}>();

const store = useCommodityStore();
const searchInputRef = ref<HTMLInputElement | null>(null);
const searchQuery = ref('');
const results = ref<CommoditySearchResult[]>([]);
const hasSearched = ref(false);
const isLoading = ref(false);
const localError = ref<string | null>(null);
const addingSymbol = ref<string | null>(null);
const retryCount = ref(0);
const maxRetries = 2;

// 离线数据缓存（用于网络错误时）
const offlineData = ref<CommoditySearchResult[]>([]);
const canUseOfflineData = computed(() => offlineData.value.length > 0);

// 计算是否有结果
const hasResults = computed(() => results.value.length > 0);

// 计算显示的错误信息（优先显示本地错误，其次是 store 错误）
const displayError = computed(() => {
  if (localError.value) return localError.value;
  if (store.searchError) return store.searchError;
  return null;
});

// 监听对话框显示
watch(() => props.visible, (visible) => {
  if (visible) {
    // 打开时重置状态
    resetState();
    // 聚焦搜索框
    nextTick(() => {
      searchInputRef.value?.focus();
    });
    // 加载所有可用商品
    loadAvailableCommodities();
  } else {
    // 关闭时清空
    clearSearch();
  }
});

// 监听 store 中的搜索结果变化
watch(() => store.searchResults, (newResults) => {
  if (!searchQuery.value && hasSearched.value === false) {
    results.value = newResults;
    // 缓存离线数据
    if (newResults.length > 0) {
      offlineData.value = [...newResults];
    }
  }
});

// 监听 store 错误
watch(() => store.searchError, (error) => {
  if (error) {
    isLoading.value = false;
  }
});

// 重置状态
function resetState() {
searchQuery.value = '';
results.value = [];
hasSearched.value = false;
isLoading.value = false;
localError.value = null;
addingSymbol.value = null;
retryCount.value = 0;
// 清除搜索超时
if (searchTimeout) {
  clearTimeout(searchTimeout);
  searchTimeout = null;
}
}

// 加载所有可用商品
async function loadAvailableCommodities() {
  isLoading.value = true;
  localError.value = null;

  try {
    const data = await store.fetchAvailableCommodities();
    results.value = data;
    // 缓存离线数据
    if (data.length > 0) {
      offlineData.value = [...data];
    }
  } catch (err) {
    console.error('[CommoditySearchDialog] 加载可用商品失败:', err);
    // 如果有离线数据，使用离线数据
    if (offlineData.value.length > 0) {
      results.value = [...offlineData.value];
      localError.value = '使用离线数据，可能不是最新';
    } else {
      localError.value = store.searchError || '加载商品列表失败';
    }
  } finally {
    isLoading.value = false;
  }
}

// 搜索输入处理（防抖）
let searchTimeout: ReturnType<typeof setTimeout> | null = null;
function handleSearchInput() {
  // 清除之前的错误
  localError.value = null;

  if (searchTimeout) {
    clearTimeout(searchTimeout);
  }

  if (!searchQuery.value.trim()) {
    results.value = store.searchResults;
    hasSearched.value = false;
    return;
  }

  searchTimeout = setTimeout(() => {
    performSearch();
  }, 300);
}

// 执行搜索
async function performSearch() {
  if (!searchQuery.value.trim()) {
    results.value = store.searchResults;
    hasSearched.value = false;
    return;
  }

  hasSearched.value = true;
  isLoading.value = true;
  localError.value = null;

  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    retryCount.value = attempt;
    try {
      const data = await store.searchCommodities(searchQuery.value);
      results.value = data;
      isLoading.value = false;
      return;
    } catch (err) {
      console.error(`[CommoditySearchDialog] 搜索失败 (尝试 ${attempt + 1}/${maxRetries + 1}):`, err);

      if (attempt < maxRetries) {
        // 指数退避重试
        const delayMs = 1000 * Math.pow(2, attempt);
        await new Promise(resolve => setTimeout(resolve, delayMs));
      }
    }
  }

  // 所有重试都失败了
  isLoading.value = false;

  // 如果有离线数据，尝试在离线数据中搜索
  if (offlineData.value.length > 0) {
    const query = searchQuery.value.toLowerCase();
    const filtered = offlineData.value.filter(item =>
      item.symbol.toLowerCase().includes(query) ||
      item.name.toLowerCase().includes(query)
    );
    if (filtered.length > 0) {
      results.value = filtered;
      localError.value = '使用离线数据搜索，结果可能不完整';
      return;
    }
  }

  localError.value = store.searchError || '搜索失败，请稍后重试';
  emit('error', localError.value);
}

// 搜索处理（回车键）
function handleSearch() {
  if (searchTimeout) {
    clearTimeout(searchTimeout);
  }
  performSearch();
}

// 重试
function handleRetry() {
  localError.value = null;
  if (searchQuery.value.trim()) {
    performSearch();
  } else {
    loadAvailableCommodities();
  }
}

// 使用离线数据
function useOfflineData() {
  results.value = [...offlineData.value];
  localError.value = null;
}

// 清空搜索
function clearSearch() {
  searchQuery.value = '';
  hasSearched.value = false;
  localError.value = null;
  store.clearSearch();
  results.value = store.searchResults;
}

// 格式化分类名称
function formatCategory(category: string): string {
  const names: Record<string, string> = {
    precious_metal: '贵金属',
    energy: '能源',
    base_metal: '基本金属',
    agriculture: '农产品',
    crypto: '加密货币',
    other: '其他',
  };
  return names[category] || category;
}

// 检查是否已在关注列表
function isInWatchlist(symbol: string): boolean {
  return store.watchedCommodities.some(
    (item) => item.symbol.toUpperCase() === symbol.toUpperCase()
  );
}

// 选择商品
async function handleSelect(result: CommoditySearchResult) {
  if (isInWatchlist(result.symbol)) {
    return;
  }

  // 防止重复点击
  if (addingSymbol.value) {
    return;
  }

  addingSymbol.value = result.symbol;

  try {
    const success = await store.addToWatchlist(
      result.symbol,
      result.name,
      result.category
    );

    if (success) {
      emit('added', result.symbol, result.name);
      // 可以在这里添加 toast 提示
    } else {
      localError.value = store.watchlistError || '添加失败';
      emit('error', localError.value);
    }
  } catch (err) {
    const errorMsg = err instanceof Error ? err.message : '添加失败';
    localError.value = errorMsg;
    emit('error', errorMsg);
  } finally {
    addingSymbol.value = null;
  }
}

// 关闭对话框
function handleClose() {
  emit('close');
}
</script>

<style lang="scss" scoped>
.search-dialog-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: var(--spacing-lg);
}

.search-dialog {
  background: var(--color-bg-primary);
  border-radius: var(--radius-lg);
  width: 100%;
  max-width: 500px;
  max-height: 80vh;
  display: flex;
  flex-direction: column;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
  animation: slideIn var(--transition-normal);
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateY(-20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.dialog-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--spacing-lg);
  border-bottom: 1px solid var(--color-divider);
}

.dialog-title {
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}

.close-button {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: none;
  border-radius: var(--radius-md);
  cursor: pointer;
  color: var(--color-text-tertiary);
  transition: all var(--transition-fast);

  svg {
    width: 20px;
    height: 20px;
  }

  &:hover {
    background: var(--color-bg-secondary);
    color: var(--color-text-primary);
  }
}

.search-section {
  padding: var(--spacing-md) var(--spacing-lg);
}

.search-input-wrapper {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  background: var(--color-bg-secondary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: 0 var(--spacing-md);
  transition: all var(--transition-fast);

  &:focus-within {
    border-color: var(--color-primary);
    box-shadow: 0 0 0 2px var(--color-primary-light);
  }

  &.has-error {
    border-color: var(--color-fall);
    box-shadow: 0 0 0 2px rgba(var(--color-fall-rgb), 0.2);
  }
}

.search-icon {
  width: 20px;
  height: 20px;
  color: var(--color-text-tertiary);
  flex-shrink: 0;
}

.search-input {
  flex: 1;
  height: 44px;
  background: transparent;
  border: none;
  outline: none;
  font-size: var(--font-size-md);
  color: var(--color-text-primary);

  &::placeholder {
    color: var(--color-text-tertiary);
  }

  &:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }
}

.clear-button {
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-bg-tertiary);
  border: none;
  border-radius: 50%;
  cursor: pointer;
  color: var(--color-text-tertiary);
  transition: all var(--transition-fast);

  svg {
    width: 14px;
    height: 14px;
  }

  &:hover {
    background: var(--color-border);
    color: var(--color-text-primary);
  }
}

.input-spinner {
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;

  .spinner {
    width: 16px;
    height: 16px;
    border: 2px solid var(--color-border);
    border-top-color: var(--color-primary);
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }
}

.input-error {
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
  margin-top: var(--spacing-xs);
  font-size: var(--font-size-sm);
  color: var(--color-fall);

  svg {
    width: 14px;
    height: 14px;
  }
}

.results-section {
  flex: 1;
  overflow-y: auto;
  padding: 0 var(--spacing-lg);
}

.results-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--spacing-xs) 0;
  margin-bottom: var(--spacing-xs);
}

.results-count {
  font-size: var(--font-size-sm);
  color: var(--color-text-tertiary);
}

.updating-hint {
  font-size: var(--font-size-xs);
  color: var(--color-primary);
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);

  &::before {
    content: '';
    width: 6px;
    height: 6px;
    background: var(--color-primary);
    border-radius: 50%;
    animation: pulse 1s ease-in-out infinite;
  }
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.5;
  }
}

.results-list {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
}

.result-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
  padding: var(--spacing-md);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: background var(--transition-fast);

  &:hover {
    background: var(--color-bg-secondary);
  }

  &.is-adding {
    opacity: 0.7;
    pointer-events: none;
  }
}

.result-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.result-symbol {
  font-size: var(--font-size-md);
  font-weight: var(--font-weight-medium);
  font-family: var(--font-mono);
  color: var(--color-text-primary);
}

.result-name {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

.result-meta {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 2px;
}

.result-exchange {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
}

.result-category {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
  background: var(--color-bg-secondary);
  padding: 2px 6px;
  border-radius: var(--radius-sm);
}

.add-button {
  padding: var(--spacing-xs) var(--spacing-md);
  background: var(--color-primary);
  border: none;
  border-radius: var(--radius-md);
  color: white;
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  cursor: pointer;
  transition: background var(--transition-fast);
  flex-shrink: 0;
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);

  &:hover:not(:disabled) {
    background: var(--color-primary-hover);
  }

  &:disabled {
    opacity: 0.7;
    cursor: not-allowed;
  }

  &.loading {
    background: var(--color-primary-light);
  }

  .btn-spinner {
    width: 12px;
    height: 12px;
    border: 2px solid rgba(255, 255, 255, 0.3);
    border-top-color: white;
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }
}

.added-badge {
  padding: var(--spacing-xs) var(--spacing-md);
  background: var(--color-bg-secondary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  color: var(--color-text-tertiary);
  font-size: var(--font-size-sm);
  cursor: default;
  flex-shrink: 0;
}

.dialog-footer {
  padding: var(--spacing-md) var(--spacing-lg);
  border-top: 1px solid var(--color-divider);
  text-align: center;
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

  .hint {
    font-size: var(--font-size-sm);
    opacity: 0.7;
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

.error-actions {
  display: flex;
  gap: var(--spacing-sm);
  margin-top: var(--spacing-sm);
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

.offline-button {
  padding: var(--spacing-xs) var(--spacing-md);
  background: var(--color-bg-secondary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
  cursor: pointer;
  transition: all var(--transition-fast);

  &:hover {
    background: var(--color-bg-tertiary);
  }
}

// Modal transition
.modal-enter-active,
.modal-leave-active {
  transition: opacity var(--transition-normal);
}

.modal-enter-active .search-dialog,
.modal-leave-active .search-dialog {
  transition: transform var(--transition-normal);
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}

.modal-enter-from .search-dialog,
.modal-leave-to .search-dialog {
  transform: translateY(-20px);
}
</style>
