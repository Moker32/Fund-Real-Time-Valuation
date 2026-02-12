<template>
  <div class="fund-chart" ref="chartContainer">
    <div v-if="!data || data.length === 0" class="chart-empty">
      <span class="chart-empty-text">暂无数据</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue';
import { createChart, ColorType, CrosshairMode, LineSeries } from 'lightweight-charts';
import type { FundHistory, FundIntraday } from '@/types';

const props = withDefaults(defineProps<{
  data: FundHistory[] | FundIntraday[];
  height?: number;
}>(), {
  height: 100,
});

const chartContainer = ref<Element | null>(null);
let chart: ReturnType<typeof createChart> | null = null;
let series: {
  setData: (data: FundHistory[] | { time: string; value: number }[]) => void;
  applyOptions: (opts: { color: string }) => void;
} | null = null;

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

const initChart = () => {
  if (!chartContainer.value) return;

  // 清空容器
  chartContainer.value.innerHTML = '';

  chart = createChart(chartContainer.value, {
    width: chartContainer.value.clientWidth,
    height: props.height,
    layout: {
      background: { type: ColorType.Solid, color: 'transparent' },
      textColor: '#9ca3af',
    },
    grid: {
      vertLines: { visible: false },
      horzLines: { visible: false },
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
        drawCrosshairMarker: false,
      },
      horzLine: {
        visible: false,
        width: 0,
      },
    },
    handleScroll: false,
    handleScale: false,
    scaleMargins: {
      top: 0,
      bottom: 0,
    },
    // 禁用所有插件，防止水印
    plugins: [],
  });

  // 先添加 series
  series = chart.addSeries(LineSeries, {
    color: getTrendColor(),
    lineWidth: 2,
    lineStyle: 0,
    crosshairMarker: {
      size: 0, // 隐藏十字星标记
    },
  });

  // 确保图表创建完成后再设置数据
  setTimeout(() => {
    if (props.data && props.data.length > 0) {
      updateData();
    }
  }, 0);
};

const updateData = () => {
  if (!series || !props.data || props.data.length === 0) return;

  // 过滤无效数据
  const validData = props.data.filter((item): item is { time: string; price: number } => {
    if (!item) return false;
    const price = 'close' in item ? item.close : item.price;
    return typeof price === 'number' && typeof item.time === 'string' && item.time.length > 0;
  });

  if (validData.length === 0) return;

  // 比较数据是否变化
  const currentDataJson = JSON.stringify(validData.map(d => d.time + d.price));
  if (currentDataJson === lastDataJson) return;
  lastDataJson = currentDataJson;

  const lineData = validData.map((item) => {
    if ('close' in item) {
      return { time: item.time, value: item.close };
    } else {
      const timeStr = item.time;
      // 解析时间格式
      const match = timeStr.match(/^(\d{4})-(\d{2})-(\d{2})(?:[T\s](\d{2}):(\d{2}))?$/);
      if (match && match[4]) {
        return {
          time: {
            year: parseInt(match[1], 10),
            month: parseInt(match[2], 10),
            day: parseInt(match[3], 10),
            hour: parseInt(match[4], 10),
            minute: parseInt(match[5], 10),
          },
          value: item.price,
        };
      }
      return { time: timeStr.split(' ')[0], value: item.price };
    }
  });

  try {
    series.setData(lineData as { time: string | { year: number; month: number; day: number; hour?: number; minute?: number; }; value: number }[]);
  } catch (e) {
    console.warn('[FundChart] setData error:', e);
  }
};

// 合并为一个 watch，避免竞态
watch(() => props.data, (newData) => {
  if (!newData || newData.length === 0) return;

  // 更新颜色
  if (newData.length >= 2 && series) {
    const newColor = getTrendColor();
    try {
      series.applyOptions({ color: newColor });
    } catch (e) {
      // 忽略颜色更新错误
    }
  }

  // 更新数据
  updateData();
}, { deep: true, flush: 'post' });

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
  series = null;
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

.fund-chart :deep(canvas) {
  filter: none !important;
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
