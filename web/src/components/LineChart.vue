<template>
  <div class="fund-chart" ref="chartContainer">
    <div v-if="!hasData" class="chart-empty">
      <span class="chart-empty-text">暂无数据</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, computed } from 'vue';
import uPlot from 'uplot';
import 'uplot/dist/uPlot.min.css';
import type { FundHistory, FundIntraday } from '@/types';

// 扩展 uPlot 接口以支持自定义属性
interface uPlotWithBaseline extends uPlot {
  _baselineColor?: string;
}

const props = withDefaults(defineProps<{
  data: FundHistory[] | FundIntraday[];
  height?: number;
  baseline?: number;
  trend?: 'rising' | 'falling' | 'neutral';
}>(), {
  height: 100,
  trend: 'neutral',
});

const chartContainer = ref<Element | null>(null);
let uplotInstance: uPlot | null = null;

// 响应式获取趋势颜色 - 当数据变化时自动重新计算
const color = computed(() => getTrendColor());

// 判断是否有有效数据用于显示空状态
// eslint-disable-next-line no-useless-assignment
const hasData = computed(() => {
  // 如果没有图表实例且没有数据，显示空状态
  if (!uplotInstance && (!props.data || props.data.length === 0)) return false;
  // 其他情况（图表已初始化，或者正在等待数据）
  return true;
});

// 缓存上次数据，用于比较
let lastDataJson: string = '';

const getTrendColor = (): string => {
  // 优先使用传入的 trend 属性
  if (props.trend === 'rising') return '#ef4444';
  if (props.trend === 'falling') return '#22c55e';
  return '#71717a';
};

// 解析时间字符串为秒级 Unix 时间戳
// 支持格式: "YYYY-MM-DD", "YYYY-MM-DD HH:mm:ss", "HH:mm"
const parseTimeToTimestamp = (timeStr: string): number => {
  // 格式: "HH:mm" (日内分时数据，如 "14:30")
  const timeOnlyMatch = timeStr.match(/^(\d{1,2}):(\d{2})$/);
  if (timeOnlyMatch) {
    const hour = parseInt(timeOnlyMatch[1], 10);
    const minute = parseInt(timeOnlyMatch[2], 10);
    const now = new Date();
    return Math.floor(new Date(now.getFullYear(), now.getMonth(), now.getDate(), hour, minute, 0).getTime() / 1000);
  }

  // 格式: "YYYY-MM-DD" 或 "YYYY-MM-DD HH:mm:ss" 或 ISO 格式
  const date = new Date(timeStr);
  if (!isNaN(date.getTime())) {
    return Math.floor(date.getTime() / 1000);
  }

  // 尝试解析其他格式
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

  // 返回当前时间戳作为回退
  return Math.floor(Date.now() / 1000);
};

// 判断是否为日内分时数据 (FundIntraday)
// FundIntraday 有 price 字段，FundHistory 有 close 字段
const isIntradayData = (data: FundHistory[] | FundIntraday[]): boolean => {
  if (!data || data.length === 0) return false;
  const firstItem = data[0];
  return 'price' in firstItem && !('close' in firstItem);
};

// 计算日内分时数据的x轴范围
// 根据数据自动适应X轴范围，不再固定为A股时间
const getIntradayXRange = (data: FundHistory[] | FundIntraday[]): { min: number; max: number } | null => {
  if (!isIntradayData(data) || data.length === 0) return null;

  // 从数据中提取时间戳
  const timestamps: number[] = [];
  for (const item of data) {
    if (item && item.time) {
      const ts = parseTimeToTimestamp(item.time);
      timestamps.push(ts);
    }
  }

  if (timestamps.length === 0) return null;

  // 根据实际数据范围设置X轴，添加少量边距
  const minTs = Math.min(...timestamps);
  const maxTs = Math.max(...timestamps);
  
  // 添加5分钟的边距
  const padding = 5 * 60;
  
  return { min: minTs - padding, max: maxTs + padding };
};

// 计算 Y 轴范围，确保始终包含 baseline 值
const getYScaleRange = (data: [number[], number[]] | null, baseline: number | undefined): { min: number; max: number } | undefined => {
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

  // 添加 2% 边距
  const padding = (max - min) * 0.02;
  min -= padding;
  max += padding;

  // 确保 baseline 包含在范围内
  if (baseline !== undefined && baseline > 0) {
    min = Math.min(min, baseline);
    max = Math.max(max, baseline);
  }

  return { min, max };
};

const initChart = () => {
  if (!chartContainer.value) return;

  if (uplotInstance) return;
  
  chartContainer.value.innerHTML = '';

  // 计算日内分时数据的x轴范围 (09:30 - 15:00)
  const xRange = getIntradayXRange(props.data);

  try {
    uplotInstance = new uPlot({
      width: chartContainer.value.clientWidth || 300,
      height: props.height,
      legend: {
        show: false,
      },
      series: [
        {},
        {
          stroke: color.value,
          width: 2,
          fill: undefined,
          points: { show: false },
          spanGaps: false,
        },
      ],
      axes: [
        { show: false },
        { show: false },
      ],
      scales: {
        x: {
          time: true,
          ...(xRange && { min: xRange.min, max: xRange.max }),
        },
        y: {
          auto: true,
        },
      },
      cursor: {
        drag: { x: false, y: false },
        show: false,
      },
      hooks: {
        draw: [
          (u: uPlot) => {
            if (props.baseline === undefined) return;
            const baseline = props.baseline;
            const yScale = u.scales.y;
            if (!yScale) return;

            // 计算基准线在图表中的 Y 坐标
            const yPos = u.valToPos(baseline, 'y', true);
            if (yPos < 0 || yPos > u.bbox.height) return; // 如果在图表外则不绘制

            const ctx = u.ctx;
            ctx.save();
            // 优先使用存储的基准线颜色，否则回退到动态获取
            const uWithBaseline = u as uPlotWithBaseline;
            ctx.strokeStyle = uWithBaseline._baselineColor ?? getTrendColor();
            ctx.lineWidth = 1;
            ctx.setLineDash([4, 4]); // 虚线
            ctx.beginPath();
            ctx.moveTo(0, yPos);
            ctx.lineTo(u.bbox.width, yPos);
            ctx.stroke();
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

  // 过滤无效数据
  const validData = props.data.filter((item): item is { time: string; price: number; close?: number } => {
    if (!item) return false;
    const price = 'close' in item ? item.close : item.price;
    return typeof price === 'number' && typeof item.time === 'string' && item.time.length > 0;
  });

  if (validData.length === 0) return;

  // 比较数据是否变化
  const currentDataJson = JSON.stringify(validData.map(d => d.time + (d.close ?? d.price)));
  if (currentDataJson === lastDataJson) return;
  lastDataJson = currentDataJson;

  // 构建 uPlot 数据格式: [timestamps, values]
  const timestamps: number[] = [];
  const values: number[] = [];

  for (const item of validData) {
    const ts = parseTimeToTimestamp(item.time);
    const price = 'close' in item ? (item.close ?? item.price) : item.price;
    if (price !== undefined) {
      timestamps.push(ts);
      values.push(price);
    }
  }

  // 按时间排序并检测午间休市断点
  // 原始数据格式: "HH:mm" (如 "09:30", "13:00")
  const sortedData = [...validData].sort((a, b) => {
    const tsA = parseTimeToTimestamp(a.time);
    const tsB = parseTimeToTimestamp(b.time);
    return tsA - tsB;
  });

  const sortedTimestamps: number[] = [];
  const sortedValues: number[] = [];

  // 获取当前时间和市场结束时间
  const now = new Date();
  const currentHour = now.getHours();
  const currentMinute = now.getMinutes();
  const currentTimeInMinutes = currentHour * 60 + currentMinute;

  // 检测午间休市断点 (A股: 11:30-13:00 休市)
  let prevHour = -1;
  for (const item of sortedData) {
    const ts = parseTimeToTimestamp(item.time);
    const price = 'close' in item ? (item.close ?? item.price) : item.price;
    if (price === undefined) continue;

    // 从时间字符串提取小时
    const hourMatch = item.time.match(/^(\d{1,2}):/);
    const hour = hourMatch ? parseInt(hourMatch[1], 10) : -1;

    // 如果从上午跳到下午 (hour < 11:59 -> hour >= 13)，插入 null 断点
    if (prevHour >= 0 && prevHour <= 11 && hour >= 13) {
      sortedTimestamps.push(ts - 60); // 提前1分钟作为断点
      sortedValues.push(null);
    }

    sortedTimestamps.push(ts);
    sortedValues.push(price);
    prevHour = hour;
  }

  // 如果当前时间在交易时间内（09:30-15:00），在最后一个数据点之后插入 null 断点
  // 这样线条不会拉伸到 15:00
  const lastTs = sortedTimestamps[sortedTimestamps.length - 1];
  const marketEndInMinutes = 15 * 60; // 15:00
  const marketStartInMinutes = 9 * 60 + 30; // 09:30

  if (lastTs && currentTimeInMinutes > marketStartInMinutes && currentTimeInMinutes < marketEndInMinutes) {
    // 计算市场结束时间戳
    const year = now.getFullYear();
    const month = now.getMonth();
    const day = now.getDate();
    const marketEndTs = Math.floor(new Date(year, month, day, 15, 0, 0).getTime() / 1000);

    // 插入断点在最后一个数据点之后
    sortedTimestamps.push(lastTs + 60); // 延后1分钟
    sortedValues.push(null);

    // 延后到市场结束时间（作为占位，保持轴范围）
    sortedTimestamps.push(marketEndTs);
    sortedValues.push(null);
  }

  const newData: [number[], number[]] = [sortedTimestamps, sortedValues];

  try {
    uplotInstance.setData(newData);
    // 更新 Y 轴范围，确保包含 baseline
    updateYScaleRange(newData);
  } catch (e) {
    console.warn('[FundChart] setData error:', e);
  }
};

// 更新 Y 轴范围，确保始终包含 baseline
const updateYScaleRange = (data: [number[], number[]]) => {
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
    // uPlot setSeries API requires series options
    uplotInstance.setSeries(1, { stroke: newColor });
    // 存储基准线颜色并强制重绘，以更新基准线颜色
    (uplotInstance as uPlotWithBaseline)._baselineColor = newColor;
    uplotInstance.redraw();
  } catch (e) {
    console.warn('[FundChart] updateColor error:', e);
  }
};

// 缓存数据类型，用于检测变化
let lastDataType: 'history' | 'intraday' | null = null;

// 监听数据变化
watch(() => props.data, (newData) => {
  // 如果没有图表实例但有数据，先初始化图表
  if (!uplotInstance && chartContainer.value && newData && newData.length > 0) {
    initChart();
    // 记录初始数据类型
    lastDataType = isIntradayData(newData) ? 'intraday' : 'history';
  }

  if (!uplotInstance) return;

  if (!newData || newData.length === 0) return;

  // 检测数据类型是否变化，如果变化则需要重新初始化图表
  const currentDataType = isIntradayData(newData) ? 'intraday' : 'history';
  if (lastDataType !== null && lastDataType !== currentDataType) {
    // 数据类型变化，销毁并重新创建图表
    uplotInstance.destroy();
    uplotInstance = null;
    lastDataType = null;
    initChart();
    lastDataType = currentDataType;
  }

  // 更新颜色
  updateColor();

  // 更新数据
  updateData();
}, { deep: true, flush: 'post' });

// 监听 trend 变化以更新颜色
watch(() => props.trend, () => {
  if (uplotInstance) {
    updateColor();
  }
});

// 监听 baseline 变化以重绘基准线并更新 Y 轴范围
watch(() => props.baseline, () => {
  if (uplotInstance) {
    // 获取当前数据并更新 Y 轴范围
    const data = uplotInstance.data;
    if (data && data[0].length > 0) {
      updateYScaleRange(data as [number[], number[]]);
    }
    uplotInstance.redraw();
  }
});

onMounted(() => {
  // 如果挂载时数据已存在，先初始化图表再更新数据
  if (props.data && props.data.length > 0) {
    initChart();
    updateColor(); // 确保初始化时颜色和基准线都正确
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
  cursor: default !important;
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
