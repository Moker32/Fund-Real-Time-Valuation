<template>
  <div class="fund-chart" ref="chartContainer">
    <div v-if="!data || data.length === 0" class="chart-empty">
      <span class="chart-empty-text">暂无历史数据</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue';
import { createChart, ColorType, CrosshairMode } from 'lightweight-charts';
import type { FundHistory } from '@/types';

// 类型定义
interface ChartApi {
  addCandlestickSeries: (options: {
    upColor: string;
    downColor: string;
    borderVisible: boolean;
    wickUpColor: string;
    wickDownColor: string;
  }) => {
    setData: (data: FundHistory[]) => void;
  };
  applyOptions: (options: { width: number }) => void;
  remove: () => void;
  getSeries: () => {
    setData: (data: FundHistory[]) => void;
  } | null;
}

const props = withDefaults(defineProps<{
  data: FundHistory[];
  height?: number;
}>(), {
  height: 100,
});

const chartContainer = ref<Element | null>(null);
let chart: ChartApi | null = null;
let candleSeries: { setData: (data: FundHistory[]) => void } | null = null;

const initChart = () => {
  if (!chartContainer.value) return;

  chart = createChart(chartContainer.value, {
    width: chartContainer.value.clientWidth,
    height: props.height,
    layout: {
      background: { type: ColorType.Solid, color: 'transparent' },
      textColor: '#9ca3af',
    },
    grid: {
      vertLines: { visible: false },
      horzLines: { color: '#f3f4f6' },
    },
    timeScale: {
      visible: false,
      borderVisible: false,
    },
    rightPriceScale: {
      visible: false,
      borderVisible: false,
    },
    crosshair: {
      mode: CrosshairMode.Normal,
      vertLine: {
        width: 1,
        color: '#e5e7eb',
        style: 2,
      },
      horzLine: {
        width: 1,
        color: '#e5e7eb',
        style: 2,
      },
    },
    handleScroll: false,
    handleScale: false,
  });

  candleSeries = chart.addCandlestickSeries({
    upColor: '#ef4444',
    downColor: '#22c55e',
    borderVisible: false,
    wickUpColor: '#ef4444',
    wickDownColor: '#22c55e',
  });

  if (props.data.length > 0) {
    candleSeries.setData(props.data);
  }
};

const updateData = () => {
  if (!candleSeries || !props.data || props.data.length === 0) return;
  candleSeries.setData(props.data);
};

watch(() => props.data, updateData, { deep: true });

onMounted(() => {
  initChart();
  window.addEventListener('resize', handleResize);
});

onUnmounted(() => {
  window.removeEventListener('resize', handleResize);
  if (chart) {
    chart.remove();
    chart = null;
  }
});

const handleResize = () => {
  if (chart && chartContainer.value) {
    chart.applyOptions({ width: chartContainer.value.clientWidth });
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
