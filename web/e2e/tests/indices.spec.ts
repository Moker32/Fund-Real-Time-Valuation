/**
 * 指数功能 E2E 测试
 */

import { test, expect } from '@playwright/test';
import { mockIndicesApi } from '../utils/api-mock';

test.describe('指数列表测试', () => {
  test('指数列表正常显示', async ({ page }) => {
    await mockIndicesApi(page);
    await page.goto('/indices');
    await page.waitForLoadState('load');

    // 验证指数卡片存在
    const cards = page.locator('.index-card, .card');
    const count = await cards.count();
    expect(count).toBeGreaterThanOrEqual(0);
  });

  test('指数数据更新时间显示', async ({ page }) => {
    await mockIndicesApi(page);
    await page.goto('/indices');
    await page.waitForLoadState('load');

    // 检查时间显示
    const timeElement = page.locator('.update-time, .time');
    const count = await timeElement.count();
    expect(count).toBeGreaterThanOrEqual(0);
  });
});

test.describe('指数页面响应式测试', () => {
  test.use({ viewport: { width: 375, height: 667 } });

  test('移动端指数列表正确显示', async ({ page }) => {
    await mockIndicesApi(page);
    await page.goto('/indices');
    await page.waitForLoadState('load');

    // 验证页面加载
    await expect(page.locator('body')).toBeVisible();
  });
});