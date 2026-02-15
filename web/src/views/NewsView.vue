<script setup lang="ts">
</script>

<template>
  <div class="news-view">
    <div class="view-header">
      <h2 class="section-title">7×24快讯</h2>
    </div>

    <!-- Coming Soon State -->
    <div class="coming-soon">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <path d="M4 22h16a2 2 0 0 0 2-2V4a2 2 0 0 0-2-2H8a2 2 0 0 0-2 2v16a2 2 0 0 1-2 2zm0 0a2 2 0 0 1-2-2v-9c0-1.1.9-2 2-2h2"/>
        <path d="M18 14h-8"/>
        <path d="M15 18h-5"/>
        <path d="M10 6h8v4h-8z"/>
      </svg>
      <span>即将上线</span>
      <p>财经新闻功能正在开发中，敬请期待...</p>
    </div>
  </div>
</template>

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
  font-size: var(--font-size-xl);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
  margin: 0;
}

.coming-soon {
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
    font-size: var(--font-size-xl);
    font-weight: var(--font-weight-semibold);
  }

  p {
    font-size: var(--font-size-sm);
    opacity: 0.7;
    margin: 0;
  }
}
</style>
