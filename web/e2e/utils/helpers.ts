/**
 * E2E 测试辅助函数
 */

import { Page } from '@playwright/test';

/**
 * 等待页面加载完成
 */
export async function waitForPageLoad(page: Page): Promise<void> {
  await page.waitForLoadState('networkidle');
}

/**
 * 等待元素出现并点击
 */
export async function waitAndClick(
  page: Page,
  selector: string
): Promise<void> {
  await page.waitForSelector(selector, { state: 'visible' });
  await page.click(selector);
}

/**
 * 等待元素出现并获取文本
 */
export async function waitAndGetText(
  page: Page,
  selector: string
): Promise<string> {
  await page.waitForSelector(selector, { state: 'visible' });
  return (await page.textContent(selector)) || '';
}

/**
 * 判断元素是否存在
 */
export async function elementExists(
  page: Page,
  selector: string
): Promise<boolean> {
  try {
    await page.waitForSelector(selector, { timeout: 5000 });
    return true;
  } catch {
    return false;
  }
}

/**
 * 获取元素数量
 */
export async function getElementCount(
  page: Page,
  selector: string
): Promise<number> {
  return await page.locator(selector).count();
}

/**
 * 截图并保存
 */
export async function takeScreenshot(
  page: Page,
  name: string
): Promise<void> {
  await page.screenshot({ path: `screenshots/${name}.png` });
}

/**
 * 模拟视口大小
 */
export async function setViewportSize(
  page: Page,
  width: number,
  height: number
): Promise<void> {
  await page.setViewportSize({ width, height });
}

/**
 * 桌面端视口
 */
export const DESKTOP_VIEWPORT = { width: 1440, height: 900 };

/**
 * 平板端视口
 */
export const TABLET_VIEWPORT = { width: 768, height: 1024 };

/**
 * 移动端视口
 */
export const MOBILE_VIEWPORT = { width: 375, height: 667 };

/**
 * 断点定义（与 CSS 变量一致）
 */
export const BREAKPOINTS = {
  xs: 480,
  sm: 640,
  md: 768,
  lg: 1024,
  xl: 1280,
};

/**
 * 响应式测试辅助
 */
export async function testResponsive(
  page: Page,
  testFn: () => Promise<void>
): Promise<void> {
  // 桌面端
  await setViewportSize(page, DESKTOP_VIEWPORT.width, DESKTOP_VIEWPORT.height);
  await testFn();

  // 平板端
  await setViewportSize(page, TABLET_VIEWPORT.width, TABLET_VIEWPORT.height);
  await testFn();

  // 移动端
  await setViewportSize(page, MOBILE_VIEWPORT.width, MOBILE_VIEWPORT.height);
  await testFn();
}

/**
 * 格式化百分比
 */
export function formatPercent(value: number): string {
  const sign = value >= 0 ? '+' : '';
  return `${sign}${value.toFixed(2)}%`;
}

/**
 * 等待 loading 状态消失
 */
export async function waitForLoadingToFinish(
  page: Page,
  loadingSelector = '.skeleton-card, .loading-state'
): Promise<void> {
  // 等待 loading 元素出现
  const loadingExists = await elementExists(page, loadingSelector);

  if (loadingExists) {
    // 等待 loading 元素消失
    await page.waitForSelector(loadingSelector, { state: 'hidden', timeout: 30000 });
  }
}

/**
 * 等待内容加载
 */
export async function waitForContentLoaded(
  page: Page,
  contentSelector: string
): Promise<void> {
  await page.waitForSelector(contentSelector, { state: 'visible', timeout: 30000 });
}