/**
 * 统一时间格式化工具
 * 统一使用 Asia/Shanghai 时区
 */

// 上海时区
const TIMEZONE = 'Asia/Shanghai';

/**
 * 格式化时间为中文格式（显示用）
 * @param date Date 对象或 ISO 字符串
 * @returns 格式化的中文时间字符串，如 "21:44:44"
 */
export function formatTime(date: Date | string): string {
  const d = typeof date === 'string' ? new Date(date) : date;
  return d.toLocaleTimeString('zh-CN', {
    timeZone: TIMEZONE,
    hour12: false,
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
}

/**
 * 格式化为日期时间中文格式
 * @param date Date 对象或 ISO 字符串
 * @returns 格式化的中文日期时间字符串，如 "2026-02-12 21:44:44"
 */
export function formatDateTime(date: Date | string): string {
  const d = typeof date === 'string' ? new Date(date) : date;
  return d.toLocaleString('zh-CN', {
    timeZone: TIMEZONE,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
}

/**
 * 格式化为纯日期中文格式
 * @param date Date 对象或 ISO 字符串
 * @returns 格式化的中文日期字符串，如 "2026-02-12"
 */
export function formatDate(date: Date | string): string {
  const d = typeof date === 'string' ? new Date(date) : date;
  return d.toLocaleDateString('zh-CN', {
    timeZone: TIMEZONE,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  });
}

/**
 * 获取当前时间的格式化字符串
 * @param type 时间格式类型
 * @returns 格式化的时间字符串
 */
export function getCurrentTime(type: 'time' | 'date' | 'datetime' = 'time'): string {
  const now = new Date();
  switch (type) {
    case 'date':
      return formatDate(now);
    case 'datetime':
      return formatDateTime(now);
    default:
      return formatTime(now);
  }
}
