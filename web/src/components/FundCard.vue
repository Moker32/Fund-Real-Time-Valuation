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
        <!-- 涨跌幅视觉焦点（左侧大色块） | 净值+估值（右侧辅助信息） -->
        <div class="info-section">
          <div class="change-block" :class="[changeClass, { 'value-updated': changeAnimating }]">
            <div class="change-main">
              <span class="change-percent font-mono">{{ displayChangePercent }}</span>
              <span class="change-value font-mono">{{ displayChangeValueStr }}</span>
            </div>
          </div>

          <div class="value-section">
            <div class="value-row">
              <span class="label">净值</span>
              <span class="value font-mono">{{ formatNumber(fund.netValue, 4) }}</span>
              <span class="value-date">{{ fund.netValueDate ? formatNetValueDate(fund.netValueDate) : '--' }}</span>
            </div>
            <div v-if="fund.hasRealTimeEstimate !== false" class="value-row">
              <span class="label">估值</span>
              <span class="value font-mono" :class="{ 'value-updated': valueAnimating }">{{ formatNumber(fund.estimateValue, 4) }}</span>
              <span class="value-date">{{ fund.estimateTime ? formatNetValueDate(fund.estimateTime) : '--' }}</span>
            </div>
            <div v-else-if="fund.qdiiEstimateChangePercent != null" class="value-row qdii-estimate-row">
              <span class="label">估算</span>
              <span class="value font-mono" :class="{ 'value-updated': valueAnimating }">{{ formatNumber(fund.estimateValue, 4) }}</span>
              <span class="value-date">{{ fund.estimateTime ? formatNetValueDate(fund.estimateTime) : '--' }}</span>
            </div>
            <div v-else-if="fund.prevNetValue" class="value-row qdii-prev-row">
              <span class="label">前日</span>
              <span class="value font-mono">{{ formatNumber(fund.prevNetValue, 4) }}</span>
              <span class="value-date">{{ formatNetValueDate(fund.prevNetValueDate) }}</span>
            </div>

            <!-- 区间收益率标签 -->
            <div v-if="fund.intervalReturns" class="interval-returns">
              <span
                v-for="[label, pct] in Object.entries(fund.intervalReturns || {})"
                :key="label"
                class="return-tag"
                :class="pct >= 0 ? 'return-up' : 'return-down'"
              >
                {{ intervalLabel(label) }} {{ pct >= 0 ? '+' : '' }}{{ pct }}%
              </span>
            </div>
          </div>
        </div>

        <LineChart v-if="shouldShowChart" :data="chartData" :height="60" :baseline="baseline" :trend="changeClass" :show-axes="false" :show-tooltip="false" :streaming="!!fund.intraday?.length" :max-points="500" class="fund-chart" />
      </div>

      <div class="card-footer">
        <div class="footer-left">
          <span v-if="fund.hasRealTimeEstimate !== false" class="update-time">
            更新: {{ formatTime(fund.estimateTime) }}
          </span>
          <span v-else-if="fund.qdiiEstimateChangePercent != null" class="update-time qdii-footer">
            <span class="market-status-dot" :class="marketStatusClass"></span>
            <span>{{ marketStatusLabel }}</span>
            <span class="footer-sep">·</span>
            <span>{{ formatTime(fund.estimateTime) }}</span>
          </span>
        </div>
        <div class="footer-right">
          <template v-if="fund.conceptTags?.length">
            <span v-for="tag in fund.conceptTags.slice(0, 3)" :key="tag" class="fund-concept-tag">{{ tag }}</span>
          </template>
          <span v-if="fund.peerRank" class="peer-rank" :title="`同类排名: ${fund.peerRank.rank}/${fund.peerRank.total}`">
            {{ fund.peerRank.category }} {{ fund.peerRank.rank }}/{{ fund.peerRank.total }}
          </span>
          <span v-if="fund.underlyingIndices && fund.underlyingIndices.length > 0" class="underlying-indices">
            {{ fund.underlyingIndices.map(idx => idx.name).join(' / ') }}
          </span>
        </div>
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
  const target = event.target as Element;
  const interactiveSelectors = ['button', '.action-btn', '.fund-type', '.fund-concept-tag'];
  const isInteractive = interactiveSelectors.some(selector =>
    target.matches(selector) || target.closest(selector)
  );
  if (isInteractive) return;
  emit('show-history', { code: props.fund.code, name: props.fund.name });
}

const chartData = computed(() => {
  if (props.fund.intraday && props.fund.intraday.length > 0) return props.fund.intraday;
  if (props.fund.history && props.fund.history.length > 0) return props.fund.history;
  return [];
});

const shouldShowChart = computed(() => fundStore.showChart && chartData.value.length > 0);

const changeClass = computed(() => {
  if (props.fund.estimateChangePercent > 0) return 'rising';
  if (props.fund.estimateChangePercent < 0) return 'falling';
  return 'neutral';
});

const baseline = computed(() => {
  // QDII funds use qdiiEstimateChangePercent which is based on prevNetValue
  // Normal funds use estimateChangePercent which is based on netValue
  if (props.fund.qdiiEstimateChangePercent != null) {
    if (props.fund.prevNetValue && props.fund.prevNetValue > 0) return props.fund.prevNetValue;
  }
  // Use netValue (yesterday's close / today's baseline) as baseline
  // This aligns with estimateChangePercent which is calculated from netValue
  if (props.fund.netValue && props.fund.netValue > 0) return props.fund.netValue;
  if (props.fund.prevNetValue && props.fund.prevNetValue > 0) return props.fund.prevNetValue;
  return undefined;
});

const displayChangePercent = computed(() => {
  if (props.fund.qdiiEstimateChangePercent != null) return formatPercent(props.fund.qdiiEstimateChangePercent);
  return formatPercent(props.fund.estimateChangePercent);
});

const displayChangeValue = computed(() => {
  if (props.fund.qdiiEstimateChangePercent != null && props.fund.prevNetValue) {
    return props.fund.prevNetValue * props.fund.qdiiEstimateChangePercent / 100;
  }
  return props.fund.estimateChange ?? 0;
});

const displayChangeValueStr = computed(() => formatChange(displayChangeValue.value));

const marketStatusClass = computed(() => {
  const s = props.fund.marketStatus;
  if (s === 'open') return 'dot-open';
  if (s === 'pre_market' || s === 'pre') return 'dot-pre';
  return 'dot-closed';
});

const marketStatusLabel = computed(() => {
  const s = props.fund.marketStatus;
  if (s === 'open') return '交易中';
  if (s === 'pre_market' || s === 'pre') return '盘前';
  if (s === 'after_hours') return '盘后';
  return '已收盘';
});

const valueAnimating = ref(false);
const changeAnimating = ref(false);
let valueAnimationTimeout: ReturnType<typeof setTimeout> | null = null;
let changeAnimationTimeout: ReturnType<typeof setTimeout> | null = null;

watch(() => props.fund.estimateValue, (newVal, oldVal) => {
  if (oldVal !== undefined && newVal !== undefined && newVal !== oldVal) triggerValueAnimation();
});

watch(() => props.fund.estimateChangePercent, (newVal, oldVal) => {
  if (oldVal !== undefined && newVal !== undefined && newVal !== oldVal) triggerChangeAnimation();
});

function triggerValueAnimation() {
  if (valueAnimationTimeout) window.clearTimeout(valueAnimationTimeout);
  valueAnimating.value = true;
  valueAnimationTimeout = window.setTimeout(() => { valueAnimating.value = false; valueAnimationTimeout = null; }, 500);
}

function triggerChangeAnimation() {
  if (changeAnimationTimeout) window.clearTimeout(changeAnimationTimeout);
  changeAnimating.value = true;
  changeAnimationTimeout = window.setTimeout(() => { changeAnimating.value = false; changeAnimationTimeout = null; }, 500);
}

onUnmounted(() => {
  if (valueAnimationTimeout) window.clearTimeout(valueAnimationTimeout);
  if (changeAnimationTimeout) window.clearTimeout(changeAnimationTimeout);
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
    const hours = parseInt(date.toLocaleTimeString('zh-CN', { timeZone: 'Asia/Shanghai', hour12: false, hour: '2-digit' }), 10);
    const minutes = parseInt(date.toLocaleTimeString('zh-CN', { timeZone: 'Asia/Shanghai', minute: '2-digit' }), 10);
    if (hours === 0 && minutes === 0) return date.toLocaleDateString('zh-CN', { timeZone: 'Asia/Shanghai' });
    return date.toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai', month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit', hour12: false });
  } catch { return dateStr; }
}

function formatNetValueDate(dateStr: string | undefined): string {
  if (!dateStr) return '';
  try {
    const date = new Date(dateStr);
    return `${(date.getMonth() + 1).toString().padStart(2, '0')}/${date.getDate().toString().padStart(2, '0')}`;
  } catch { return ''; }
}

function intervalLabel(key: string): string {
  const map: Record<string, string> = { '1w': '近1周', '1m': '近1月', '3m': '近3月', '6m': '近6月', '1y': '近1年' };
  return map[key] || key;
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

  &.skeleton-title { width: 60%; height: 18px; }
  &.skeleton-value { width: 80%; }
  &.skeleton-change { width: 40%; }
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

.fund-concept-tag {
  font-size: 10px;
  padding: 1px 6px;
  border-radius: 3px;
  white-space: nowrap;
  flex-shrink: 0;
  background: rgba(139, 92, 246, 0.1);
  color: #8b5cf6;
}

.fund-concept-tag:nth-child(2n) {
  background: rgba(236, 72, 153, 0.1);
  color: #ec4899;
}

.fund-concept-tag:nth-child(3n) {
  background: rgba(234, 179, 8, 0.1);
  color: #ca8a04;
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

  svg { width: 16px; height: 16px; }

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
  svg { stroke-width: 2.5; }

  &:hover {
    background: var(--color-rise-alpha);
    color: var(--color-rise);
  }

  &.active {
    opacity: 1;
    color: var(--color-rise);

    &:hover { background: var(--color-rise-alpha); }
  }
}

.fund-card:hover .action-btn { opacity: 1; }

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
  align-items: stretch;
  min-width: 0;
  gap: var(--spacing-md);
}

// 涨跌幅视觉焦点 — 左侧大色块
.change-block {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-md);
  padding: var(--spacing-sm) var(--spacing-xs);
  transition: all var(--transition-fast);
  width: 110px;
  min-width: 110px;
  max-width: 110px;
  box-sizing: border-box;
  align-self: stretch;

  .change-main {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 2px;
    width: 100%;
  }

  .change-percent {
    font-size: 26px;
    font-weight: var(--font-weight-bold);
    line-height: 1.1;
    white-space: nowrap;
  }

  .change-value {
    font-size: var(--font-size-sm);
    font-weight: var(--font-weight-medium);
    white-space: nowrap;
  }

  &.rising {
    background: var(--color-rise-bg);
    color: var(--color-rise);
  }

  &.falling {
    background: var(--color-fall-bg);
    color: var(--color-fall);
  }

  &.neutral { color: var(--color-neutral); }

  &.value-updated { animation: change-pulse 0.5s ease-out; }
}

@keyframes change-pulse {
  0% { transform: scale(1); }
  50% { transform: scale(1.05); }
  100% { transform: scale(1); }
}

.value-section {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
  min-width: 0;
  flex: 1 1 auto;
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
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .value-date {
    flex-shrink: 0;
    min-width: 36px;
    text-align: right;
    margin-left: auto;
  }

  &.qdii-prev-row { opacity: 0.7; }

  &.qdii-estimate-row {
    .label {
      display: flex;
      align-items: center;
      gap: 4px;
    }
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
  font-size: var(--font-size-md);
  font-weight: var(--font-weight-medium);
  color: var(--color-text-primary);
  transition: all 0.3s ease;

  &.value-updated { animation: value-pulse 0.5s ease-out; }
}

@keyframes value-pulse {
  0% { transform: scale(1); color: var(--color-text-primary); background: transparent; }
  25% { background: var(--color-rise-bg); }
  50% { transform: scale(1.1); color: var(--color-rise); }
  75% { background: var(--color-rise-bg); }
  100% { transform: scale(1); color: var(--color-text-primary); background: transparent; }
}

// 区间收益率标签
.interval-returns {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-top: 2px;
}

.return-tag {
  font-size: 10px;
  padding: 1px 6px;
  border-radius: 3px;
  font-weight: var(--font-weight-medium);
  font-family: var(--font-mono);
  white-space: nowrap;

  &.return-up {
    background: rgba(34, 197, 94, 0.1);
    color: #22c55e;
  }

  &.return-down {
    background: rgba(239, 68, 68, 0.1);
    color: #ef4444;
  }
}

.market-status-dot {
  display: inline-block;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  flex-shrink: 0;

  &.dot-open { background: #22c55e; }
  &.dot-pre { background: #ca8a04; }
  &.dot-closed { background: #6b7280; }
}

.qdii-footer {
  display: flex;
  align-items: center;
  gap: 4px;
}

.footer-sep {
  color: var(--color-text-tertiary);
  opacity: 0.5;
}

.card-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-top: var(--spacing-sm);
  border-top: 1px solid var(--color-divider);
  gap: var(--spacing-xs);
  min-width: 0;
}

.footer-left, .footer-right {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
}

.footer-left { flex-shrink: 0; }
.footer-right {
  justify-content: flex-end;
  flex-shrink: 1;
  min-width: 0;
}

.update-time, .peer-rank, .underlying-indices {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.peer-rank {
  font-family: var(--font-mono);
}

.underlying-indices {
  font-size: 10px;
}

// ==================== 响应式布局优化 ====================

@media (max-width: 1024px) {
  .fund-card { padding: var(--spacing-md); }

  .change-block {
    width: 100px;
    min-width: 100px;
    max-width: 100px;
    padding: var(--spacing-xs) 8px;

    .change-percent { font-size: 24px; }
  }
}

@media (max-width: 768px) {
  .fund-card { padding: var(--spacing-md); }

  .card-header { margin-bottom: var(--spacing-sm); }
  .card-body { margin-bottom: var(--spacing-sm); }

  .info-section { gap: var(--spacing-sm); }

  .change-block {
    width: 90px;
    min-width: 90px;
    max-width: 90px;
    padding: var(--spacing-xs) 6px;

    .change-percent { font-size: 22px; }
    .change-value { font-size: var(--font-size-xs); }
  }

  .value-row {
    gap: 6px;
    .value { font-size: var(--font-size-md); min-width: 40px; }
    .value-date { min-width: 32px; }
  }

  .card-footer { flex-wrap: wrap; gap: var(--spacing-xs); }
}

@media (max-width: 640px) {
  .fund-card {
    padding: var(--spacing-sm);
    min-width: 0;
    width: 100%;

    &.has-chart { min-width: 0; width: 100%; }
  }

  .action-btn {
    opacity: 1;
    width: 36px; height: 36px;
    min-width: 36px; min-height: 36px;
    svg { width: 18px; height: 18px; }
  }

  .header-row { min-height: 36px; }
  .fund-name { font-size: var(--font-size-sm); }
  .info-section { gap: var(--spacing-xs); }

  .change-block {
    width: 80px;
    min-width: 80px;
    max-width: 80px;
    padding: 6px 4px;

    .change-percent { font-size: 20px; }
    .change-value { font-size: 10px; }
  }

  .value-row {
    gap: 4px;
    .label { min-width: 26px; }
    .value { font-size: var(--font-size-md); min-width: 38px; }
    .value-date { min-width: 30px; font-size: 10px; }
  }

  .card-footer { padding-top: var(--spacing-xs); }
  .update-time, .source, .peer-rank { font-size: 10px; }
}

@media (max-width: 480px) {
  .fund-card { padding: var(--spacing-sm); }

  .card-header { margin-bottom: var(--spacing-xs); gap: 2px; }
  .header-row { min-height: 32px; }
  .fund-name { font-size: var(--font-size-xs); line-height: 1.2; }
  .fund-code { font-size: 10px; }
  .fund-type { font-size: 10px; padding: 1px 6px; }
  .fund-concept-tag { font-size: 10px; padding: 1px 6px; }

  .action-btn {
    width: 32px; height: 32px;
    min-width: 32px; min-height: 32px;
    svg { width: 16px; height: 16px; }
  }

  .card-body { margin-bottom: var(--spacing-xs); gap: var(--spacing-xs); }
  .info-section { gap: 6px; }

  .change-block {
    width: 72px;
    min-width: 72px;
    max-width: 72px;
    padding: 4px 3px;

    .change-percent { font-size: 18px; }
    .change-value { font-size: 9px; }
  }

  .value-section { gap: 2px; overflow: hidden; }

  .value-row {
    gap: 4px;
    .label { min-width: 24px; font-size: 10px; }
    .value { font-size: var(--font-size-sm); min-width: 35px; }
    .value-date { min-width: 28px; font-size: 9px; }
  }

  .card-footer { padding-top: var(--spacing-xs); gap: 4px; }
  .update-time, .source, .peer-rank { font-size: 9px; }
  .fund-chart { min-height: 50px; }
}

@media (max-width: 360px) {
  .fund-card { padding: 8px; }
  .fund-name { font-size: 10px; }

  .change-block {
    width: 64px;
    min-width: 64px;
    max-width: 64px;
    padding: 3px 2px;

    .change-percent { font-size: 16px; }
    .change-value { font-size: 8px; }
  }

  .value-row {
    .value { font-size: var(--font-size-xs); min-width: 32px; }
    .value-date { min-width: 26px; font-size: 9px; }
  }
}

@media (prefers-reduced-motion: reduce) {
  .fund-card {
    transition: none;
    &:hover { transform: none; }
  }
  .value-updated { animation: none !important; }
  .change-block.value-updated { animation: none !important; }
}

@media (hover: none) and (pointer: coarse) {
  .action-btn { opacity: 1; }
}
</style>
