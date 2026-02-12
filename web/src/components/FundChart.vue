<template>
  <div class="fund-chart" ref="chartContainer">
    <div v-if="!data || data.length === 0" class="chart-empty">
      <span class="chart-empty-text">暂无历史数据</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue';
import { createChart, ColorType, CrosshairMode, LineSeries } from 'lightweight-charts';
import type { FundHistory, FundIntraday } from '@/types';

// 类型定义
interface ChartApi {
  addSeries: (seriesType: typeof LineSeries, options: {
    upColor?: string;
    downColor?: string;
    borderVisible?: boolean;
    color?: string;
    lineWidth?: number;
    lineStyle?: number;
  }) => {
    setData: (data: FundHistory[] | { time: string; value: number }[]) => void;
  };
  applyOptions: (options: { width: number }) => void;
  remove: () => void;
}

const props = withDefaults(defineProps<{
  data: FundHistory[] | FundIntraday[];
  height?: number;
  showGrid?: boolean;  // 是否显示网格
  gradientFill?: boolean;  // 是否显示渐变填充
}>(), {
  height: 100,
  showGrid: false,
  gradientFill: true,
});

const chartContainer = ref<Element | null>(null);
let chart: ReturnType<typeof createChart> | null = null;
let series: { setData: (data: FundHistory[] | { time: string; value: number }[]) => void } | null = null;

// 获取涨跌幅颜色
const getTrendColor = (): string => {
  if (props.data.length < 2) return '#22c55e'; // 默认绿色

  const firstValue = 'close' in props.data[0]
    ? props.data[0].close
    : props.data[0].price;
  const lastValue = 'close' in props.data[props.data.length - 1]
    ? props.data[props.data.length - 1].close
    : props.data[props.data.length - 1].price;

  return lastValue >= firstValue ? '#ef4444' : '#22c55e';
};

const initChart = () => {
  if (!chartContainer.value) return;

  const trendColor = getTrendColor();

  chart = createChart(chartContainer.value, {
    width: chartContainer.value.clientWidth,
    height: props.height,
    layout: {
      background: { type: ColorType.Solid, color: 'transparent' },
      textColor: '#9ca3af',
    },
    // iOS 风格：隐藏网格
    grid: {
      vertLines: { visible: props.showGrid },
      horzLines: { visible: props.showGrid, color: '#f3f4f6' },
    },
    // 隐藏坐标轴
    timeScale: {
      visible: false,
      borderVisible: false,
    },
    rightPriceScale: {
      visible: false,
      borderVisible: false,
    },
    // 简化 crosshair - iOS 风格
    crosshair: {
      mode: CrosshairMode.Normal,
      vertLine: {
        width: 1,
        color: '#e5e7eb',
        style: 2,
        // 不显示圆点，只显示线
        drawCrosshairMarker: false,
      },
      horzLine: {
        visible: false,  // iOS 风格隐藏水平线
        width: 0,
      },
    },
    // 禁用交互 - iOS 风格主要是展示
    handleScroll: false,
    handleScale: false,
    // 禁用右侧价格刻度
    scaleMargins: {
      top: 0,
      bottom: 0,
    },
  });

  // iOS 风格折线图
  series = chart.addSeries(LineSeries, {
    color: trendColor,
    lineWidth: 2,
    lineStyle: 0,
    // 顶部圆点（可选）
    crosshairMarker: {
      size: 6,  // iOS 风格小圆点
      backgroundColor: trendColor,
      borderColor: '#ffffff',
      borderSize: 2,
      radius: 6,
    },
  });

  if (props.data.length > 0) {
    updateData();
  }

  // iOS 风格：显示渐变填充（线条下方）
  if (props.gradientFill) {
    // 创建渐变
    const isRising = trendColor === '#ef4444';
    const gradientStart = isRising ? 'rgba(239, 68, 68, 0.3)' : 'rgba(34, 197, 94, 0.3)';
    const gradientEnd = isRising ? 'rgba(239, 68, 68, 0.0)' : 'rgba(34, 197, 94, 0.0)';

    chart.applyOptions({
      rightPriceScale: {
        visible: false,
      },
    });

    // 注意：lightweight-charts v5 需要通过 AreaSeries 实现渐变填充
    // LineSeries 不支持渐变，这里保持简洁线条
  }
};

const updateData = () => {
  if (!series || !props.data || props.data.length === 0) return;

  const lineData = props.data.map((item) => {
    if ('close' in item) {
      return { time: item.time, value: item.close };
    } else {
      // FundIntraday 格式
      const timeStr = item.time;
      const match = timeStr.match(/(\d{4})-(\d{2})-(\d{2})[T\s](\d{2}):(\d{2})/);
      if (match) {
        return {
          time: {
            year: parseInt(match[1]),
            month: parseInt(match[2]),
            day: parseInt(match[3]),
            hour: parseInt(match[4]),
            minute: parseInt(match[5]),
          },
          value: item.price,
        };
      }
      return { time: timeStr.split(' ')[0], value: item.price };
    }
  });

  series.setData(lineData as { time: string | { year: number; month: number; day: number; hour?: number; minute?: number; }; value: number }[]);
};

watch(() => props.data, updateData, { deep: true });

// 监听颜色变化
watch(() => props.data, () => {
  if (chart && props.data.length >= 2) {
    const newColor = getTrendColor();
    series && 'applyOptions' in series && series.applyOptions({ color: newColor });
  }
}, { deep: true });

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

/* iOS 风格：简洁背景 */
.fund-chart :deep(canvas) {
  /* 移除不必要的阴影 */
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
