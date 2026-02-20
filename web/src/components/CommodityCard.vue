<template>
  <div class="commodity-card" :class="{ loading: loading }">
    <template v-if="loading">
      <div class="skeleton-content">
        <div class="skeleton skeleton-title"></div>
        <div class="skeleton skeleton-price"></div>
        <div class="skeleton skeleton-change"></div>
      </div>
    </template>

    <template v-else>
      <div class="card-header">
        <div class="commodity-info">
          <span class="commodity-symbol">{{ commodity.symbol }}</span>
          <span class="commodity-name">{{ commodity.name }}</span>
        </div>
        <div class="header-tags">
          <div class="trading-status" :class="`status-${tradingStatus}`">
            <span class="status-dot"></span>
            <span class="status-text">{{ statusText }}</span>
          </div>
          <button
            class="action-btn watch-btn"
            :class="{ active: isWatched }"
            :title="isWatched ? '取消关注' : '添加关注'"
            :aria-label="isWatched ? '取消关注' : '添加关注'"
            @click.stop="toggleWatch"
          >
            <svg v-if="isWatched" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
              <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/>
            </svg>
            <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
              <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/>
            </svg>
          </button>
        </div>
      </div>

      <div class="card-body">
        <div class="price-section">
          <span class="price font-mono" :class="{ 'value-updated': priceAnimating }">{{ formatPrice(commodity.price) }}</span>
          <span class="currency">{{ commodity.currency }}</span>
        </div>

        <div class="change-section" :class="[changeClass, { 'value-updated': changeAnimating }]">
          <span class="change-percent font-mono">{{ formatPercent(commodity.changePercent) }}</span>
          <span class="change-indicator-value">
            <svg v-if="commodity.changePercent > 0" viewBox="0 0 24 24" fill="none">
              <path d="M12 19V5M5 12L12 5L19 12" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
            </svg>
            <svg v-else-if="commodity.changePercent < 0" viewBox="0 0 24 24" fill="none">
              <path d="M12 5V19M19 12L12 19L5 12" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
            </svg>
            <span v-else>—</span>
          </span>
          <span class="change-value font-mono">{{ formatChange(commodity.change) }}</span>
        </div>
      </div>

      <div class="card-footer">
        <div class="price-range">
          <span class="range-item">
            <span class="label">高</span>
            <span class="value font-mono">{{ formatPrice(commodity.high) }}</span>
          </span>
          <span class="range-item">
            <span class="label">低</span>
            <span class="value font-mono">{{ formatPrice(commodity.low) }}</span>
          </span>
        </div>
        <div class="card-footer-row2">
          <span class="timestamp">{{ formatTime(commodity.timestamp) }}</span>
          <span class="commodity-source" v-if="sourceName">{{ sourceName }}</span>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch, onMounted } from 'vue';
import { useCommodityStore } from '@/stores/commodityStore';
import { getCommodityCategory, getCommodityMarket } from '@/utils/commodityNames';
import { tradingCalendarApi } from '@/api';
import type { Commodity } from '@/types';

interface Props {
  commodity: Commodity;
  loading?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  loading: false,
});

const store = useCommodityStore();

// 简化数据源名称显示
const sourceName = computed(() => {
  const source = props.commodity.source;
  if (!source) return '';
  if (source.includes('akshare')) return 'AKShare';
  if (source.includes('yfinance')) return 'yFinance';
  if (source.includes('binance')) return 'Binance';
  return source;
});

// 缓存各市场交易日结果
const tradingDayCache = ref<Record<string, boolean>>({});

// 获取对应市场的交易日状态
async function fetchTradingDayStatus(market: string) {
  if (tradingDayCache.value[market] !== undefined) {
    return;
  }
  try {
    const result = await tradingCalendarApi.isTradingDay(market);
    tradingDayCache.value[market] = result.is_trading_day;
  } catch (e) {
    console.warn(`获取 ${market} 交易日失败，使用本地判断`, e);
    tradingDayCache.value[market] = null;
  }
}

onMounted(() => {
  const market = getCommodityMarket(props.commodity.symbol);
  fetchTradingDayStatus(market);
});

// 检查该商品是否在关注列表中
const isWatched = computed(() => {
  return store.watchedCommodities.some(
    (item) => item.symbol.toUpperCase() === props.commodity.symbol.toUpperCase()
  );
});

const changeClass = computed(() => {
  if (props.commodity.changePercent > 0) return 'rising';
  if (props.commodity.changePercent < 0) return 'falling';
  return 'neutral';
});

// 判断是否为交易时段 (基于市场)
function isInTradingHours(market: string, timeValue: number): boolean {
  const isWeekend = () => {
    const now = new Date();
    const shanghaiTime = now.toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai' });
    const shanghaiDate = new Date(shanghaiTime);
    return shanghaiDate.getDay() === 0 || shanghaiDate.getDay() === 6;
  };

  // 加密货币 24/7 交易
  if (market === 'crypto') {
    return true;
  }

  // 伦敦金银市场 (LBMA) - 24小时交易，周末休市
  if (market === 'lbma') {
    return !isWeekend();
  }

  // 上海黄金交易所 (SGE) - 日盘 9:00-15:30, 夜盘 19:50-次日02:30
  if (market === 'sge') {
    if (isWeekend()) return false;
    const daySessionStart = 9 * 60;       // 9:00
    const daySessionEnd = 15 * 60 + 30;    // 15:30
    const nightSessionStart = 19 * 60 + 50; // 19:50
    const nightSessionEnd = 24 * 60 + 150;  // 次日 02:30 = 24*60 + 150

    // 夜盘跨日处理
    if (timeValue >= nightSessionStart) {
      // 当天夜盘时段
      return timeValue < nightSessionEnd;
    } else if (timeValue < 2 * 60 + 30) {
      // 次日凌晨时段（夜盘延续）
      return true;
    }
    // 日盘时段
    return timeValue >= daySessionStart && timeValue < daySessionEnd;
  }

  // COMEX (纽约商品交易所) - 8:00-13:30 纽约时间 = 21:00-02:30 北京时间
  if (market === 'comex') {
    if (isWeekend()) return false;
    const openHour = 21;  // 北京时间 21:00
    const closeHour = 2;   // 次日 02:30
    const closeMinute = 30;
    const closeTimeValue = closeHour * 60 + closeMinute; // 150

    if (timeValue >= openHour * 60) {
      // 当天晚盘时段 (21:00-23:59)
      return true;
    } else if (timeValue < closeTimeValue) {
      // 次日凌晨时段
      return true;
    }
    return false;
  }

  // CME (芝加哥商品交易所) - 大部分品种 8:00-13:30 芝加哥时间 = 22:00-03:30 北京时间
  if (market === 'cme') {
    if (isWeekend()) return false;
    const openHour = 22;  // 北京时间 22:00
    const closeHour = 3;   // 次日 03:30
    const closeMinute = 30;
    const closeTimeValue = closeHour * 60 + closeMinute; // 210

    if (timeValue >= openHour * 60) {
      return true;
    } else if (timeValue < closeTimeValue) {
      return true;
    }
    return false;
  }

  // 默认 A 股交易时间 (仅作备用)
  if (market === 'china' || market === 'sse' || market === 'szse') {
    if (isWeekend()) return false;
    const daySessionStart = 9 * 60;    // 9:30
    const daySessionEnd = 15 * 60;     // 15:00
    return timeValue >= daySessionStart && timeValue < daySessionEnd;
  }

  return false;
}

// 交易状态判断
const tradingStatus = computed(() => {
  // 优先使用后端返回的状态
  if (props.commodity.tradingStatus) {
    return props.commodity.tradingStatus;
  }

  const timestamp = props.commodity.timestamp;
  const symbol = props.commodity.symbol;
  const market = getCommodityMarket(symbol);

  // 检查缓存的交易日状态
  const cachedTradingDay = tradingDayCache.value[market];

  // 如果不是交易日（周末/节假日），直接返回 closed
  if (cachedTradingDay === false) {
    return 'closed';
  }

  // 加密货币 24/7 交易
  if (market === 'crypto') {
    return 'open';
  }

  // 如果有数据时间戳，根据时间判断
  if (timestamp) {
    try {
      // 处理纯时间格式 "15:30:00" (沪金实时数据)
      const timeMatch = timestamp.match(/^(\d{2}):(\d{2}):(\d{2})$/);
      if (timeMatch) {
        // 获取当前上海时间
        const now = new Date();
        const shanghaiTime = now.toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai' });
        const shanghaiDate = new Date(shanghaiTime);
        const hour = shanghaiDate.getHours();
        const minute = shanghaiDate.getMinutes();
        const timeValue = hour * 60 + minute;

        // 根据市场判断是否在交易时段
        if (isInTradingHours(market, timeValue)) {
          return 'open';
        }
        return 'closed';
      }

      // 处理完整时间格式 "2026-02-14 05:59:50 UTC"
      const dateStr = timestamp.replace(' UTC', '').trim();
      const dataTime = new Date(dateStr + 'Z');
      const now = new Date();
      const diffMinutes = (now.getTime() - dataTime.getTime()) / (1000 * 60);

      // 数据超过15分钟认为已收盘
      if (diffMinutes > 15) {
        return 'closed';
      }
      return 'open';
    } catch {
      return 'unknown';
    }
  }

  // 如果没有时间戳，根据当前市场时间判断
  const now = new Date();
  const shanghaiTime = now.toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai' });
  const shanghaiDate = new Date(shanghaiTime);
  const hour = shanghaiDate.getHours();
  const minute = shanghaiDate.getMinutes();
  const timeValue = hour * 60 + minute;

  if (isInTradingHours(market, timeValue)) {
    return 'open';
  }

  // 周末检查 - 对所有市场生效
  const day = shanghaiDate.getDay();
  if (day === 0 || day === 6) {
    return 'closed';
  }

  return 'unknown';
});

const statusText = computed(() => {
  const labels: Record<string, string> = {
    'open': '交易中',
    'closed': '已收盘',
    'unknown': '未知',
  };
  return labels[tradingStatus.value] || '未知';
});

// 价格动画状态
const priceAnimating = ref(false);
const changeAnimating = ref(false);

// 监听价格变化触发动画
watch(() => props.commodity.price, (newVal, oldVal) => {
  if (oldVal !== undefined && newVal !== undefined && newVal !== oldVal) {
    triggerPriceAnimation();
  }
});

watch(() => props.commodity.changePercent, (newVal, oldVal) => {
  if (oldVal !== undefined && newVal !== undefined && newVal !== oldVal) {
    triggerChangeAnimation();
  }
});

function triggerPriceAnimation() {
  priceAnimating.value = true;
  setTimeout(() => priceAnimating.value = false, 500);
}

function triggerChangeAnimation() {
  changeAnimating.value = true;
  setTimeout(() => changeAnimating.value = false, 500);
}

async function toggleWatch() {
  const category = getCommodityCategory(props.commodity.symbol);
  if (isWatched.value) {
    await store.removeFromWatchlist(props.commodity.symbol);
  } else {
    await store.addToWatchlist(
      props.commodity.symbol,
      props.commodity.name,
      category
    );
  }
}

function formatPrice(value: number): string {
  if (value == null) return '--';
  if (value >= 1000) {
    return value.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }
  return value.toFixed(2);
}

function formatChange(value: number): string {
  if (value == null) return '--';
  const sign = value >= 0 ? '+' : '';
  return `${sign}${value.toFixed(2)}`;
}

function formatPercent(value: number): string {
  if (value == null) return '--';
  const sign = value >= 0 ? '+' : '';
  return `${sign}${value.toFixed(2)}%`;
}

function formatTime(dateStr: string | undefined | null): string {
  if (!dateStr) return '--';
  try {
    // 处理 ISO 格式 "2026-02-13T00:00:00Z"
    if (dateStr.includes('T') && dateStr.endsWith('Z')) {
      const date = new Date(dateStr);
      if (isNaN(date.getTime())) return '--';
      return date.toLocaleTimeString('zh-CN', {
        timeZone: 'Asia/Shanghai',
        hour12: false,
        hour: '2-digit',
        minute: '2-digit',
      });
    }
    // 处理纯日期格式 "2026-02-13"
    if (/^\d{4}-\d{2}-\d{2}$/.test(dateStr)) {
      return dateStr;
    }
    // 处理纯时间格式 "15:30:00" (沪金实时数据)
    if (/^\d{2}:\d{2}:\d{2}$/.test(dateStr)) {
      return dateStr;
    }
    // 处理 "2026-02-13 21:59:50 UTC" 格式
    const utcStr = dateStr.replace(' UTC', '').trim();
    const date = new Date(utcStr + 'Z');
    if (isNaN(date.getTime())) return '--';
    return date.toLocaleTimeString('zh-CN', {
      timeZone: 'Asia/Shanghai',
      hour12: false,
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return '--';
  }
}
</script>

<style lang="scss" scoped>
.commodity-card {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: var(--spacing-lg);
  transition: all var(--transition-normal);
  cursor: pointer;

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
    width: 50%;
    height: 18px;
  }

  &.skeleton-price {
    width: 70%;
    height: 24px;
  }

  &.skeleton-change {
    width: 30%;
  }
}

.card-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: var(--spacing-md);
}

.header-tags {
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
}

.commodity-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.commodity-symbol {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
  font-family: var(--font-mono);
  font-weight: var(--font-weight-medium);
}

.commodity-name {
  font-size: var(--font-size-md);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}

.commodity-source {
  font-size: var(--font-size-xs);
  padding: 2px 8px;
  background: var(--color-bg-tertiary);
  border-radius: var(--radius-full);
  color: var(--color-text-secondary);
}

.trading-status {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 2px 8px;
  border-radius: var(--radius-full);
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-medium);

  .status-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
  }

  .status-text {
    line-height: 1;
  }

  &.status-open {
    background: var(--color-rise-bg);
    color: var(--color-rise);

    .status-dot {
      background: var(--color-rise);
    }
  }

  &.status-closed {
    background: var(--color-bg-tertiary);
    color: var(--color-text-tertiary);

    .status-dot {
      background: var(--color-text-tertiary);
    }
  }

  &.status-unknown {
    background: var(--color-bg-tertiary);
    color: var(--color-text-tertiary);

    .status-dot {
      background: var(--color-text-tertiary);
    }
  }
}

.action-btn {
  width: 28px;
  height: 28px;
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
  }
}

.watch-btn {
  &:hover {
    color: var(--color-rise);
  }

  &.active {
    opacity: 1;
    color: #fbbf24;

    svg {
      fill: #fbbf24;
    }
  }
}

.commodity-card:hover .action-btn {
  opacity: 1;
}

.card-body {
  font-size: var(--font-size-xs);
  padding: 2px 8px;
  background: var(--color-bg-tertiary);
  border-radius: var(--radius-full);
  color: var(--color-text-secondary);
}

.card-body {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  margin-bottom: var(--spacing-md);
}

.price-section {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.price {
  font-size: var(--font-size-2xl);
  font-weight: var(--font-weight-bold);
  color: var(--color-text-primary);
  line-height: 1;
  transition: all 0.3s ease;

  &.value-updated {
    animation: value-pulse 0.5s ease-out;
  }
}

.currency {
  font-size: var(--font-size-sm);
  color: var(--color-text-tertiary);
}

@keyframes value-pulse {
  0% {
    transform: scale(1);
    color: var(--color-text-primary);
  }
  30% {
    color: var(--color-rise);
  }
  50% {
    transform: scale(1.05);
  }
  100% {
    transform: scale(1);
    color: var(--color-text-primary);
  }
}

.change-section {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 2px;
  padding: var(--spacing-xs) var(--spacing-sm);
  border-radius: var(--radius-md);
  transition: all var(--transition-fast);

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
    transform: scale(1.05);
  }
  100% {
    transform: scale(1);
  }
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
  flex-direction: column;
  gap: var(--spacing-xs);
  padding-top: var(--spacing-sm);
  border-top: 1px solid var(--color-divider);
}

.card-footer-row2 {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.price-range {
  display: flex;
  gap: var(--spacing-md);
}

.range-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
}

.label {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
}

.value {
  font-size: var(--font-size-xs);
  color: var(--color-text-secondary);
}

.timestamp {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
  white-space: nowrap;
}

.commodity-source {
  font-size: 10px;
  color: var(--color-text-tertiary);
  padding: 1px 4px;
  background: var(--color-bg-tertiary);
  border-radius: 3px;
  white-space: nowrap;
  max-width: 120px;
  overflow: hidden;
  text-overflow: ellipsis;
}
</style>
