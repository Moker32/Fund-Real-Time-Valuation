<template>
  <div class="capital-flow-chart" ref="chartContainer">
    <div v-if="!data || data.length === 0" class="chart-empty">
      <span class="chart-empty-text">暂无资金流向数据</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, computed } from 'vue';
import uPlot from 'uplot';
import 'uplot/dist/uPlot.min.css';
import type { Sector } from '@/types';

interface FlowDataItem {
  name: string;
  mainInflow: number;
  smallInflow: number;
  mediumInflow?: number;
  largeInflow?: number;
  hugeInflow?: number;
}

const props = withDefaults(defineProps<{
  sectors: Sector[];
  height?: number;
  maxItems?: number;
  showDetail?: boolean;
}>(), {
  height: 300,
  maxItems: 20,
  showDetail: false,
});

const chartContainer = ref<Element | null>(null);
let uplotInstance: uPlot | null = null;

// 准备图表数据
const chartData = computed((): FlowDataItem[] => {
  if (!props.sectors || props.sectors.length === 0) return [];

  return props.sectors
    .filter(s => s.mainInflow !== undefined)
    .slice(0, props.maxItems)
    .map(s => ({
      name: s.name,
      mainInflow: s.mainInflow || 0,
      smallInflow: s.smallInflow || 0,
      mediumInflow: (s as any).mediumInflow,
      largeInflow: (s as any).largeInflow,
      hugeInflow: (s as any).hugeInflow,
    }));
});

// 颜色配置
const COLORS = {
  mainInflow: '#ef4444',    // 主力净流入 - 红色
  smallInflow: '#22c55e',   // 小单净流入 - 绿色
  mediumInflow: '#f59e0b',  // 中单 - 橙色
  largeInflow: '#8b5cf6',   // 大单 - 紫色
  hugeInflow: '#06b6d4',    // 超大单 - 青色
  grid: 'rgba(148, 163, 184, 0.1)',
  text: '#64748b',
};

const initChart = () => {
  if (!chartContainer.value) return;

  // 清空容器
  chartContainer.value.innerHTML = '';

  const data = chartData.value;
  if (data.length === 0) return;

  // 准备数据
  const names = data.map(d => d.name);
  const mainFlows = data.map(d => d.mainInflow);
  const smallFlows = data.map(d => d.smallInflow);
  const mediumFlows = data.map(d => d.mediumInflow || 0);
  const largeFlows = data.map(d => d.largeInflow || 0);
  const hugeFlows = data.map(d => d.hugeInflow || 0);

  // 计算Y轴范围
  const allValues = [...mainFlows, ...smallFlows, ...mediumFlows, ...largeFlows, ...hugeFlows];
  const maxValue = Math.max(...allValues.map(Math.abs));
  const yRange = maxValue * 1.1;

  const series: uPlot.Series[] = [
    {
      label: '板块',
      value: (u: uPlot, v: number) => names[v] || '',
    },
  ];

  const bands: uPlot.Band[] = [];

  // 主力净流入
  series.push({
    label: '主力净流入',
    stroke: COLORS.mainInflow,
    fill: COLORS.mainInflow + '40',
    width: 2,
    points: { show: false },
  });

  // 如果显示详细，添加更多系列
  if (props.showDetail) {
    series.push(
      {
        label: '小单净流入',
        stroke: COLORS.smallInflow,
        fill: COLORS.smallInflow + '40',
        width: 2,
        points: { show: false },
      },
      {
        label: '中单',
        stroke: COLORS.mediumInflow,
        fill: COLORS.mediumInflow + '40',
        width: 2,
        points: { show: false },
      },
      {
        label: '大单',
        stroke: COLORS.largeInflow,
        fill: COLORS.largeInflow + '40',
        width: 2,
        points: { show: false },
      },
      {
        label: '超大单',
        stroke: COLORS.hugeInflow,
        fill: COLORS.hugeInflow + '40',
        width: 2,
        points: { show: false },
      }
    );
  }

  uplotInstance = new uPlot({
    width: chartContainer.value.clientWidth,
    height: props.height,
    series,
    bands,
    axes: [
      {
        show: true,
        stroke: COLORS.text,
        grid: { show: false },
        ticks: { show: false },
        values: (u: uPlot, splits: number[]) => {
          return splits.map(i => names[Math.floor(i)] || '');
        },
      },
      {
        show: true,
        stroke: COLORS.text,
        grid: {
          show: true,
          stroke: COLORS.grid,
          width: 1,
        },
        ticks: { show: true, stroke: COLORS.grid },
        values: (u: uPlot, splits: number[]) => {
          return splits.map(v => `${v >= 0 ? '+' : ''}${v.toFixed(1)}亿`);
        },
        range: () => [-yRange, yRange],
      },
    ],
    scales: {
      x: {
        time: false,
        auto: true,
      },
      y: {
        auto: false,
        range: () => [-yRange, yRange],
      },
    },
    cursor: {
      drag: { x: false, y: false },
      show: true,
      focus: { prox: 16 },
      sync: { key: 'capital-flow' },
    },
    legend: {
      show: true,
      live: true,
      marker: {
        width: 12,
        height: 12,
      },
    },
  }, [
    Array.from({ length: data.length }, (_, i) => i),
    mainFlows,
    ...(props.showDetail ? [smallFlows, mediumFlows, largeFlows, hugeFlows] : []),
  ], chartContainer.value);
};

const updateChart = () => {
  if (!uplotInstance) {
    initChart();
    return;
  }

  const data = chartData.value;
  if (data.length === 0) return;

  const names = data.map(d => d.name);
  const mainFlows = data.map(d => d.mainInflow);
  const smallFlows = data.map(d => d.smallInflow);
  const mediumFlows = data.map(d => d.mediumInflow || 0);
  const largeFlows = data.map(d => d.largeInflow || 0);
  const hugeFlows = data.map(d => d.hugeInflow || 0);

  const allValues = [...mainFlows, ...smallFlows, ...mediumFlows, ...largeFlows, ...hugeFlows];
  const maxValue = Math.max(...allValues.map(Math.abs));
  const yRange = maxValue * 1.1;

  uplotInstance.setScale('y', { min: -yRange, max: yRange });
  uplotInstance.setData([
    Array.from({ length: data.length }, (_, i) => i),
    mainFlows,
    ...(props.showDetail ? [smallFlows, mediumFlows, largeFlows, hugeFlows] : []),
  ]);
};

const handleResize = () => {
  if (uplotInstance && chartContainer.value) {
    uplotInstance.setSize({
      width: chartContainer.value.clientWidth,
      height: props.height,
    });
  }
};

// 监听数据变化
watch(() => props.sectors, () => {
  updateChart();
}, { deep: true });

onMounted(() => {
  initChart();
  window.addEventListener('resize', handleResize);
});

onUnmounted(() => {
  window.removeEventListener('resize', handleResize);
  if (uplotInstance) {
    uplotInstance.destroy();
    uplotInstance = null;
  }
});
</script>

<style scoped>
.capital-flow-chart {
  width: 100%;
  min-height: v-bind('props.height + "px"');
  border-radius: 8px;
  overflow: hidden;
  position: relative;
  background: var(--color-bg-card);
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
  background: var(--color-bg-tertiary);
  border-radius: 8px;
}

.chart-empty-text {
  font-size: 14px;
  color: var(--color-text-tertiary);
}

.capital-flow-chart :deep(.uplot) {
  font-family: inherit;
}

.capital-flow-chart :deep(.u-legend) {
  font-size: 12px;
  padding: 8px;
  background: var(--color-bg-card);
  border-radius: 6px;
  border: 1px solid var(--color-border);
}

.capital-flow-chart :deep(.u-legend .u-marker) {
  border-radius: 2px;
}
</style>
