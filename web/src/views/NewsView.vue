<template>
  <div class="news-view">
    <div class="view-header">
      <h2 class="section-title">7×24快讯</h2>
      <span class="last-updated" v-if="newsStore.lastUpdated">
        更新时间: {{ newsStore.lastUpdated }}
      </span>
    </div>

    <!-- Category Tabs -->
    <div class="category-tabs">
      <button
        v-for="cat in newsStore.categories"
        :key="cat.id"
        :class="['category-tab', { active: newsStore.activeCategory === cat.id }]"
        @click="newsStore.setCategory(cat.id)"
      >
        <span class="tab-icon">{{ cat.icon }}</span>
        <span class="tab-name">{{ cat.name }}</span>
      </button>
    </div>

    <!-- Error State -->
    <div v-if="newsStore.error" class="error-state">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <circle cx="12" cy="12" r="10"/>
        <path d="M12 8V12M12 16H12.01"/>
      </svg>
      <span>{{ newsStore.error }}</span>
      <button @click="newsStore.retry">重试</button>
    </div>

    <!-- Loading State -->
    <div v-else-if="newsStore.loading && newsStore.news.length === 0" class="loading-state">
      <div class="loading-list">
        <div v-for="i in 8" :key="i" class="news-skeleton">
          <div class="skeleton-time"></div>
          <div class="skeleton-title"></div>
        </div>
      </div>
    </div>

    <!-- Empty State -->
    <div v-else-if="newsStore.news.length === 0" class="empty-state">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <path d="M4 22h16a2 2 0 0 0 2-2V4a2 2 0 0 0-2-2H8a2 2 0 0 0-2 2v16a2 2 0 0 1-2 2zm0 0a2 2 0 0 1-2-2v-9c0-1.1.9-2 2-2h2"/>
        <path d="M18 14h-8"/>
        <path d="M15 18h-5"/>
        <path d="M10 6h8v4h-8z"/>
      </svg>
      <span>暂无新闻</span>
      <p>该分类下暂无新闻数据</p>
    </div>

    <!-- News List -->
    <div v-else class="news-list">
      <a
        v-for="(item, index) in newsStore.news"
        :key="index"
        :href="item.url"
        target="_blank"
        rel="noopener noreferrer"
        class="news-item"
      >
        <div class="news-time">{{ item.time }}</div>
        <div class="news-title">{{ item.title }}</div>
        <div class="news-source">{{ item.source }}</div>
      </a>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue';
import { useNewsStore } from '@/stores/newsStore';

const newsStore = useNewsStore();

onMounted(async () => {
  await newsStore.fetchCategories();
  if (newsStore.news.length === 0) {
    await newsStore.fetchNews({ force: true });
  }
});
</script>

<style lang="scss" scoped>
.news-view {
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
  margin: 0;
}

.last-updated {
  font-size: var(--font-size-sm);
  color: var(--color-text-tertiary);
}

.category-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: var(--spacing-sm);
  margin-bottom: var(--spacing-lg);
}

.category-tab {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  background: var(--color-bg-secondary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-full);
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
  cursor: pointer;
  transition: all var(--transition-fast);

  &:hover {
    background: var(--color-bg-tertiary);
    border-color: var(--color-border-light);
  }

  &.active {
    background: var(--color-primary);
    border-color: var(--color-primary);
    color: white;
  }

  .tab-icon {
    font-size: 14px;
  }
}

.news-list {
  display: flex;
  flex-direction: column;
  gap: 1px;
  background: var(--color-divider);
  border-radius: var(--radius-md);
  overflow: hidden;
}

.news-item {
  display: grid;
  grid-template-columns: 80px 1fr 80px;
  align-items: center;
  gap: var(--spacing-md);
  padding: var(--spacing-md) var(--spacing-lg);
  background: var(--color-bg-secondary);
  text-decoration: none;
  color: var(--color-text-primary);
  transition: background var(--transition-fast);

  &:hover {
    background: var(--color-bg-tertiary);
  }

  .news-time {
    font-size: var(--font-size-sm);
    color: var(--color-text-tertiary);
    font-family: var(--font-mono);
    white-space: nowrap;
  }

  .news-title {
    font-size: var(--font-size-sm);
    line-height: 1.5;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .news-source {
    font-size: var(--font-size-xs);
    color: var(--color-text-tertiary);
    text-align: right;
    white-space: nowrap;
  }
}

.loading-list {
  display: flex;
  flex-direction: column;
  gap: 1px;
  background: var(--color-divider);
  border-radius: var(--radius-md);
  overflow: hidden;
}

.news-skeleton {
  padding: var(--spacing-md) var(--spacing-lg);
  background: var(--color-bg-secondary);

  .skeleton-time {
    width: 60px;
    height: 14px;
    background: var(--color-skeleton);
    border-radius: var(--radius-sm);
    margin-bottom: 8px;
    animation: pulse 1.5s ease-in-out infinite;
  }

  .skeleton-title {
    width: 80%;
    height: 16px;
    background: var(--color-skeleton);
    border-radius: var(--radius-sm);
    animation: pulse 1.5s ease-in-out infinite;
    animation-delay: 0.1s;
  }
}

@keyframes pulse {
  0%, 100% { opacity: 0.4; }
  50% { opacity: 0.7; }
}

.error-state,
.loading-state,
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--spacing-2xl);
  gap: var(--spacing-md);
  color: var(--color-text-secondary);

  svg {
    width: 48px;
    height: 48px;
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

  button {
    margin-top: var(--spacing-sm);
    padding: var(--spacing-sm) var(--spacing-lg);
    background: var(--color-bg-tertiary);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    color: var(--color-text-primary);
    font-size: var(--font-size-sm);
    cursor: pointer;
    transition: all var(--transition-fast);

    &:hover {
      background: var(--color-bg-card);
      border-color: var(--color-border-light);
    }
  }
}
</style>
