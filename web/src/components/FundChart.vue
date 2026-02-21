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

const props = withDefaults(defineProps<{
  data: FundHistory[] | FundIntraday[];
  height?: number;
}>(), {
  height: 100,
});

const chartContainer = ref<Element | null>(null);
let uplotInstance: uPlot | null = null;

// 判断是否有有效数据用于显示空状态
const hasData = computed(() => {
  // 如果没有图表实例且没有数据，显示空状态
  if (!uplotInstance && (!props.data || props.data.length === 0)) return false;
  // 其他情况（图表已初始化，或者正在等待数据）
  return true;
});

// 缓存上次数据，用于比较
let lastDataJson: string = '';

const getTrendColor = (): string => {
  if (!props.data || props.data.length < 2) return '#22c55e';

  const firstValue = 'close' in props.data[0]
    ? props.data[0].close
    : props.data[0].price;
  const lastValue = 'close' in props.data[props.data.length - 1]
    ? props.data[props.data.length - 1].close
    : props.data[props.data.length - 1].price;

  // 数值无效时默认绿色
  if (typeof firstValue !== 'number' || typeof lastValue !== 'number') {
    return '#22c55e';
  }

  return lastValue >= firstValue ? '#ef4444' : '#22c55e';
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

const initChart = () => {
  if (!chartContainer.value) return;

  if (uplotInstance) return;
  
  chartContainer.value.innerHTML = '';

  const color = getTrendColor();

  try {
    uplotInstance = new uPlot({
      width: chartContainer.value.clientWidth || 300,
      height: props.height,
      series: [
        {
          label: '时间',
        },
        {
          label: '价格',
          stroke: color,
          width: 2,
          fill: undefined,
          points: { show: false },
        },
      ],
      axes: [
        { show: false },
        { show: false },
      ],
      scales: {
        x: {
          time: true,
        },
        y: {
          auto: true,
        },
      },
      cursor: {
        drag: { x: false, y: false },
        show: false,
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

  // 按时间排序
  const sortedIndices = timestamps.map((ts, i) => ({ ts, i })).sort((a, b) => a.ts - b.ts);
  const sortedTimestamps: number[] = [];
  const sortedValues: number[] = [];

  for (const { ts, i } of sortedIndices) {
    const val = values[i];
    if (val !== undefined) {
      sortedTimestamps.push(ts);
      sortedValues.push(val);
    }
  }

  const newData: [number[], number[]] = [sortedTimestamps, sortedValues];

  try {
    uplotInstance.setData(newData);
  } catch (e) {
    console.warn('[FundChart] setData error:', e);
  }
};

const updateColor = () => {
  if (!uplotInstance) return;

  const newColor = getTrendColor();
  try {
    // uPlot setSeries API requires series options
    uplotInstance.setSeries(1, { stroke: newColor });
  } catch {
    // 忽略颜色更新错误
  }
};

// 监听数据变化
watch(() => props.data, (newData) => {
  // 如果图表未初始化但有数据，先初始化图表
  if (!uplotInstance && chartContainer.value && newData && newData.length > 0) {
    initChart();
  }

  if (!uplotInstance) return;

  if (!newData || newData.length === 0) return;

  // 更新颜色
  if (newData.length >= 2) {
    updateColor();
  }

  // 更新数据
  updateData();
}, { deep: true, flush: 'post' });

onMounted(() => {
  // 如果挂载时数据已存在，先初始化图表再更新数据
  if (props.data && props.data.length > 0) {
    initChart();
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
