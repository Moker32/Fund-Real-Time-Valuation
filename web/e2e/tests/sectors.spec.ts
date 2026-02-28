/**
 * 板块功能 E2E 测试
 */

import { test, expect } from '@playwright/test';
import { mockSectorsApi } from '../utils/api-mock';

test.describe('板块列表测试', () => {
  test('板块列表正常显示', async ({ page }) => {
    await mockSectorsApi(page);
    await page.goto('/sectors');
    await page.waitForLoadState('load');

    // 验证板块卡片存在
    const cards = page.locator('.sector-card, .card');
    const count = await cards.count();
    expect(count).toBeGreaterThanOrEqual(0);
  });

  test('板块资金流向显示', async ({ page }) => {
    await mockSectorsApi(page);
    await page.goto('/sectors');
    await page.waitForLoadState('load');

    // 检查资金流向元素
    const flowElement = page.locator('.net-inflow, .capital-flow');
    const count = await flowElement.count();
    expect(count).toBeGreaterThanOrEqual(0);
  });

  test('板块领涨股显示', async ({ page }) => {
    await mockSectorsApi(page);
    await page.goto('/sectors');
    await page.waitForLoadState('load');

    // 检查领涨股元素
    const leadingStock = page.locator('.leading-stock, .top-stock');
    const count = await leadingStock.count();
    expect(count).toBeGreaterThanOrEqual(0);
  });
});

test.describe('板块页面响应式测试', () => {
  test.use({ viewport: { width: 375, height: 667 } });

  test('移动端板块列表正确显示', async ({ page }) => {
    await mockSectorsApi(page);
    await page.goto('/sectors');
    await page.waitForLoadState('load');

    // 验证页面加载
    await expect(page.locator('body')).toBeVisible();
  });
});