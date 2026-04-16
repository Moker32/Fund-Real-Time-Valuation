<template>
  <div class="fund-chart" ref="chartContainer">
    <div v-if="!hasData" class="chart-empty">
      <span class="chart-empty-text">暂无数据</span>
    </div>
    <div v-if="isTooltipVisible" class="chart-tooltip" :style="tooltipStyle">
      <div class="tooltip-time">{{ tooltipTime }}</div>
      <div class="tooltip-value">{{ tooltipValue }}</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, computed } from 'vue';
import uPlot from 'uplot';
import 'uplot/dist/uPlot.min.css';

interface uPlotWithBaseline extends uPlot {
  _baselineColor?: string;
}

interface ChartDataItem {
  time: string;
  price?: number;
  close?: number | null;
}

interface LunchBreak {
  start: number;  // minutes from midnight, e.g., 11:30 -> 690
  end: number;    // minutes from midnight, e.g., 13:00 -> 780
}

const props = withDefaults(defineProps<{
  data: ChartDataItem[];
  height?: number;
  baseline?: number;
  trend?: 'rising' | 'falling' | 'neutral';
  showAxes?: boolean;
  showTooltip?: boolean;
  lunchBreak?: LunchBreak;  // 午休时间段，如 { start: 690, end: 780 } 表示 11:30-13:00
}>(), {
  height: 100,
  trend: 'neutral',
  showAxes: true,
  showTooltip: true,
});

const chartContainer = ref<HTMLElement | null>(null);
let uplotInstance: uPlot | null = null;

const color = computed(() => getTrendColor());

const hasData = computed(() => {
  if (!uplotInstance && (!props.data || props.data.length === 0)) return false;
  return true;
});

let lastDataJson = '';
let processedTimestamps: number[] = [];
let processedValues: (number | null)[] = [];
let realTimestamps: number[] = [];
let rawDataItems: ChartDataItem[] = [];
let lunchBreakX: number | null = null;

const getTrendColor = (): string => {
  if (props.trend === 'rising') return '#ef4444';
  if (props.trend === 'falling') return '#22c55e';
  return '#71717a';
};

const parseTimeToTimestamp = (timeStr: string): number => {
  const timeOnlyMatch = timeStr.match(/^(\d{1,2}):(\d{2})$/);
  if (timeOnlyMatch && timeOnlyMatch[1] && timeOnlyMatch[2]) {
    const hour = parseInt(timeOnlyMatch[1], 10);
    const minute = parseInt(timeOnlyMatch[2], 10);
    const now = new Date();
    return Math.floor(new Date(now.getFullYear(), now.getMonth(), now.getDate(), hour, minute, 0).getTime() / 1000);
  }

  const date = new Date(timeStr);
  if (!isNaN(date.getTime())) {
    return Math.floor(date.getTime() / 1000);
  }

  const match = timeStr.match(/^(\d{4})-(\d{2})-(\d{2})(?:[\sT](\d{2}):(\d{2}):?(\d{2})?)?$/);
  if (match) {
    const year = parseInt(match[1] ?? '0', 10);
    const month = (parseInt(match[2] ?? '0', 10)) - 1;
    const day = parseInt(match[3] ?? '0', 10);
    const hour = match[4] ? parseInt(match[4], 10) : 0;
    const minute = match[5] ? parseInt(match[5], 10) : 0;
    const second = match[6] ? parseInt(match[6], 10) : 0;
    return Math.floor(new Date(year, month, day, hour, minute, second).getTime() / 1000);
  }

  return Math.floor(Date.now() / 1000);
};

const isIntradayData = (data: ChartDataItem[]): boolean => {
  if (!data || data.length === 0) return false;
  const firstItem = data[0]!;
  return 'price' in firstItem && !('close' in firstItem);
};

const getIntradayXRange = (data: ChartDataItem[]): { min: number; max: number } | null => {
  if (!isIntradayData(data) || data.length === 0) return null;

  const timestamps: number[] = [];
  for (const item of data) {
    if (item && item.time) {
      const ts = parseTimeToTimestamp(item.time);
      timestamps.push(ts);
    }
  }

  if (timestamps.length === 0) return null;

  const minTs = Math.min(...timestamps);
  const maxTs = Math.max(...timestamps);
  const padding = 5 * 60;

  return { min: minTs - padding, max: maxTs + padding };
};

const getYScaleRange = (data: [number[], (number | null)[]] | null, baseline: number | undefined): { min: number; max: number } | undefined => {
  if (!data || data[0].length === 0) return undefined;

  const values = data[1];
  let min = Infinity;
  let max = -Infinity;

  for (const v of values) {
    if (v !== null && typeof v === 'number') {
      min = Math.min(min, v);
      max = Math.max(max, v);
    }
  }

  if (min === Infinity || max === -Infinity) return undefined;

  const padding = (max - min) * 0.02;
  min -= padding;
  max += padding;

  if (baseline !== undefined && baseline > 0) {
    if (baseline <= min + padding * 0.5) {
      min = baseline - (max - baseline) * 0.1;
    }
    if (baseline >= max - padding * 0.5) {
      max = baseline + (baseline - min) * 0.1;
    }
    min = Math.min(min, baseline);
    max = Math.max(max, baseline);
  }

  return { min, max };
};

const formatXAxisLabel = (timestamp: number): string => {
  if (isIntradayData(props.data) && realTimestamps.length > 0) {
    const idx = processedTimestamps.indexOf(timestamp);
    if (idx >= 0 && realTimestamps[idx]) {
      const date = new Date(realTimestamps[idx] * 1000);
      const h = date.getHours();
      const m = date.getMinutes();
      return `${h}:${m.toString().padStart(2, '0')}`;
    }
    const h = timestamp >= 40000 ? Math.floor(timestamp / 3600) % 24 : new Date(timestamp * 1000).getHours();
    const m = timestamp >= 40000 ? Math.floor((timestamp % 3600) / 60) : new Date(timestamp * 1000).getMinutes();
    return `${h}:${m.toString().padStart(2, '0')}`;
  }
  const date = new Date(timestamp * 1000);
  const month = date.getMonth() + 1;
  const day = date.getDate();
  return `${month}/${day}`;
};

const isTooltipVisible = ref(false);
const tooltipStyle = ref<Record<string, string>>({});
const tooltipTime = ref('');
const tooltipValue = ref('');

const onCursorMove = (u: uPlot) => {
  const idx = u.cursor.idx;
  if (idx == null || idx < 0 || !rawDataItems.length) {
    isTooltipVisible.value = false;
    return;
  }

  const rawItem = rawDataItems[idx];
  if (!rawItem) {
    isTooltipVisible.value = false;
    return;
  }

  const val = processedValues[idx];
  if (val == null) {
    isTooltipVisible.value = false;
    return;
  }

  const ts = realTimestamps.length > 0 ? realTimestamps[idx] : processedTimestamps[idx];
  const date = new Date(ts * 1000);

  if (isIntradayData(props.data)) {
    tooltipTime.value = rawItem.time;
  } else {
    tooltipTime.value = `${date.getFullYear()}-${(date.getMonth() + 1).toString().padStart(2, '0')}-${date.getDate().toString().padStart(2, '0')}`;
  }

  tooltipValue.value = val.toFixed(4);

  const displayTs = processedTimestamps[idx];
  const xPos = u.valToPos(displayTs, 'x', true);
  const yPos = u.valToPos(val, 'y', true);
  const containerWidth = chartContainer.value?.clientWidth ?? 300;

  let left = xPos + 12;
  if (left + 120 > containerWidth) {
    left = xPos - 130;
  }

  tooltipStyle.value = {
    left: `${left}px`,
    top: `${yPos - 40}px`,
  };
  isTooltipVisible.value = true;
};

const initChart = () => {
  if (!chartContainer.value) return;
  if (uplotInstance) return;

  chartContainer.value.innerHTML = '';
  const xRange = getIntradayXRange(props.data);

  try {
    uplotInstance = new uPlot({
      width: chartContainer.value.clientWidth || 300,
      height: props.height,
      legend: { show: false },
      series: [
        {},
        {
          stroke: color.value,
          width: 2,
          fill: (u: uPlot) => {
            const ctx = u.ctx;
            const gradient = ctx.createLinearGradient(0, 0, 0, u.bbox.height);
            const c = color.value;
            gradient.addColorStop(0, c + '30');
            gradient.addColorStop(1, c + '05');
            return gradient;
          },
          points: { show: false },
          spanGaps: false,
        },
      ],
      axes: [
        props.showAxes
          ? {
              show: true,
              space: 60,
              size: 24,
              stroke: '#444',
              grid: { show: false },
              ticks: { show: false },
              font: '11px -apple-system, sans-serif',
              values: (_u: uPlot, vals: number[]) => vals.map(v => formatXAxisLabel(v)),
            }
          : { show: false },
        props.showAxes
          ? {
              show: true,
              space: 30,
              size: 50,
              stroke: '#444',
              grid: { show: true, stroke: '#2a2a2a', width: 1 },
              ticks: { show: false },
              font: '11px -apple-system, sans-serif',
              values: (_u: uPlot, vals: number[]) => vals.map(v => v.toFixed(4)),
            }
          : { show: false },
      ],
      scales: {
        x: {
          time: true,
          ...(xRange && { min: xRange.min, max: xRange.max }),
        },
        y: { auto: true },
      },
      cursor: {
        drag: { x: false, y: false },
        show: props.showTooltip,
        x: props.showTooltip,
        y: false,
        lock: props.showTooltip,
        points: props.showTooltip
          ? {
              show: true,
              size: 6,
              width: 2,
              stroke: (_u: uPlot) => color.value,
              fill: '#1e1e1e',
            }
          : { show: false },
      },
      hooks: {
        ...(props.showTooltip ? { setCursor: [onCursorMove] } : {}),
        draw: [
          (u: uPlot) => {
            const ctx = u.ctx;
            ctx.save();

            if (lunchBreakX !== null) {
              const xPos = u.valToPos(lunchBreakX, 'x', true);
              if (xPos > u.bbox.left + 2 && xPos < u.bbox.left + u.bbox.width - 2) {
                ctx.strokeStyle = 'rgba(255, 255, 255, 0.2)';
                ctx.lineWidth = 1;
                ctx.setLineDash([2, 2]);
                ctx.beginPath();
                ctx.moveTo(xPos, u.bbox.top);
                ctx.lineTo(xPos, u.bbox.top + u.bbox.height);
                ctx.stroke();
              }
            }

            if (props.baseline !== undefined) {
              const baseline = props.baseline;
              const yScale = u.scales.y;
              if (yScale) {
                const yPos = u.valToPos(baseline, 'y', true);
                if (yPos >= 0 && yPos <= u.bbox.height) {
                  const uWithBaseline = u as uPlotWithBaseline;
                  ctx.strokeStyle = uWithBaseline._baselineColor ?? getTrendColor();
                  ctx.lineWidth = 1;
                  ctx.setLineDash([4, 4]);
                  ctx.beginPath();
                  ctx.moveTo(u.bbox.left, yPos);
                  ctx.lineTo(u.bbox.left + u.bbox.width, yPos);
                  ctx.stroke();
                }
              }
            }

            ctx.restore();
          },
        ],
      },
    }, [], chartContainer.value);
  } catch (e) {
    console.error('[FundChart] 初始化图表失败:', e);
  }
};

const updateData = () => {
  if (!uplotInstance) return;
  if (!props.data || props.data.length === 0) return;

  const validData = props.data.filter((item): item is { time: string; price: number; close?: number | null } => {
    if (!item) return false;
    const price = 'close' in item ? item.close : item.price;
    return typeof price === 'number' && typeof item.time === 'string' && item.time.length > 0;
  });

  if (validData.length === 0) return;

  const currentDataJson = JSON.stringify(validData.map(d => d.time + (d.close ?? d.price)));
  if (currentDataJson === lastDataJson) return;
  lastDataJson = currentDataJson;

  rawDataItems = [...validData];

  const sortedData = [...validData].sort((a, b) => {
    const tsA = parseTimeToTimestamp(a.time);
    const tsB = parseTimeToTimestamp(b.time);
    return tsA - tsB;
  });

  const isAStockIntraday = isIntradayData(props.data) && hasLunchBreak(sortedData);

  if (isAStockIntraday) {
    buildCompressedIntradayData(sortedData);
  } else {
    buildRegularData(sortedData);
  }

  const newData: [number[], (number | null)[]] = [processedTimestamps, processedValues];

  try {
    uplotInstance.setData(newData);
    updateYScaleRange(newData);
  } catch (e) {
    console.warn('[FundChart] setData error:', e);
  }
};

const LUNCH_BREAK_START = 11 * 60 + 30;
const LUNCH_BREAK_END = 13 * 60;

// 获取午休时间配置，优先使用 props.lunchBreak，否则使用默认值（A 股）
const getLunchBreakConfig = (): { start: number; end: number } => {
  if (props.lunchBreak) {
    return { start: props.lunchBreak.start, end: props.lunchBreak.end };
  }
  return { start: LUNCH_BREAK_START, end: LUNCH_BREAK_END };
};

const hasLunchBreak = (data: { time: string }[]): boolean => {
  const { start, end } = getLunchBreakConfig();
  let hasMorning = false;
  let hasAfternoon = false;
  let hasLunchGap = true;

  for (const item of data) {
    const m = item.time.match(/^(\d{1,2}):(\d{2})$/);
    if (!m || !m[1] || !m[2]) continue;
    const minutes = parseInt(m[1], 10) * 60 + parseInt(m[2], 10);
    if (minutes <= start) hasMorning = true;
    if (minutes >= end) hasAfternoon = true;
    if (minutes > start && minutes < end) hasLunchGap = false;
  }
  return hasMorning && hasAfternoon && hasLunchGap;
};

const timeToMinutes = (timeStr: string): number => {
  const m = timeStr.match(/^(\d{1,2}):(\d{2})$/);
  if (!m || !m[1] || !m[2]) return -1;
  return parseInt(m[1], 10) * 60 + parseInt(m[2], 10);
};

const minutesToTimestamp = (minutes: number): number => {
  const now = new Date();
  return Math.floor(new Date(now.getFullYear(), now.getMonth(), now.getDate(), Math.floor(minutes / 60), minutes % 60, 0).getTime() / 1000);
};

const buildCompressedIntradayData = (sortedData: { time: string; price?: number; close?: number | null }[]) => {
  const { start, end } = getLunchBreakConfig();
  const displayTimestamps: number[] = [];
  const values: (number | null)[] = [];
  const reals: number[] = [];

  let lunchIdx = -1;

  for (const item of sortedData) {
    const minutes = timeToMinutes(item.time);
    if (minutes < 0) continue;

    const price = 'close' in item ? (item.close ?? item.price) : item.price;
    if (price === undefined) continue;

    const realTs = parseTimeToTimestamp(item.time);

    let displayMinutes: number;
    if (minutes <= start) {
      displayMinutes = minutes;
    } else {
      displayMinutes = minutes - (end - start);
    }

    const displayTs = minutesToTimestamp(displayMinutes);

    if (lunchIdx === -1 && minutes > start && displayTimestamps.length > 0) {
      lunchIdx = displayTimestamps.length;
    }

    displayTimestamps.push(displayTs);
    values.push(price);
    reals.push(realTs);
  }

  if (lunchIdx > 0) {
    lunchBreakX = minutesToTimestamp(start);
  }

  processedTimestamps = displayTimestamps;
  processedValues = values;
  realTimestamps = reals;
};

const buildRegularData = (sortedData: { time: string; price?: number; close?: number | null }[]) => {
  const timestamps: number[] = [];
  const values: (number | null)[] = [];
  const reals: number[] = [];

  for (const item of sortedData) {
    const ts = parseTimeToTimestamp(item.time);
    const price = 'close' in item ? (item.close ?? item.price) : item.price;
    if (price === undefined) continue;

    timestamps.push(ts);
    values.push(price);
    reals.push(ts);
  }

  const lastTs = timestamps[timestamps.length - 1];
  const now = new Date();
  const currentTimeInMinutes = now.getHours() * 60 + now.getMinutes();
  const marketEndInMinutes = 15 * 60;
  const marketStartInMinutes = 9 * 60 + 30;

  if (lastTs && currentTimeInMinutes > marketStartInMinutes && currentTimeInMinutes < marketEndInMinutes) {
    const year = now.getFullYear();
    const month = now.getMonth();
    const day = now.getDate();
    const marketEndTs = Math.floor(new Date(year, month, day, 15, 0, 0).getTime() / 1000);

    timestamps.push(lastTs + 60);
    values.push(null);
    reals.push(0);
    timestamps.push(marketEndTs);
    values.push(null);
    reals.push(0);
  }

  processedTimestamps = timestamps;
  processedValues = values;
  realTimestamps = reals;
};

const updateYScaleRange = (data: [number[], (number | null)[]]) => {
  if (!uplotInstance) return;

  const range = getYScaleRange(data, props.baseline);
  if (!range) return;

  try {
    uplotInstance.setScale('y', range);
  } catch (e) {
    console.warn('[FundChart] setScale error:', e);
  }
};

const updateColor = () => {
  if (!uplotInstance) return;

  const newColor = getTrendColor();
  try {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    uplotInstance.setSeries(1, { stroke: newColor } as any);
    (uplotInstance as uPlotWithBaseline)._baselineColor = newColor;
    uplotInstance.redraw();
  } catch (e) {
    console.warn('[FundChart] updateColor error:', e);
  }
};

let lastDataType: 'history' | 'intraday' | null = null;

watch(() => props.data, (newData) => {
  if (!uplotInstance && chartContainer.value && newData && newData.length > 0) {
    initChart();
    lastDataType = isIntradayData(newData) ? 'intraday' : 'history';
  }

  if (!uplotInstance) return;
  if (!newData || newData.length === 0) return;

  const currentDataType = isIntradayData(newData) ? 'intraday' : 'history';
  if (lastDataType !== null && lastDataType !== currentDataType) {
    uplotInstance.destroy();
    uplotInstance = null;
    lastDataType = null;
    initChart();
    lastDataType = currentDataType;
  }

  updateColor();
  updateData();
}, { deep: true, flush: 'post' });

watch(() => props.trend, () => {
  if (uplotInstance) {
    updateColor();
  }
});

watch(() => props.baseline, () => {
  if (uplotInstance) {
    const data = uplotInstance.data;
    if (data && data[0].length > 0) {
      updateYScaleRange(data as [number[], (number | null)[]]);
    }
    uplotInstance.redraw();
  }
});

onMounted(() => {
  if (props.data && props.data.length > 0) {
    initChart();
    updateColor();
    updateData();
  }
  window.addEventListener('resize', handleResize);
});

onUnmounted(() => {
  window.removeEventListener('resize', handleResize);
  if (uplotInstance) {
    uplotInstance.destroy();
    uplotInstance = null;
  }
});

const handleResize = () => {
  if (uplotInstance && chartContainer.value) {
    uplotInstance.setSize({
      width: chartContainer.value.clientWidth,
      height: props.height,
    });
  }
};
</script>

<style scoped>
.fund-chart {
  width: 100%;
  min-height: v-bind('props.height + "px"');
  margin-top: 8px;
  border-radius: 6px;
  overflow: hidden;
  position: relative;
}

.fund-chart :deep(.uplot) {
  filter: none !important;
}

.fund-chart :deep(.uplot .u-over) {
  cursor: crosshair !important;
}

.fund-chart :deep(.uplot .u-cursor-x) {
  stroke: #555 !important;
  stroke-width: 1 !important;
  stroke-dasharray: 3 3 !important;
}

.chart-tooltip {
  position: absolute;
  z-index: 10;
  background: rgba(30, 30, 30, 0.95);
  border: 1px solid #3a3a3a;
  border-radius: 6px;
  padding: 6px 10px;
  pointer-events: none;
  font-size: 12px;
  backdrop-filter: blur(4px);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
  transition: opacity 0.15s ease;
}

.tooltip-time {
  color: #888;
  font-size: 11px;
  margin-bottom: 2px;
}

.tooltip-value {
  color: #fff;
  font-weight: 600;
  font-family: 'SF Mono', 'Fira Code', monospace;
  font-size: 13px;
}

.chart-empty {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-bg-tertiary, #f9fafb);
  border-radius: 6px;
}

.chart-empty-text {
  font-size: 12px;
  color: var(--color-text-tertiary, #9ca3af);
}
</style>
