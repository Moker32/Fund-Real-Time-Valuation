<template>
  <div
    class="fund-card"
    :class="{ loading: loading, 'has-chart': shouldShowChart }"
    @click="handleCardClick"
  >
    <template v-if="loading">
      <div class="skeleton-content">
        <div class="skeleton skeleton-title"></div>
        <div class="skeleton skeleton-value"></div>
        <div class="skeleton skeleton-change"></div>
      </div>
    </template>

    <template v-else>
      <div class="card-header">
        <div class="header-row">
          <span class="fund-code">{{ fund.code }}</span>
          <div class="card-actions">
            <button
              class="action-btn delete-btn"
              title="从自选移除"
              aria-label="从自选移除"
              @click.stop="$emit('remove', fund.code)"
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                <path d="M3 6h18M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/>
              </svg>
            </button>
            <button
              class="action-btn holding-btn"
              :class="{ active: fund.isHolding }"
              :title="fund.isHolding ? '取消持有' : '标记持有'"
              :aria-label="fund.isHolding ? '取消持有' : '标记为持有'"
              @click.stop="toggleHolding"
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                <path v-if="fund.isHolding" d="M5 12l5 5L19 7" stroke-linecap="round" stroke-linejoin="round"/>
                <path v-else d="M12 5v14M5 12h14" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
            </button>
            <span
              class="fund-type"
              :class="{ 'fund-type--qdii': fund.type?.startsWith('QDII') }"
            >
              {{ fund.type || '其他' }}
            </span>
          </div>
        </div>
        <div class="fund-name-row">
          <span class="fund-name" :title="fund.name">{{ fund.name }}</span>
        </div>
      </div>

      <div class="card-body">
        <!-- 左侧：净值+估值 | 右侧：涨跌幅 | 下方：折线图 -->
        <div class="info-section" :class="{ 'has-chart': shouldShowChart }">
          <div class="value-section">
            <div class="value-row">
              <span class="label">净值</span>
              <span class="value font-mono">{{ formatNumber(fund.netValue, 4) }}</span>
              <span class="value-date">{{ fund.netValueDate ? formatNetValueDate(fund.netValueDate) : '--' }}</span>
            </div>
            <!-- 非 QDII 基金显示估值 -->
            <div v-if="fund.hasRealTimeEstimate !== false" class="value-row">
              <span class="label">估值</span>
              <span class="value font-mono" :class="{ 'value-updated': valueAnimating }">{{ formatNumber(fund.estimateValue, 4) }}</span>
              <span class="value-date">{{ fund.estimateTime ? formatNetValueDate(fund.estimateTime) : '--' }}</span>
            </div>
            <!-- QDII 基金显示前日净值 -->
            <div v-else-if="fund.prevNetValue" class="value-row qdii-prev-row">
              <span class="label">前日</span>
              <span class="value font-mono">{{ formatNumber(fund.prevNetValue, 4) }}</span>
              <span class="value-date">{{ formatNetValueDate(fund.prevNetValueDate) }}</span>
            </div>
          </div>

          <div class="change-section" :class="[changeClass, { 'value-updated': changeAnimating }]">
            <div class="change-info">
              <span class="change-percent font-mono">{{ formatPercent(fund.estimateChangePercent) }}</span>
              <span class="change-indicator-value">
                <svg v-if="fund.estimateChangePercent > 0" viewBox="0 0 24 24" fill="none">
                  <path d="M12 19V5M5 12L12 5L19 12" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
                </svg>
                <svg v-else-if="fund.estimateChangePercent < 0" viewBox="0 0 24 24" fill="none">
                  <path d="M12 5V19M19 12L12 19L5 12" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
                </svg>
                <span v-else>—</span>
              </span>
              <span class="change-value font-mono">{{ formatChange(fund.estimateChange) }}</span>
            </div>
          </div>
        </div>

        <!-- 折线图：显示在估值下方 -->
        <LineChart v-if="shouldShowChart" :data="chartData" :height="60" :baseline="baseline" :trend="changeClass" :show-axes="false" :show-tooltip="false" class="fund-chart" />
      </div>

      <div class="card-footer">
        <span v-if="fund.hasRealTimeEstimate !== false" class="update-time">
          更新: {{ formatTime(fund.estimateTime) }}
        </span>
        <span class="source" v-if="fund.source">{{ fund.source }}</span>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch, onUnmounted } from 'vue';
import { useFundStore } from '@/stores/fundStore';
import type { Fund } from '@/types';
import LineChart from './LineChart.vue';

interface Props {
  fund: Fund;
  loading?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  loading: false,
});

const fundStore = useFundStore();

const emit = defineEmits<{
  (e: 'remove', code: string): void;
  (e: 'show-history', fund: { code: string; name: string }): void;
}>();

function handleCardClick(event: Event) {
  // 检查点击目标是否是交互元素或其子元素
  const target = event.target as Element;
  const interactiveSelectors = ['button', '.action-btn', '.fund-type'];

  // 检查点击的是否是交互元素
  const isInteractive = interactiveSelectors.some(selector =>
    target.matches(selector) || target.closest(selector)
  );

  if (isInteractive) {
    return;
  }

  // 触发显示历史记录事件
  emit('show-history', { code: props.fund.code, name: props.fund.name });
}

// 图表数据：优先使用日内分时数据，如果没有则使用历史数据
const chartData = computed(() => {
  if (props.fund.intraday && props.fund.intraday.length > 0) {
    return props.fund.intraday;
  }
  if (props.fund.history && props.fund.history.length > 0) {
    return props.fund.history;
  }
  return [];
});

// 是否显示图表
const shouldShowChart = computed(() => {
  return fundStore.showChart && chartData.value.length > 0;
});

// 涨跌样式
const changeClass = computed(() => {
  if (props.fund.estimateChangePercent > 0) return 'rising';
  if (props.fund.estimateChangePercent < 0) return 'falling';
  return 'neutral';
});

// 基准线 - 使用最新净值（与涨跌幅计算基准一致）
// fund123.cn 的涨跌幅是基于最新净值计算的，所以基准线也应该使用最新净值
const baseline = computed(() => {
  // 优先使用最新净值作为基准线（与API涨跌幅计算基准一致）
  if (props.fund.netValue && props.fund.netValue > 0) {
    return props.fund.netValue;
  }
  // 回退到前日净值（兼容旧数据）
  if (props.fund.prevNetValue && props.fund.prevNetValue > 0) {
    return props.fund.prevNetValue;
  }
  return undefined;
});

// 价格动画状态
const valueAnimating = ref(false);
const changeAnimating = ref(false);

// Track timeout IDs for cleanup
let valueAnimationTimeout: ReturnType<typeof setTimeout> | null = null;
let changeAnimationTimeout: ReturnType<typeof setTimeout> | null = null;

// 监听价格变化触发动画
watch(() => props.fund.estimateValue, (newVal, oldVal) => {
  if (oldVal !== undefined && newVal !== undefined && newVal !== oldVal) {
    triggerValueAnimation();
  }
});

watch(() => props.fund.estimateChangePercent, (newVal, oldVal) => {
  if (oldVal !== undefined && newVal !== undefined && newVal !== oldVal) {
    triggerChangeAnimation();
  }
});

function triggerValueAnimation() {
  // Clear existing timeout to prevent memory leak
  if (valueAnimationTimeout) {
    window.clearTimeout(valueAnimationTimeout);
  }
  valueAnimating.value = true;
  valueAnimationTimeout = window.setTimeout(() => {
    valueAnimating.value = false;
    valueAnimationTimeout = null;
  }, 500);
}

function triggerChangeAnimation() {
  // Clear existing timeout to prevent memory leak
  if (changeAnimationTimeout) {
    window.clearTimeout(changeAnimationTimeout);
  }
  changeAnimating.value = true;
  changeAnimationTimeout = window.setTimeout(() => {
    changeAnimating.value = false;
    changeAnimationTimeout = null;
  }, 500);
}

// Cleanup timeouts on unmount to prevent memory leaks
onUnmounted(() => {
  if (valueAnimationTimeout) {
    window.clearTimeout(valueAnimationTimeout);
  }
  if (changeAnimationTimeout) {
    window.clearTimeout(changeAnimationTimeout);
  }
});

async function toggleHolding() {
  await fundStore.toggleHolding(props.fund.code, !props.fund.isHolding);
}

function formatNumber(value: number, decimals: number = 2): string {
  if (value == null) return '--';
  return value.toFixed(decimals);
}

function formatChange(value: number): string {
  if (value == null) return '--';
  const sign = value >= 0 ? '+' : '';
  return `${sign}${value.toFixed(4)}`;
}

function formatPercent(value: number): string {
  if (value == null) return '--';
  const sign = value >= 0 ? '+' : '';
  return `${sign}${value.toFixed(2)}%`;
}

function formatTime(dateStr: string | undefined): string {
  if (!dateStr) return '--';
  try {
    const date = new Date(dateStr);
    // 如果没有时间部分（00:00），只显示日期
    const hours = parseInt(date.toLocaleTimeString('zh-CN', { timeZone: 'Asia/Shanghai', hour12: false, hour: '2-digit' }), 10);
    const minutes = parseInt(date.toLocaleTimeString('zh-CN', { timeZone: 'Asia/Shanghai', minute: '2-digit' }), 10);
    if (hours === 0 && minutes === 0) {
      return date.toLocaleDateString('zh-CN', { timeZone: 'Asia/Shanghai' });
    }
    return date.toLocaleString('zh-CN', {
      timeZone: 'Asia/Shanghai',
      month: 'numeric',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      hour12: false,
    });
  } catch {
    return dateStr;
  }
}

function formatNetValueDate(dateStr: string | undefined): string {
  if (!dateStr) return '';
  try {
    const date = new Date(dateStr);
    return `${(date.getMonth() + 1).toString().padStart(2, '0')}/${date.getDate().toString().padStart(2, '0')}`;
  } catch {
    return '';
  }
}
</script>

<style lang="scss" scoped>
.fund-card {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: var(--spacing-lg);
  transition: transform var(--transition-normal), box-shadow var(--transition-normal);
  will-change: transform;
  cursor: pointer;
  overflow: hidden;
  width: 100%;
  min-width: 0;
  max-width: 100%;
  flex: 1 1 auto;

  &.has-chart {
    width: 100%;
    min-width: 0;
    flex: 1 1 auto;
  }

  &:hover {
    background: var(--color-bg-card-hover);
    border-color: var(--color-border-light);
    transform: translateY(-2px);
    box-shadow: var(--shadow-md);
  }

  &.loading {
    cursor: default;
    pointer-events: none;
  }
}

.skeleton-content {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
}

.skeleton {
  height: 16px;
  border-radius: var(--radius-sm);

  &.skeleton-title {
    width: 60%;
    height: 18px;
  }

  &.skeleton-value {
    width: 80%;
  }

  &.skeleton-change {
    width: 40%;
  }
}

.card-header {
  display: flex;
  flex-direction: column;
  margin-bottom: var(--spacing-md);
  gap: var(--spacing-xs);
}

.header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-height: 28px;
  gap: var(--spacing-xs);
}

.card-actions {
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
  flex-shrink: 0;
}

.fund-code {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
  font-family: var(--font-mono);
  flex-shrink: 0;
}

.fund-name-row {
  display: flex;
  align-items: center;
  min-width: 0;
  width: 100%;
  overflow: hidden;
}

.fund-name {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
  line-height: 1.3;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  width: 100%;
}

.fund-type {
  font-size: var(--font-size-xs);
  padding: 2px 8px;
  background: var(--color-bg-tertiary);
  border-radius: var(--radius-full);
  color: var(--color-text-secondary);
  flex-shrink: 0;

  &--qdii {
    background: rgba(139, 92, 246, 0.15);
    color: #8b5cf6;
  }
}

.action-btn {
  width: 32px;
  height: 32px;
  min-width: 32px;
  min-height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: none;
  border-radius: var(--radius-md);
  color: var(--color-text-tertiary);
  cursor: pointer;
  transition: all var(--transition-fast);
  opacity: 0;

  svg {
    width: 16px;
    height: 16px;
  }

  &:hover {
    background: var(--color-bg-tertiary);
    color: var(--color-fall);
  }
}

.delete-btn:hover {
  background: var(--color-fall-alpha);
  color: var(--color-fall);
}

.holding-btn {
  svg {
    stroke-width: 2.5;
  }

  &:hover {
    background: var(--color-rise-alpha);
    color: var(--color-rise);
  }

  &.active {
    opacity: 1;
    color: var(--color-rise);

    &:hover {
      background: var(--color-rise-alpha);
    }
  }
}

.fund-card:hover .action-btn {
  opacity: 1;
}

.card-body {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
  margin-bottom: var(--spacing-md);
  min-width: 0;
  width: 100%;
}

.info-section {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  min-width: 0;
  gap: var(--spacing-md);
}

.value-section {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
  min-width: 0;
  flex: 1 1 auto;
  /* 移除 max-width，让 flex 布局自然分配空间 */
  overflow: hidden;
}

.fund-chart {
  width: 100%;
  min-height: 60px;
  flex-shrink: 0;
}

.value-row {
  display: flex;
  align-items: center;
  gap: 4px;
  min-width: 0;
  width: 100%;

  .label {
    flex-shrink: 0;
    min-width: 28px;
  }

  .value {
    flex: 0 1 auto;
    min-width: 45px;
    text-align: right;
    /* 允许数值收缩但保持可读性 */
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .value-date {
    flex-shrink: 0;
    min-width: 36px;
    text-align: right;
    margin-left: auto; /* 将日期推到右侧 */
  }

  &.qdii-prev-row {
    opacity: 0.7;
  }
}

.value-date {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
  font-family: var(--font-mono);
  white-space: nowrap;
}

.label {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
}

.value {
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-medium);
  color: var(--color-text-primary);
  transition: all 0.3s ease;

  &.value-updated {
    animation: value-pulse 0.5s ease-out;
  }
}

@keyframes value-pulse {
  0% {
    transform: scale(1);
    color: var(--color-text-primary);
    background: transparent;
  }
  25% {
    background: var(--color-rise-bg);
  }
  50% {
    transform: scale(1.1);
    color: var(--color-rise);
  }
  75% {
    background: var(--color-rise-bg);
  }
  100% {
    transform: scale(1);
    color: var(--color-text-primary);
    background: transparent;
  }
}

.change-section {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--spacing-xs) var(--spacing-sm);
  border-radius: var(--radius-md);
  transition: all var(--transition-fast);
  /* 固定宽度，防止压缩 */
  width: 90px;
  min-width: 90px;
  max-width: 90px;
  flex: 0 0 auto;
  box-sizing: border-box;

  .change-info {
    display: flex;
    flex-direction: column;
    align-items: center;
    width: 100%;
    flex-shrink: 0;
    gap: 2px;
    justify-content: center;
  }

  .change-percent,
  .change-value {
    white-space: nowrap;
  }

  &.rising {
    background: var(--color-rise-bg);
    color: var(--color-rise);

    .change-indicator-value svg {
      color: var(--color-rise);
    }
  }

  &.falling {
    background: var(--color-fall-bg);
    color: var(--color-fall);

    .change-indicator-value svg {
      color: var(--color-fall);
    }
  }

  &.neutral {
    color: var(--color-neutral);
  }

  &.value-updated {
    animation: change-pulse 0.5s ease-out;
  }
}

@keyframes change-pulse {
  0% {
    transform: scale(1);
  }
  50% {
    transform: scale(1.15);
  }
  100% {
    transform: scale(1);
  }
}

.change-value {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
}

.change-percent {
  font-size: var(--font-size-xl);
  font-weight: var(--font-weight-bold);
  line-height: 1;
}

.change-indicator-value {
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 2px 0;

  svg {
    width: 14px;
    height: 14px;
  }
}

.card-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-top: var(--spacing-sm);
  border-top: 1px solid var(--color-divider);
  gap: var(--spacing-xs);
}

.update-time,
.source {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

// ==================== 响应式布局优化 ====================

// 平板及以下 (< 1024px)
@media (max-width: 1024px) {
  .fund-card {
    padding: var(--spacing-md);
  }

  .change-section {
    width: 85px;
    min-width: 85px;
    max-width: 85px;
    padding: var(--spacing-xs);
  }

  .change-percent {
    font-size: var(--font-size-lg);
  }
}

// 手机横屏/大手机 (< 768px)
@media (max-width: 768px) {
  .fund-card {
    padding: var(--spacing-md);
  }

  .card-header {
    margin-bottom: var(--spacing-sm);
  }

  .card-body {
    margin-bottom: var(--spacing-sm);
  }

  .info-section {
    align-items: center;
    gap: var(--spacing-sm);
  }

  .value-section {
    /* 移除 max-width，让 flex 布局自然分配 */
    overflow: hidden;
  }

  .value-row {
    gap: 6px;

    .value {
      font-size: var(--font-size-md);
      min-width: 40px;
    }

    .value-date {
      min-width: 32px;
    }
  }

  .change-section {
    width: 80px;
    min-width: 80px;
    max-width: 80px;
    padding: var(--spacing-xs) 6px;

    .change-info {
      gap: 1px;
    }
  }

  .change-percent {
    font-size: var(--font-size-md);
  }

  .change-value {
    font-size: var(--font-size-xs);
  }

  .change-indicator-value {
    margin: 1px 0;

    svg {
      width: 12px;
      height: 12px;
    }
  }

  .card-footer {
    flex-wrap: wrap;
    gap: var(--spacing-xs);
  }
}

// 标准小屏手机 (< 640px)
@media (max-width: 640px) {
  .fund-card {
    padding: var(--spacing-sm);
    min-width: 0;
    width: 100%;

    &.has-chart {
      min-width: 0;
      width: 100%;
    }
  }

  // 移动端始终显示操作按钮（触摸设备无法 hover）
  .action-btn {
    opacity: 1;
    width: 36px;
    height: 36px;
    min-width: 36px;
    min-height: 36px;

    svg {
      width: 18px;
      height: 18px;
    }
  }

  .header-row {
    min-height: 36px;
  }

  .fund-name {
    font-size: var(--font-size-sm);
  }

  .info-section {
    gap: var(--spacing-xs);
  }

  .value-section {
    /* 移除 max-width，让 flex 布局自然分配 */
    overflow: hidden;
  }

  .value-row {
    gap: 4px;

    .label {
      min-width: 26px;
    }

    .value {
      font-size: var(--font-size-md);
      min-width: 38px;
    }

    .value-date {
      min-width: 30px;
      font-size: 10px;
    }
  }

  .change-section {
    width: 72px;
    min-width: 72px;
    max-width: 72px;
    padding: 4px 6px;
  }

  .change-percent {
    font-size: var(--font-size-md);
  }

  .change-value {
    font-size: 10px;
  }

  .card-footer {
    padding-top: var(--spacing-xs);
  }

  .update-time,
  .source {
    font-size: 10px;
  }
}

// 超小屏手机 (< 480px)
@media (max-width: 480px) {
  .fund-card {
    padding: var(--spacing-sm);
  }

  .card-header {
    margin-bottom: var(--spacing-xs);
    gap: 2px;
  }

  .header-row {
    min-height: 32px;
  }

  .fund-name {
    font-size: var(--font-size-xs);
    line-height: 1.2;
  }

  .fund-code {
    font-size: 10px;
  }

  .fund-type {
    font-size: 10px;
    padding: 1px 6px;
  }

  .action-btn {
    width: 32px;
    height: 32px;
    min-width: 32px;
    min-height: 32px;

    svg {
      width: 16px;
      height: 16px;
    }
  }

  .card-body {
    margin-bottom: var(--spacing-xs);
    gap: var(--spacing-xs);
  }

  .info-section {
    gap: 6px;
  }

  .value-section {
    gap: 2px;
    /* 移除 max-width，让 flex 布局自然分配 */
    overflow: hidden;
  }

  .value-row {
    gap: 4px;

    .label {
      min-width: 24px;
      font-size: 10px;
    }

    .value {
      font-size: var(--font-size-sm);
      min-width: 35px;
    }

    .value-date {
      min-width: 28px;
      font-size: 9px;
    }
  }

  .change-section {
    width: 64px;
    min-width: 64px;
    max-width: 64px;
    padding: 3px 5px;

    .change-info {
      gap: 0;
    }
  }

  .change-percent {
    font-size: var(--font-size-sm);
  }

  .change-value {
    font-size: 9px;
  }

  .change-indicator-value {
    margin: 0;

    svg {
      width: 10px;
      height: 10px;
    }
  }

  .card-footer {
    padding-top: var(--spacing-xs);
    gap: 4px;
  }

  .update-time,
  .source {
    font-size: 9px;
  }

  .fund-chart {
    min-height: 50px;
  }
}

// 极小屏 (< 360px)
@media (max-width: 360px) {
  .fund-card {
    padding: 8px;
  }

  .fund-name {
    font-size: 10px;
  }

  .value-section {
    /* 移除 max-width，让 flex 布局自然分配 */
    overflow: hidden;
  }

  .value-row {
    .value {
      font-size: var(--font-size-xs);
      min-width: 32px;
    }

    .value-date {
      min-width: 26px;
      font-size: 9px;
    }
  }

  .change-section {
    width: 58px;
    min-width: 58px;
    max-width: 58px;
    padding: 2px 4px;
  }

  .change-percent {
    font-size: var(--font-size-xs);
  }
}

// 减少动画偏好支持
@media (prefers-reduced-motion: reduce) {
  .fund-card {
    transition: none;

    &:hover {
      transform: none;
    }
  }

  .value-updated {
    animation: none !important;
  }

  .change-section.value-updated {
    animation: none !important;
  }
}

// 触摸设备优化：始终显示操作按钮
@media (hover: none) and (pointer: coarse) {
  .action-btn {
    opacity: 1;
  }
}
</style>
