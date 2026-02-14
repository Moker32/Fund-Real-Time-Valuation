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

/**
 * 格式化数据时间为友好的显示格式
 * 今日数据显示 "今日 HH:mm"，历史数据显示 "MM-DD HH:mm"
 * @param date Date 对象或 ISO 字符串
 * @returns 格式化的时间字符串
 */
export function formatDataTime(date: Date | string): string {
  const d = typeof date === 'string' ? new Date(date) : date;
  const now = new Date();
  
  // 转换为上海时区的日期
  const shanghaiTime = new Date(d.toLocaleString('en-US', { timeZone: 'Asia/Shanghai' }));
  const today = new Date(now.toLocaleString('en-US', { timeZone: 'Asia/Shanghai' }));
  
  const dataDate = new Date(shanghaiTime.getFullYear(), shanghaiTime.getMonth(), shanghaiTime.getDate());
  const todayDate = new Date(today.getFullYear(), today.getMonth(), today.getDate());
  
  const timeStr = shanghaiTime.toLocaleTimeString('zh-CN', {
    timeZone: 'Asia/Shanghai',
    hour12: false,
    hour: '2-digit',
    minute: '2-digit',
  });
  
  const diffDays = Math.floor((todayDate.getTime() - dataDate.getTime()) / (1000 * 60 * 60 * 24));
  
  if (diffDays === 0) {
    return `今日 ${timeStr}`;
  } else if (diffDays === 1) {
    return `昨日 ${timeStr}`;
  } else {
    return `${shanghaiTime.getMonth() + 1}-${shanghaiTime.getDate()} ${timeStr}`;
  }
}

/**
 * 格式化数据日期
 * 数据是哪天的就显示哪天
 * 如果是今天显示 "今日"，否则显示日期如 "02-13"
 * @param date Date 对象或 ISO 字符串
 * @returns 格式化的时间字符串
 */
export function formatDataDate(date: Date | string): string {
  const d = typeof date === 'string' ? new Date(date) : date;
  const now = new Date();
  
  // 转换为上海时区
  const shanghaiTime = new Date(d.toLocaleString('en-US', { timeZone: 'Asia/Shanghai' }));
  const today = new Date(now.toLocaleString('en-US', { timeZone: 'Asia/Shanghai' }));
  
  // 比较日期（只比较年月日）
  const dataDate = new Date(shanghaiTime.getFullYear(), shanghaiTime.getMonth(), shanghaiTime.getDate());
  const todayDate = new Date(today.getFullYear(), today.getMonth(), today.getDate());
  
  if (dataDate.getTime() === todayDate.getTime()) {
    return '今日';
  }
  
  // 否则显示日期
  const month = shanghaiTime.getMonth() + 1;
  const day = shanghaiTime.getDate();
  return `${month.toString().padStart(2, '0')}-${day.toString().padStart(2, '0')}`;
}
