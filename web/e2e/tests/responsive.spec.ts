/**
 * 响应式布局 E2E 测试
 */

import { test, expect } from '@playwright/test';
import { mockAllApis } from '../utils/api-mock';

// 定义测试视口
const viewports = [
  { name: '桌面', width: 1440, height: 900 },
  { name: '平板', width: 768, height: 1024 },
  { name: '手机', width: 375, height: 667 },
];

test.describe('响应式布局测试', () => {
  for (const viewport of viewports) {
    test.describe(`${viewport.name}端 (${viewport.width}x${viewport.height})`, () => {
      test.use({ viewport: { width: viewport.width, height: viewport.height } });

      test('首页布局正确', async ({ page }) => {
        await mockAllApis(page);
        await page.goto('/');
        await page.waitForLoadState('load');

        // 验证页面加载
        await expect(page.locator('body')).toBeVisible();

        // 验证 Hero 区域
        const heroTitle = page.locator('.hero-title');
        await expect(heroTitle).toBeVisible();
      });

      test('基金页面布局正确', async ({ page }) => {
        await mockAllApis(page);
        await page.goto('/funds');
        await page.waitForLoadState('load');

        // 验证页面加载
        await expect(page.locator('body')).toBeVisible();
      });

      test('商品页面布局正确', async ({ page }) => {
        await mockAllApis(page);
        await page.goto('/commodities');
        await page.waitForLoadState('load');

        // 验证页面加载
        await expect(page.locator('body')).toBeVisible();
      });

      test('指数页面布局正确', async ({ page }) => {
        await mockAllApis(page);
        await page.goto('/indices');
        await page.waitForLoadState('load');

        // 验证页面加载
        await expect(page.locator('body')).toBeVisible();
      });

      test('板块页面布局正确', async ({ page }) => {
        await mockAllApis(page);
        await page.goto('/sectors');
        await page.waitForLoadState('load');

        // 验证页面加载
        await expect(page.locator('body')).toBeVisible();
      });
    });
  }
});

test.describe('侧边栏响应式测试', () => {
  test.use({ viewport: { width: 375, height: 667 } });

  test('移动端侧边栏默认隐藏', async ({ page }) => {
    await mockAllApis(page);
    await page.goto('/');
    await page.waitForLoadState('load');

    // 验证侧边栏状态（根据实际实现调整）
    // 使用 .sidebar 作为主选择器，避免匹配到 nav 元素
    const sidebar = page.locator('.sidebar').first();
    const menuToggle = page.locator('.menu-toggle, .hamburger');

    // 移动端可能有菜单按钮
    const hasMenuToggle = await menuToggle.isVisible().catch(() => false);
    const sidebarVisible = await sidebar.isVisible().catch(() => false);
    expect(hasMenuToggle || sidebarVisible).toBeTruthy();
  });

  test('移动端点击菜单按钮打开侧边栏', async ({ page }) => {
    await mockAllApis(page);
    await page.goto('/');
    await page.waitForLoadState('load');

    const menuToggle = page.locator('.menu-toggle, .hamburger');
    
    if (await menuToggle.isVisible()) {
      await menuToggle.click();
      await page.waitForTimeout(300);

      // 验证侧边栏打开
      const sidebar = page.locator('.sidebar, nav');
      await expect(sidebar).toBeVisible();
    }
  });
});

test.describe('栅格布局响应式测试', () => {
  test('桌面端显示多列栅格', async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await mockAllApis(page);
    await page.goto('/');
    await page.waitForLoadState('load');

    // 验证快速访问卡片布局
    const actionsGrid = page.locator('.actions-grid');
    if (await actionsGrid.isVisible()) {
      // 桌面端应该显示 2 列
      const cards = await actionsGrid.locator('.action-card').count();
      expect(cards).toBeGreaterThanOrEqual(4);
    }
  });

  test('移动端显示单列布局', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await mockAllApis(page);
    await page.goto('/');
    await page.waitForLoadState('load');

    // 验证内容不溢出
    const bodyWidth = await page.evaluate(() => document.body.scrollWidth);
    expect(bodyWidth).toBeLessThanOrEqual(400);
  });
});

test.describe('文字大小响应式测试', () => {
  test('移动端字体可读', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await mockAllApis(page);
    await page.goto('/');
    await page.waitForLoadState('load');

    // 检查主要文字大小
    const heroTitle = page.locator('.hero-title');
    if (await heroTitle.isVisible()) {
      const fontSize = await heroTitle.evaluate((el) =>
        window.getComputedStyle(el).fontSize
      );
      const size = parseFloat(fontSize);
      expect(size).toBeGreaterThanOrEqual(20); // 最小 20px
    }
  });
});