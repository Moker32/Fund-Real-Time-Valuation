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
            <div class="search-input-wrapper">
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
                @input="handleSearch"
              />
              <button v-if="searchQuery" class="clear-button" @click="clearSearch">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <circle cx="12" cy="12" r="10"/>
                  <path d="M15 9l-6 6M9 9l6 6"/>
                </svg>
              </button>
            </div>
          </div>

          <!-- Loading State -->
          <div v-if="store.searchLoading" class="loading-state">
            <div class="loading-spinner"></div>
            <span>搜索中...</span>
          </div>

          <!-- Error State -->
          <div v-else-if="store.searchError" class="error-state">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10"/>
              <path d="M12 8v4M12 16h.01"/>
            </svg>
            <span>{{ store.searchError }}</span>
            <button class="retry-button" @click="handleSearch">重试</button>
          </div>

          <!-- Empty State -->
          <div v-else-if="!store.searchQuery && !hasSearched" class="empty-state">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="11" cy="11" r="8"/>
              <path d="M21 21l-4.35-4.35"/>
            </svg>
            <span>输入关键词搜索商品</span>
            <span class="hint">支持代码（如 GC=F）或名称（如 黄金）</span>
          </div>

          <!-- No Results State -->
          <div v-else-if="hasSearched && results.length === 0" class="empty-state">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10"/>
              <path d="M8 15s1.5-2 4-2 4 2 4 2M9 9h.01M15 9h.01"/>
            </svg>
            <span>未找到相关商品</span>
            <span class="hint">请尝试其他关键词</span>
          </div>

          <!-- Results List -->
          <div v-else class="results-section">
            <div class="results-list">
              <div
                v-for="result in results"
                :key="result.symbol"
                class="result-item"
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
import { ref, watch, nextTick } from 'vue';
import { useCommodityStore } from '@/stores/commodityStore';
import type { CommoditySearchResult } from '@/types';

const props = defineProps<{
  visible: boolean;
}>();

const emit = defineEmits<{
  close: [];
  added: [symbol: string, name: string];
}>();

const store = useCommodityStore();
const searchInputRef = ref<Element | null>(null);
const searchQuery = ref('');
const results = ref<CommoditySearchResult[]>([]);
const hasSearched = ref(false);

// 监听对话框显示
watch(() => props.visible, (visible) => {
  if (visible) {
    // 打开时聚焦搜索框
    nextTick(() => {
      searchInputRef.value?.focus();
    });
    // 加载所有可用商品
    store.fetchAvailableCommodities().then((data) => {
      results.value = data;
    });
  } else {
    // 关闭时清空
    clearSearch();
  }
});

// 监听可用商品列表变化
watch(() => store.searchResults, (newResults) => {
  if (!searchQuery.value && hasSearched.value === false) {
    results.value = newResults;
  }
});

// 搜索处理
function handleSearch() {
  if (!searchQuery.value.trim()) {
    results.value = store.searchResults;
    hasSearched.value = false;
    return;
  }
  hasSearched.value = true;
  store.executeSearch(searchQuery.value).then((data) => {
    results.value = data;
  });
}

// 清空搜索
function clearSearch() {
  searchQuery.value = '';
  hasSearched.value = false;
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

  const success = await store.addToWatchlist(
    result.symbol,
    result.name,
    result.category
  );

  if (success) {
    emit('added', result.symbol, result.name);
    // 显示成功提示后关闭或保持打开
    // 可以在这里添加 toast 提示
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

  &:focus-within {
    border-color: var(--color-primary);
    box-shadow: 0 0 0 2px var(--color-primary-light);
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

.results-section {
  flex: 1;
  overflow-y: auto;
  padding: 0 var(--spacing-lg);
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

  &:hover {
    background: var(--color-primary-hover);
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

.results-count {
  font-size: var(--font-size-sm);
  color: var(--color-text-tertiary);
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
