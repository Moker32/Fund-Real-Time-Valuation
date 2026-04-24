<template>
  <div class="economic-calendar-view">
    <!-- Header -->
    <div class="view-header">
      <h2 class="section-title">财经日历</h2>
      <span class="last-updated" v-if="sentimentStore.lastUpdated">
        更新时间: {{ sentimentStore.lastUpdated }}
      </span>
    </div>

    <!-- Controls -->
    <div class="controls">
      <div class="date-picker">
        <input 
          type="date" 
          :value="displayDate"
          @change="handleDateChange"
          class="date-input"
        />
      </div>
      <div class="filter-controls">
        <button 
          :class="['filter-btn', { active: sentimentStore.showImportantOnly }]"
          @click="sentimentStore.toggleImportantOnly"
        >
          <span class="filter-icon">⭐</span>
          仅看重要 ({{ importantCount }})
        </button>
      </div>
    </div>

    <!-- Error State -->
    <div v-if="sentimentStore.economicError" class="error-state">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <circle cx="12" cy="12" r="10"/>
        <path d="M12 8V12M12 16H12.01"/>
      </svg>
      <span>{{ sentimentStore.economicError }}</span>
      <button @click="sentimentStore.retry">重试</button>
    </div>

    <!-- Loading State -->
    <div v-else-if="sentimentStore.economicLoading && sentimentStore.economicEvents.length === 0" class="loading-state">
      <div class="loading-list">
        <div v-for="i in 8" :key="i" class="event-skeleton">
          <div class="skeleton-time"></div>
          <div class="skeleton-region"></div>
          <div class="skeleton-event"></div>
          <div class="skeleton-values"></div>
        </div>
      </div>
    </div>

    <!-- Empty State -->
    <div v-else-if="sentimentStore.filteredEvents.length === 0" class="empty-state">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <rect x="3" y="4" width="18" height="18" rx="2" ry="2"/>
        <line x1="16" y1="2" x2="16" y2="6"/>
        <line x1="8" y1="2" x2="8" y2="6"/>
        <line x1="3" y1="10" x2="21" y2="10"/>
      </svg>
      <span>暂无财经事件</span>
      <p>{{ sentimentStore.showImportantOnly ? '当天无重要事件发布' : '请选择其他日期' }}</p>
    </div>

    <!-- Events List -->
    <div v-else class="events-container">
      <div
        v-for="(time, timeIndex) in sentimentStore.sortedTimeKeys"
        :key="time"
        class="time-group"
        :style="{ animationDelay: `${timeIndex * 100}ms` }"
      >
        <div class="time-header">
          <span class="time-label">{{ time }}</span>
          <span class="event-count">{{ sentimentStore.eventsByTime[time].length }}条</span>
        </div>
        <div class="events-list">
          <div
            v-for="(event, index) in sentimentStore.eventsByTime[time]"
            :key="index"
            :class="['event-card', { important: event.重要性 >= 2 }]"
            :style="{ animationDelay: `${timeIndex * 100 + index * 50}ms` }"
          >
            <div class="event-main">
              <div class="event-region">
                <span class="region-badge">{{ event.地区 }}</span>
                <span v-if="event.重要性 >= 2" class="importance-badge">重要</span>
              </div>
              <div class="event-name">{{ event.事件 }}</div>
            </div>
            <div class="event-values">
              <div class="value-item">
                <span class="value-label">公布</span>
                <span :class="['value-number', getValueClass(event)]">
                  {{ formatValue(event.公布) }}
                </span>
              </div>
              <div class="value-item">
                <span class="value-label">预期</span>
                <span class="value-number">{{ formatValue(event.预期) }}</span>
              </div>
              <div class="value-item">
                <span class="value-label">前值</span>
                <span class="value-number">{{ formatValue(event.前值) }}</span>
              </div>
            </div>
            <div class="event-comparison" v-if="event.公布 !== null && event.预期 !== null">
              <span :class="['comparison-tag', getComparisonClass(event)]">
                {{ getComparisonText(event) }}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Summary Stats -->
    <div class="stats-summary" v-if="sentimentStore.economicEvents.length > 0">
      <div class="stat-item">
        <span class="stat-value">{{ sentimentStore.economicEvents.length }}</span>
        <span class="stat-label">总事件</span>
      </div>
      <div class="stat-item">
        <span class="stat-value">{{ importantCount }}</span>
        <span class="stat-label">重要事件</span>
      </div>
      <div class="stat-item">
        <span class="stat-value">{{ releasedCount }}</span>
        <span class="stat-label">已公布</span>
      </div>
      <div class="stat-item">
        <span class="stat-value">{{ pendingCount }}</span>
        <span class="stat-label">待公布</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue';
import { useSentimentStore } from '@/stores/sentimentStore';
import type { EconomicEventItem } from '@/types';

const sentimentStore = useSentimentStore();

// Computed
 
const displayDate = computed(() => {
  const date = sentimentStore.selectedDate || getTodayDate();
  return `${date.slice(0, 4)}-${date.slice(4, 6)}-${date.slice(6, 8)}`;
});

 
const importantCount = computed(() => {
  return sentimentStore.economicEvents.filter(e => e.重要性 >= 2).length;
});

 
const releasedCount = computed(() => {
  return sentimentStore.economicEvents.filter(e => e.公布 !== null).length;
});

 
const pendingCount = computed(() => {
  return sentimentStore.economicEvents.filter(e => e.公布 === null).length;
});

// Methods
function handleDateChange(event: Event) {
  const target = event.target as HTMLInputElement;
  const dateStr = target.value.replace(/-/g, '');
  sentimentStore.fetchEconomicEvents(dateStr);
}

function formatValue(value: number | null): string {
  if (value === null) return '--';
  return value.toLocaleString('en-US', { maximumFractionDigits: 2 });
}

function getValueClass(event: EconomicEventItem): string {
  if (event.公布 === null) return 'pending';
  if (event.预期 === null) return '';
  
  if (event.公布 > event.预期) return 'better';
  if (event.公布 < event.预期) return 'worse';
  return '';
}

function getComparisonClass(event: EconomicEventItem): string {
  if (event.公布 === null || event.预期 === null) return '';
  
  if (event.公布 > event.预期) return 'positive';
  if (event.公布 < event.预期) return 'negative';
  return 'neutral';
}

function getComparisonText(event: EconomicEventItem): string {
  if (event.公布 === null || event.预期 === null) return '';
  
  const diff = event.公布 - event.预期;
  const percent = Math.abs(event.预期) > 0 
    ? ((diff / event.预期) * 100).toFixed(1) 
    : Math.abs(diff).toFixed(2);
  
  if (diff > 0) return `+${percent}% 超预期`;
  if (diff < 0) return `${percent}% 低于预期`;
  return '符合预期';
}

function getTodayDate(): string {
  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, '0');
  const day = String(now.getDate()).padStart(2, '0');
  return `${year}${month}${day}`;
}

// Lifecycle
onMounted(async () => {
  if (sentimentStore.economicEvents.length === 0) {
    await sentimentStore.fetchEconomicEvents();
  }
});
</script>

<style lang="scss" scoped>
.economic-calendar-view {
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

.controls {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--spacing-md);
  margin-bottom: var(--spacing-lg);
  flex-wrap: wrap;
}

.date-picker {
  .date-input {
    padding: var(--spacing-sm) var(--spacing-md);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    background: var(--color-bg-secondary);
    color: var(--color-text-primary);
    font-size: var(--font-size-md);
    cursor: pointer;
    
    &:focus {
      outline: none;
      border-color: var(--color-primary);
    }
  }
}

.filter-controls {
  display: flex;
  gap: var(--spacing-sm);
}

.filter-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: var(--spacing-sm) var(--spacing-md);
  background: var(--color-bg-secondary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-full);
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
  cursor: pointer;
  transition: all var(--transition-fast);

  &:hover {
    background: var(--color-bg-tertiary);
  }

  &.active {
    background: var(--color-primary);
    border-color: var(--color-primary);
    color: white;
  }

  .filter-icon {
    font-size: 14px;
  }
}

// Time Group
.time-group {
  margin-bottom: var(--spacing-lg);
  animation: slideInUp 0.5s ease-out both;
}

@keyframes slideInUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.time-header {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-sm) 0;
  margin-bottom: var(--spacing-sm);
  border-bottom: 1px solid var(--color-divider);
}

.time-label {
  font-size: var(--font-size-md);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
  font-family: var(--font-mono);
}

.event-count {
  font-size: var(--font-size-sm);
  color: var(--color-text-tertiary);
}

.events-list {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
}

// Event Card
.event-card {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: var(--spacing-md);
  padding: var(--spacing-md);
  background: var(--color-bg-secondary);
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border);
  transition: all var(--transition-fast);
  animation: fadeInScale 0.4s ease-out both;

  &:hover {
    background: var(--color-bg-tertiary);
  }

  &.important {
    border-left: 3px solid var(--color-primary);
  }
}

@keyframes fadeInScale {
  from {
    opacity: 0;
    transform: scale(0.95);
  }
  to {
    opacity: 1;
    transform: scale(1);
  }
}

// 减少动画偏好支持
@media (prefers-reduced-motion: reduce) {
  .time-group,
  .event-card {
    animation: none;
  }
}

.event-main {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
  min-width: 0;
}

.event-region {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
}

.region-badge {
  display: inline-flex;
  padding: 2px 8px;
  background: var(--color-bg-tertiary);
  border-radius: var(--radius-sm);
  font-size: var(--font-size-xs);
  color: var(--color-text-secondary);
}

.importance-badge {
  display: inline-flex;
  padding: 2px 6px;
  background: rgba(255, 193, 7, 0.15);
  border-radius: var(--radius-sm);
  font-size: var(--font-size-xs);
  color: #ffc107;
  font-weight: var(--font-weight-medium);
}

.event-name {
  font-size: var(--font-size-sm);
  color: var(--color-text-primary);
  line-height: 1.5;
  word-break: break-word;
}

.event-values {
  display: flex;
  gap: var(--spacing-lg);
  flex-shrink: 0;
}

.value-item {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 2px;
}

.value-label {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
}

.value-number {
  font-size: var(--font-size-sm);
  font-family: var(--font-mono);
  font-weight: var(--font-weight-medium);
  color: var(--color-text-primary);

  &.pending {
    color: var(--color-text-tertiary);
  }

  &.better {
    color: var(--color-rise);
  }

  &.worse {
    color: var(--color-fall);
  }
}

.event-comparison {
  grid-column: 1 / -1;
  display: flex;
  justify-content: flex-end;
}

.comparison-tag {
  display: inline-flex;
  padding: 4px 10px;
  border-radius: var(--radius-sm);
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-medium);

  &.positive {
    background: rgba(52, 199, 89, 0.15);
    color: var(--color-rise);
  }

  &.negative {
    background: rgba(255, 59, 48, 0.15);
    color: var(--color-fall);
  }

  &.neutral {
    background: var(--color-bg-tertiary);
    color: var(--color-text-secondary);
  }
}

// Summary Stats
.stats-summary {
  display: flex;
  justify-content: space-around;
  padding: var(--spacing-lg);
  margin-top: var(--spacing-xl);
  background: var(--color-bg-secondary);
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border);
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--spacing-xs);
}

.stat-value {
  font-size: var(--font-size-xl);
  font-weight: var(--font-weight-bold);
  color: var(--color-text-primary);
}

.stat-label {
  font-size: var(--font-size-sm);
  color: var(--color-text-tertiary);
}

// States
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

.loading-list {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
  width: 100%;
}

.event-skeleton {
  display: grid;
  grid-template-columns: 60px 80px 1fr 150px;
  gap: var(--spacing-md);
  padding: var(--spacing-md);
  background: var(--color-bg-secondary);
  border-radius: var(--radius-md);

  .skeleton-time,
  .skeleton-region,
  .skeleton-event,
  .skeleton-values {
    height: 16px;
    background: var(--color-skeleton);
    border-radius: var(--radius-sm);
    animation: pulse 1.5s ease-in-out infinite;
  }

  .skeleton-event {
    width: 80%;
  }
}

@keyframes pulse {
  0%, 100% { opacity: 0.4; }
  50% { opacity: 0.7; }
}

// Responsive
@media (max-width: 640px) {
  .event-card {
    grid-template-columns: 1fr;
  }

  .event-values {
    justify-content: flex-start;
  }

  .value-item {
    align-items: flex-start;
  }

  .stats-summary {
    flex-wrap: wrap;
    gap: var(--spacing-md);
  }

  .stat-item {
    flex: 1 1 45%;
  }
}
</style>
