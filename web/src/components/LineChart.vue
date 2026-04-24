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
  timezone?: string;       // 市场时区，如 'Asia/Shanghai', 'Europe/Berlin', 'America/New_York'
  streaming?: boolean;      // streaming 模式，增量追加数据
  maxPoints?: number;       // streaming 模式下最大数据点数，超出后丢弃最老的点
}>(), {
  height: 100,
  trend: 'neutral',
  showAxes: true,
  showTooltip: true,
  streaming: false,
});

const chartContainer = ref<HTMLElement | null>(null);
const uplotInstance = ref<uPlot | null>(null);

const color = computed(() => getTrendColor());

const hasData = computed(() => {
  return !!(props.data && props.data.length > 0);
});

// 调试：追踪 data 变化
watch(() => props.data, () => {
  // console.log('[LineChart] data changed for chart - length:', newData?.length ?? 0);
}, { immediate: true });

const lastDataJson = ref('');
const processedTimestamps = ref<number[]>([]);
const processedValues = ref<(number | null)[]>([]);
const realTimestamps = ref<number[]>([]);
const rawDataItems = ref<ChartDataItem[]>([]);
const lastDataLen = ref(0);  // streaming 模式追踪已有数据长度

// 午休区间标记：用于绘制虚线
const lunchBreakSegment = ref<{ start: number; end: number; price: number } | null>(null);

// 重新设置 X 轴范围（固定为市场交易时段）
const resetXScale = () => {
  if (!uplotInstance.value) return;
  const { start: marketStart, end: marketEnd } = getMarketTradingRange();

  // 从第一数据点提取日期作为 baseDate
  let baseDate: Date;
  const firstRealTs = realTimestamps.value[0];
  if (firstRealTs != null && firstRealTs > 0) {
    baseDate = new Date(firstRealTs * 1000);
  } else {
    baseDate = new Date();
  }
  baseDate.setHours(0, 0, 0, 0);

  const padding = 5 * 60;
  const min = minutesToTimestamp(marketStart, baseDate, props.timezone) - padding;
  const max = minutesToTimestamp(marketEnd, baseDate, props.timezone) + padding;

  uplotInstance.value.setScale('x', { min, max });
};

const getTrendColor = (): string => {
  if (props.trend === 'rising') return '#ef4444';
  if (props.trend === 'falling') return '#22c55e';
  return '#71717a';
};

const getTimezoneOffsetMinutes = (tzName: string, now: Date): number => {
  const utcStr = now.toLocaleString('en-US', { timeZone: 'UTC', hour12: false });
  const utcH = parseInt(utcStr.match(/(\d+):(\d+)/)?.[1] || '0', 10);
  const utcM = parseInt(utcStr.match(/(\d+):(\d+)/)?.[2] || '0', 10);
  const targetStr = now.toLocaleString('en-US', { timeZone: tzName, hour12: false });
  const targetH = parseInt(targetStr.match(/(\d+):(\d+)/)?.[1] || '0', 10);
  const targetM = parseInt(targetStr.match(/(\d+):(\d+)/)?.[2] || '0', 10);
  return (targetH * 60 + targetM) - (utcH * 60 + utcM);
};

const timeToMinutes = (timeStr: string): number => {
  const m = timeStr.match(/^(\d{1,2}):(\d{2})$/);
  if (!m || !m[1] || !m[2]) return -1;
  return parseInt(m[1], 10) * 60 + parseInt(m[2], 10);
};

// 将市场时间转换为 UTC 时间戳
// timeStr: "HH:mm" 格式的市场当地时间
// tzName: IANA 时区名，如 'Asia/Shanghai', 'Europe/Berlin'
const parseTimeToTimestamp = (timeStr: string, tzName?: string): number => {
  const timeOnlyMatch = timeStr.match(/^(\d{1,2}):(\d{2})$/);
  if (timeOnlyMatch && timeOnlyMatch[1] && timeOnlyMatch[2]) {
    const hour = parseInt(timeOnlyMatch[1], 10);
    const minute = parseInt(timeOnlyMatch[2], 10);
    const now = new Date();

    if (tzName) {
      const tzOffsetMinutes = getTimezoneOffsetMinutes(tzName, now);
      const todayUtc = Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate(), 0, 0, 0);
      const marketMinuteOfDay = hour * 60 + minute;
      const utcMarketMinute = marketMinuteOfDay - tzOffsetMinutes;
      return Math.floor((todayUtc + utcMarketMinute * 60000) / 1000);
    }

    // 默认：使用浏览器本地时间
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
      const ts = parseTimeToTimestamp(item.time, props.timezone);
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
    // expand range to include baseline when it's near an edge (within 0.5× padding)
    min = Math.min(min, baseline);
    max = Math.max(max, baseline);
  }

  return { min, max };
};

const formatXAxisLabel = (timestamp: number): string => {
  if (isIntradayData(props.data) && realTimestamps.value.length > 0) {
    const idx = processedTimestamps.value.indexOf(timestamp);
    if (idx >= 0 && realTimestamps.value[idx]) {
      const date = new Date(realTimestamps.value[idx] * 1000);
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
  if (idx == null || idx < 0 || !rawDataItems.value.length) {
    isTooltipVisible.value = false;
    return;
  }

  const rawItem = rawDataItems.value[idx];
  if (!rawItem) {
    isTooltipVisible.value = false;
    return;
  }

  const val = processedValues.value[idx];
  if (val == null) {
    isTooltipVisible.value = false;
    return;
  }

  const ts = realTimestamps.value[idx] ?? processedTimestamps.value[idx];
  if (ts == null) {
    isTooltipVisible.value = false;
    return;
  }
  const date = new Date(ts * 1000);

  if (isIntradayData(props.data)) {
    tooltipTime.value = rawItem.time;
  } else {
    tooltipTime.value = `${date.getFullYear()}-${(date.getMonth() + 1).toString().padStart(2, '0')}-${date.getDate().toString().padStart(2, '0')}`;
  }

  tooltipValue.value = val.toFixed(4);

  const xTs = processedTimestamps.value[idx];
  const xPos = xTs != null ? u.valToPos(xTs, 'x', true) : 0;
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
  if (uplotInstance.value) return;

  chartContainer.value.innerHTML = '';

  let xRange: { min: number; max: number } | null = null;
  if (props.streaming) {
    const now = new Date();
    const baseDate = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const { start: marketStart, end: marketEnd } = getMarketTradingRange();
    const padding = 5 * 60;
    xRange = {
      min: minutesToTimestamp(marketStart, baseDate, props.timezone) - padding,
      max: minutesToTimestamp(marketEnd, baseDate, props.timezone) + padding,
    };
  } else {
    xRange = getIntradayXRange(props.data);
  }

  try {
    uplotInstance.value = new uPlot({
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
          ...(xRange ? { min: xRange.min, max: xRange.max } : {}),
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
              stroke: (_u: uPlot) => color.value, // eslint-disable-line @typescript-eslint/no-unused-vars
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

            // 绘制午休虚线段
            const segment = lunchBreakSegment.value;
            if (segment !== null) {
              const startX = u.valToPos(segment.start, 'x', true);
              const endX = u.valToPos(segment.end, 'x', true);
              const yPos = u.valToPos(segment.price, 'y', true);

              if (startX >= u.bbox.left && endX <= u.bbox.left + u.bbox.width) {
                ctx.strokeStyle = (color.value + '50');
                ctx.lineWidth = 2;
                ctx.setLineDash([4, 4]);
                ctx.beginPath();
                ctx.moveTo(startX, yPos);
                ctx.lineTo(endX, yPos);
                ctx.stroke();
              }
            }

            if (props.baseline !== undefined) {
              const baseline = props.baseline;
              const yScale = u.scales.y;
              if (yScale && yScale.min !== undefined && yScale.max !== undefined) {
                // Clamp baseline to ensure it's within visible range with some padding
                const range = yScale.max - yScale.min;
                const padding = range * 0.05;
                const effectiveBaseline = Math.max(yScale.min + padding, Math.min(yScale.max - padding, baseline));
                const yPos = u.valToPos(effectiveBaseline, 'y', true);
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
  if (!uplotInstance.value) return;
  if (!props.data || props.data.length === 0) return;

  const validData = props.data.filter((item): item is { time: string; price: number; close?: number | null } => {
    if (!item) return false;
    const price = 'close' in item ? item.close : item.price;
    return typeof price === 'number' && typeof item.time === 'string' && item.time.length > 0;
  });

  if (validData.length === 0) return;

  const currentDataJson = JSON.stringify(validData.map(d => d.time + (d.close ?? d.price)));
  if (currentDataJson === lastDataJson.value) return;
  lastDataJson.value = currentDataJson;

  // streaming 模式：增量追加数据
  if (props.streaming) {
    updateDataStreaming(validData);
    return;
  }

  rawDataItems.value = [...validData];

  const sortedData = [...validData].sort((a, b) => {
    const tsA = parseTimeToTimestamp(a.time, props.timezone);
    const tsB = parseTimeToTimestamp(b.time, props.timezone);
    return tsA - tsB;
  });

  const isAStockIntraday = isIntradayData(props.data) && hasLunchBreak(sortedData);

  if (isAStockIntraday) {
    buildCompressedIntradayData(sortedData);
  } else {
    buildRegularData(sortedData);
  }

  const newData: [number[], (number | null)[]] = [processedTimestamps.value, processedValues.value];

  try {
    uplotInstance.value.setData(newData);
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

// 根据午休配置获取市场交易时段范围
// 用于 streaming 模式固定 X 轴范围
const getMarketTradingRange = (): { start: number; end: number } => {
  const { start, end } = getLunchBreakConfig();
  const hasLunch = start < end;

  if (hasLunch) {
    // 有午休的市场：根据午休时间推断交易时段
    // A 股: 9:30-11:30, 13:00-15:00 → start=570, end=900
    // 港股: 9:30-12:00, 13:00-16:00 → start=570, end=960
    // 日经: 9:00-12:30, 13:30-15:00 → start=540, end=900
    // 根据午休开始时间判断
    if (start === 690) {
      // A 股 11:30-13:00
      return { start: 570, end: 900 };
    } else if (start === 720) {
      // 港股 12:00-13:00
      return { start: 570, end: 960 };
    } else if (start === 750) {
      // 日经 12:30-13:30
      return { start: 540, end: 900 };
    } else {
      // 其他有午休的市场，默认 A 股时段
      return { start: 570, end: 900 };
    }
  } else {
    // 无午休的市场：美股/欧股 9:30-16:00 或 9:00-17:00
    return { start: 540, end: 1020 };
  }
};

const hasLunchBreak = (data: { time: string }[]): boolean => {
  const { start, end } = getLunchBreakConfig();

  // 无午休配置（start >= end），直接返回 false
  if (start >= end) {
    return false;
  }

  let hasMorning = false;
  let hasAfternoon = false;
  let hasLunchData = false;

  for (const item of data) {
    const minutes = timeToMinutes(item.time);
    if (minutes < 0) continue;
    if (minutes <= start) hasMorning = true;
    if (minutes >= end) hasAfternoon = true;
    if (minutes >= start && minutes <= end) hasLunchData = true;
  }

  // 只有上午和下午都有数据，且午休期间无数据时，才认为存在午休间隙
  return hasMorning && hasAfternoon && !hasLunchData;
};

const minutesToTimestamp = (minutes: number, baseDate?: Date, tzName?: string): number => {
  const now = baseDate ?? new Date();
  const hour = Math.floor(minutes / 60);
  const minute = minutes % 60;

  if (tzName) {
    const tzOffsetMinutes = getTimezoneOffsetMinutes(tzName, now);
    const todayUtc = Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate(), 0, 0, 0);
    const marketMinuteOfDay = hour * 60 + minute;
    const utcMarketMinute = marketMinuteOfDay - tzOffsetMinutes;
    return Math.floor((todayUtc + utcMarketMinute * 60000) / 1000);
  }

  return Math.floor(new Date(now.getFullYear(), now.getMonth(), now.getDate(), hour, minute, 0).getTime() / 1000);
};

const buildCompressedIntradayData = (sortedData: { time: string; price?: number; close?: number | null }[]) => {
  const { start, end } = getLunchBreakConfig();
  const hasLunch = start < end;

  const displayTimestamps: number[] = [];
  const values: (number | null)[] = [];
  const reals: number[] = [];

  let prevDisplayTs: number | null = null;
  let morningLastPrice: number | null = null;

  // 第一遍：找到上午最后的收盘价
  if (hasLunch) {
    for (const item of sortedData) {
      const minutes = timeToMinutes(item.time);
      if (minutes < 0) continue;
      const price = 'close' in item ? (item.close ?? item.price) : item.price;
      if (price === undefined) continue;

      if (minutes <= start) {
        morningLastPrice = price;
      }
    }
  }

  // 第二遍：构建数据，在午休区间插入 null 断开连接
  let pastLunch = false;
  for (const item of sortedData) {
    const minutes = timeToMinutes(item.time);
    if (minutes < 0) continue;

    const price = 'close' in item ? (item.close ?? item.price) : item.price;
    if (price === undefined) continue;

    const realTs = parseTimeToTimestamp(item.time, props.timezone);
    const displayTs = realTs;

    // 如果进入午休区间，插入 null 断开上午和下午的连接
    if (hasLunch && !pastLunch && minutes >= start) {
      // 在午休开始时插入 null，断开上午到午休的连接
      if (prevDisplayTs !== null) {
        displayTimestamps.push(displayTs - 1);
        values.push(null);
        reals.push(0);
      }
      pastLunch = true;

      // 记录虚线区间（用于 draw hook 绘制虚线）
      const lunchStartTs = minutesToTimestamp(start, undefined, props.timezone);
      const lunchEndTs = minutesToTimestamp(end, undefined, props.timezone);
      if (morningLastPrice !== null) {
        lunchBreakSegment.value = { start: lunchStartTs, end: lunchEndTs, price: morningLastPrice };
      }

      // 跳过当前点（12:00），它只是断开标记，不应被绘制
      continue;
    }

    // 跳过午休期间的数据点（这些是外部数据源返回的伪数据）
    if (hasLunch && pastLunch && minutes < end) {
      continue;
    }

    // 如果当前时间戳与上一个时间戳相同，插入 null 断开连接
    if (prevDisplayTs !== null && displayTs <= prevDisplayTs) {
      displayTimestamps.push(prevDisplayTs + 1);
      values.push(null);
      reals.push(0);
    }

    displayTimestamps.push(displayTs);
    values.push(price);
    reals.push(realTs);
    prevDisplayTs = displayTs;
  }

  processedTimestamps.value = displayTimestamps;
  processedValues.value = values;
  realTimestamps.value = reals;
};

const buildRegularData = (sortedData: { time: string; price?: number; close?: number | null }[]) => {
  const timestamps: number[] = [];
  const values: (number | null)[] = [];
  const reals: number[] = [];

  for (const item of sortedData) {
    const ts = parseTimeToTimestamp(item.time, props.timezone);
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

  if (lastTs && currentTimeInMinutes >= marketStartInMinutes && currentTimeInMinutes <= marketEndInMinutes) {
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

  processedTimestamps.value = timestamps;
  processedValues.value = values;
  realTimestamps.value = reals;
};

const updateYScaleRange = (data: [number[], (number | null)[]]) => {
  if (!uplotInstance.value) return;

  const range = getYScaleRange(data, props.baseline);
  if (!range) return;

  try {
    uplotInstance.value.setScale('y', range);
  } catch (e) {
    console.warn('[FundChart] setScale error:', e);
  }
};

const updateColor = () => {
  if (!uplotInstance.value) return;

  const newColor = getTrendColor();
  try {
    uplotInstance.value.setSeries(1, { stroke: newColor } as uPlot.Series);
    (uplotInstance.value as uPlotWithBaseline)._baselineColor = newColor;
    uplotInstance.value.redraw();
  } catch (e) {
    console.warn('[FundChart] updateColor error:', e);
  }
};

const lastDataType = ref<'history' | 'intraday' | null>(null);

watch(() => props.data, (newData) => {
  console.log('[LineChart] data changed - length:', newData?.length ?? 0, 'for chart');
  // 如果从有数据变成没数据，打印警告和调用栈
  if (lastDataLen.value > 0 && (!newData || newData.length === 0)) {
    console.log('[LineChart] WARNING: data dropped from', lastDataLen.value, 'to 0!');
    console.log('[LineChart] Stack trace:', new Error().stack);
  }
  if (newData?.length > 0) {
    lastDataLen.value = newData.length;
  }
  if (!uplotInstance.value && chartContainer.value && newData && newData.length > 0) {
    initChart();
    lastDataType.value = isIntradayData(newData) ? 'intraday' : 'history';
  }

  if (!uplotInstance.value) return;
  if (!newData || newData.length === 0) return;

  const currentDataType = isIntradayData(newData) ? 'intraday' : 'history';
  if (lastDataType.value !== null && lastDataType.value !== currentDataType) {
    uplotInstance.value.destroy();
    uplotInstance.value = null;
    lastDataType.value = null;
    initChart();
    lastDataType.value = currentDataType;
  }

  updateColor();
  updateData();
}, { flush: 'post' });

watch(() => props.trend, () => {
  if (uplotInstance.value) {
    updateColor();
  }
});

watch(() => props.baseline, () => {
  if (uplotInstance.value) {
    const data = uplotInstance.value.data;
    if (data && data[0].length > 0) {
      updateYScaleRange(data as [number[], (number | null)[]]);
    }
    uplotInstance.value.redraw();
  }
});

// streaming 模式下的增量追加逻辑
const updateDataStreaming = (validData: { time: string; price?: number; close?: number | null }[]) => {
  // 首次数据（全量构建）
  if (lastDataLen.value === 0 || processedTimestamps.value.length === 0) {
    lastDataLen.value = validData.length;
    rawDataItems.value = [...validData];

    const sortedData = [...validData].sort((a, b) => {
      const tsA = parseTimeToTimestamp(a.time, props.timezone);
      const tsB = parseTimeToTimestamp(b.time, props.timezone);
      return tsA - tsB;
    });

    buildCompressedIntradayData(sortedData);

    const newData: [number[], (number | null)[]] = [processedTimestamps.value, processedValues.value];
    try {
      uplotInstance.value?.setData(newData);
      resetXScale();
      updateYScaleRange(newData);
    } catch (e) {
      console.warn('[FundChart] streaming setData error:', e);
    }
    return;
  }

  // 增量追加：找到新增的数据点
  const prevLen = lastDataLen.value;
  lastDataLen.value = validData.length;

  const newItems = validData.slice(prevLen);
  if (newItems.length === 0) return;

  rawDataItems.value = [...validData];

  // 从已有数据提取 baseDate，保持与 buildCompressedIntradayData 一致
  let baseDate: Date;
  const firstRealTs = realTimestamps.value[0];
  if (firstRealTs != null && firstRealTs > 0) {
    baseDate = new Date(firstRealTs * 1000);
  } else {
    baseDate = new Date();
  }
  baseDate.setHours(0, 0, 0, 0);

  // 处理每个新增点
  for (const item of newItems) {
    const minutes = timeToMinutes(item.time);
    if (minutes < 0) continue;

    const price = 'close' in item ? (item.close ?? item.price) : item.price;
    if (price === undefined) continue;

    const realTs = parseTimeToTimestamp(item.time, props.timezone);

    // 跳过时间相同的重复点
    const lastRealTs = realTimestamps.value[realTimestamps.value.length - 1];
    if (lastRealTs != null && realTs === lastRealTs) continue;

    // 直接使用原始时间戳
    const displayTs = realTs;

    const lastDisplayTs = processedTimestamps.value[processedTimestamps.value.length - 1];

    // 如果时间戳重叠，插入 null 断开
    if (lastDisplayTs != null && displayTs <= lastDisplayTs) {
      processedTimestamps.value.push(lastDisplayTs + 1);
      processedValues.value.push(null);
      realTimestamps.value.push(0);
    }

    processedTimestamps.value.push(displayTs);
    processedValues.value.push(price);
    realTimestamps.value.push(realTs);
  }

  // 如果配置了 maxPoints，超出后丢弃最老的点
  if (props.maxPoints && props.maxPoints > 0) {
    while (processedTimestamps.value.length > props.maxPoints) {
      processedTimestamps.value.shift();
      processedValues.value.shift();
      realTimestamps.value.shift();
    }
  }

  const newData: [number[], (number | null)[]] = [processedTimestamps.value, processedValues.value];
  try {
    // 先设置 X 轴范围，再设置数据
    resetXScale();
    uplotInstance.value?.setData(newData);
  } catch (e) {
    console.warn('[FundChart] streaming setData error:', e);
  }
};

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
  if (uplotInstance.value) {
    uplotInstance.value.destroy();
    uplotInstance.value = null;
  }
});

const handleResize = () => {
  if (uplotInstance.value && chartContainer.value) {
    uplotInstance.value.setSize({
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
