import { ref, watch, type Ref } from 'vue';

interface CountUpOptions {
  duration?: number; // 动画持续时间（毫秒）
  delay?: number; // 延迟开始时间（毫秒）
  decimals?: number; // 小数位数
  easing?: (t: number) => number; // 缓动函数
}

// 默认缓动函数：easeOutQuart
const defaultEasing = (t: number): number => {
  return 1 - Math.pow(1 - t, 4);
};

/**
 * 数字计数动画 composable
 * @param targetValue 目标值（响应式引用）
 * @param options 配置选项
 * @returns 当前显示值的响应式引用
 */
export function useCountUp(
  targetValue: Ref<number>,
  options: CountUpOptions = {}
): Ref<number> {
  const {
    duration = 1500,
    delay = 0,
    decimals = 0,
    easing = defaultEasing,
  } = options;

  const displayValue = ref(0);
  let animationFrameId: number | null = null;
  let startTime: number | null = null;
  let startValue = 0;

  const animate = (timestamp: number) => {
    if (startTime === null) {
      startTime = timestamp;
    }

    const elapsed = timestamp - startTime;

    if (elapsed < delay) {
      animationFrameId = requestAnimationFrame(animate);
      return;
    }

    const progress = Math.min((elapsed - delay) / duration, 1);
    const easedProgress = easing(progress);

    const currentValue = startValue + (targetValue.value - startValue) * easedProgress;
    displayValue.value = Number(currentValue.toFixed(decimals));

    if (progress < 1) {
      animationFrameId = requestAnimationFrame(animate);
    } else {
      displayValue.value = targetValue.value;
    }
  };

  const startAnimation = () => {
    if (animationFrameId !== null) {
      cancelAnimationFrame(animationFrameId);
    }
    startTime = null;
    startValue = displayValue.value;
    animationFrameId = requestAnimationFrame(animate);
  };

  // 监听目标值变化，重新触发动画
  watch(
    targetValue,
    () => {
      startAnimation();
    },
    { immediate: true }
  );

  return displayValue;
}

/**
 * 批量数字计数动画 composable
 * @param targetValues 目标值数组（响应式引用）
 * @param options 配置选项
 * @returns 当前显示值数组的响应式引用
 */
export function useCountUpBatch(
  targetValues: Ref<number[]>,
  options: CountUpOptions & { staggerDelay?: number } = {}
): Ref<number[]> {
  const { staggerDelay = 100, ...countUpOptions } = options;
  const displayValues = ref<number[]>(targetValues.value.map(() => 0));

  watch(
    targetValues,
    (newValues) => {
      newValues.forEach((value, index) => {
        setTimeout(() => {
          const singleTarget = ref(value);
          const animatedValue = useCountUp(singleTarget, {
            ...countUpOptions,
            delay: 0,
          });

          watch(animatedValue, (newVal) => {
            displayValues.value[index] = newVal;
          });
        }, index * staggerDelay);
      });
    },
    { immediate: true }
  );

  return displayValues;
}
