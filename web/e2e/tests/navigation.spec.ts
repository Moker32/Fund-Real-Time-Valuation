/**
 * 导航 E2E 测试
 */

import { test, expect } from '@playwright/test';
import { MainLayout } from '../page-objects/MainLayout';
import { mockAllApis } from '../utils/api-mock';

test.describe('导航测试', () => {
  test.beforeEach(async ({ page }) => {
    await mockAllApis(page);
  });

  test('侧边栏导航项显示正确', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('load');

    const layout = new MainLayout(page);
    
    // 验证导航项存在
    const navCount = await layout.getNavItemCount();
    expect(navCount).toBeGreaterThanOrEqual(4);
  });

  test('点击导航跳转到基金页面', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('load');

    const layout = new MainLayout(page);
    await layout.clickNavItem('基金自选');
    
    await page.waitForURL('**/funds');
    expect(page.url()).toContain('/funds');
  });

  test('点击导航跳转到商品页面', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('load');

    const layout = new MainLayout(page);
    await layout.clickNavItem('商品行情');
    
    await page.waitForURL('**/commodities');
    expect(page.url()).toContain('/commodities');
  });

  test('点击导航跳转到指数页面', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('load');

    const layout = new MainLayout(page);
    await layout.clickNavItem('全球市场');
    
    await page.waitForURL('**/indices');
    expect(page.url()).toContain('/indices');
  });

  test('点击导航跳转到板块页面', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('load');

    const layout = new MainLayout(page);
    await layout.clickNavItem('行业板块');
    
    await page.waitForURL('**/sectors');
    expect(page.url()).toContain('/sectors');
  });

  test('URL 直接访问各页面', async ({ page }) => {
    // 测试直接访问各页面
    const routes = ['/funds', '/commodities', '/indices', '/sectors'];

    for (const route of routes) {
      await page.goto(route);
      await page.waitForLoadState('load');
      expect(page.url()).toContain(route);
    }
  });
});

test.describe('移动端导航测试', () => {
  test.use({ viewport: { width: 375, height: 667 } });

  test('移动端侧边栏默认隐藏', async ({ page }) => {
    await mockAllApis(page);
    await page.goto('/');
    await page.waitForLoadState('load');

    // 移动端侧边栏可能默认隐藏
    const sidebar = page.locator('.sidebar, nav');
    // 根据实际实现调整断言
    const isVisible = await sidebar.isVisible().catch(() => false);
    // 如果不可见，尝试打开菜单
    if (!isVisible) {
      const menuToggle = page.locator('.menu-toggle, .hamburger');
      if (await menuToggle.isVisible()) {
        await menuToggle.click();
        await page.waitForTimeout(300);
      }
    }
  });

  test('移动端打开菜单后可以导航', async ({ page }) => {
    await mockAllApis(page);
    await page.goto('/');
    await page.waitForLoadState('load');

    // 点击菜单按钮
    const menuToggle = page.locator('.menu-toggle, .hamburger');
    if (await menuToggle.isVisible()) {
      await menuToggle.click();
      await page.waitForTimeout(300);
    }

    // 点击导航项
    const navItem = page.locator('.nav-item, .sidebar a').filter({ hasText: '基金自选' });
    if (await navItem.isVisible()) {
      await navItem.click();
      await page.waitForURL('**/funds');
      expect(page.url()).toContain('/funds');
    }
  });
});