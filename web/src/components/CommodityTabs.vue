<template>
  <div class="commodity-tabs">
    <div class="tabs-header">
      <button
        v-for="category in categories"
        :key="category.id"
        class="tab-button"
        :class="{ active: activeCategory === category.id }"
        @click="selectCategory(category.id)"
      >
        <span class="tab-icon">
          <svg v-if="category.icon === 'diamond'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M6 3h12l4 6-10 12H2L6 3z"/>
          </svg>
          <svg v-else-if="category.icon === 'flame'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M12 2c0 0-6 4-6 8 0 2.5 1.5 5 4 6-1 2-1 4 1 5 2.5-2 3-2 5 2.5 2 2.5-4 1-2 6 1 0 4-3 4-8C22 6 16 2 12 2z"/>
          </svg>
          <svg v-else-if="category.icon === 'cube'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/>
          </svg>
          <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10"/>
          </svg>
        </span>
        <span class="tab-name">{{ category.name }}</span>
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
interface Category {
  id: string;
  name: string;
  icon: string;
}

interface Props {
  categories: Category[];
  activeCategory: string | null;
}

withDefaults(defineProps<Props>(), {
  categories: () => [],
  activeCategory: null,
});

const emit = defineEmits<{
  (e: 'category-select', categoryId: string): void;
}>();

function selectCategory(categoryId: string) {
  emit('category-select', categoryId);
}
</script>

<style lang="scss" scoped>
.commodity-tabs {
  width: 100%;
}

.tabs-header {
  display: flex;
  gap: var(--spacing-xs);
  padding: var(--spacing-sm) 0;
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;

  &::-webkit-scrollbar {
    display: none;
  }
}

.tab-button {
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
  padding: var(--spacing-xs) var(--spacing-md);
  background: var(--color-bg-secondary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-full);
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  cursor: pointer;
  transition: all var(--transition-fast);
  white-space: nowrap;

  &:hover {
    background: var(--color-bg-tertiary);
    border-color: var(--color-border-light);
    color: var(--color-text-primary);
  }

  &.active {
    background: var(--color-primary);
    border-color: var(--color-primary);
    color: white;

    .tab-icon {
      color: white;
    }
  }
}

.tab-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  color: var(--color-text-tertiary);

  svg {
    width: 100%;
    height: 100%;
  }
}

.tab-name {
  font-family: var(--font-sans);
}
</style>
