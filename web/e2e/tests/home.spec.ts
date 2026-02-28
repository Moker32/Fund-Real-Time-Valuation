/**
 * 首页 E2E 测试
 */

import { test, expect } from '@playwright/test';
import { HomePage } from '../page-objects/HomePage';
import { mockAllApis } from '../utils/api-mock';

test.describe('首页测试', () => {
  let homePage: HomePage;

  test.beforeEach(async ({ page }) => {
    // Mock API
    await mockAllApis(page);

    homePage = new HomePage(page);
    await homePage.goto();
  });

  test('页面正常加载', async () => {
    // 验证 Hero 区域
    await expect(homePage.heroTitle).toBeVisible();
    const title = await homePage.getHeroTitle();
    expect(title).toContain('FundVue');
  });

  test('显示统计信息', async () => {
    // 等待内容加载
    await homePage.waitForContentLoaded();

    // 验证统计项存在
    const statCount = await homePage.getStatCount();
    expect(statCount).toBeGreaterThanOrEqual(3);
  });

  test('快速访问卡片显示正确', async () => {
    await homePage.waitForContentLoaded();

    // 验证快速访问卡片数量
    const cardCount = await homePage.getActionCardCount();
    expect(cardCount).toBeGreaterThanOrEqual(4);

    // 验证卡片标题
    const titles = await homePage.getActionCardTitles();
    expect(titles).toContain('基金自选');
    expect(titles).toContain('商品行情');
    expect(titles).toContain('全球市场');
    expect(titles).toContain('行业板块');
  });

  test('点击快速访问卡片跳转正确', async ({ page }) => {
    await homePage.waitForContentLoaded();

    // 点击基金自选卡片
    await homePage.clickActionCard('基金自选');
    await page.waitForURL('**/funds');
    expect(page.url()).toContain('/funds');
  });

  test('点击商品行情卡片跳转正确', async ({ page }) => {
    await homePage.waitForContentLoaded();

    await homePage.clickActionCard('商品行情');
    await page.waitForURL('**/commodities');
    expect(page.url()).toContain('/commodities');
  });

  test('点击全球市场卡片跳转正确', async ({ page }) => {
    await homePage.waitForContentLoaded();

    await homePage.clickActionCard('全球市场');
    await page.waitForURL('**/indices');
    expect(page.url()).toContain('/indices');
  });

  test('点击行业板块卡片跳转正确', async ({ page }) => {
    await homePage.waitForContentLoaded();

    await homePage.clickActionCard('行业板块');
    await page.waitForURL('**/sectors');
    expect(page.url()).toContain('/sectors');
  });

  test('涨跌幅排行显示', async () => {
    await homePage.waitForContentLoaded();

    // 检查是否有排行数据
    const hasRankings = await homePage.hasRankings();
    
    if (hasRankings) {
      // 获取涨幅排行
      const risingItems = await homePage.getRankingItems('rising');
      expect(risingItems.length).toBeGreaterThan(0);

      // 获取跌幅排行
      const fallingItems = await homePage.getRankingItems('falling');
      expect(fallingItems.length).toBeGreaterThan(0);
    }
  });
});

test.describe('首页空状态测试', () => {
  test('空状态显示正确', async ({ page }) => {
    // Mock 空数据
    await page.route('**/api/funds*', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ funds: [], total: 0 }),
      });
    });

    const homePage = new HomePage(page);
    await homePage.goto();
    await homePage.waitForContentLoaded();

    // 验证空状态显示
    const isEmpty = await homePage.isEmptyStateVisible();
    expect(isEmpty).toBe(true);
  });

  test('空状态点击添加基金跳转', async ({ page }) => {
    // Mock 空数据
    await page.route('**/api/funds*', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ funds: [], total: 0 }),
      });
    });

    const homePage = new HomePage(page);
    await homePage.goto();
    await homePage.waitForContentLoaded();

    // 点击添加基金
    await homePage.clickAddFundButton();
    await page.waitForURL('**/funds');
    expect(page.url()).toContain('/funds');
  });
});

test.describe('首页响应式测试', () => {
  test.use({ viewport: { width: 375, height: 667 } });

  test('移动端布局正确', async ({ page }) => {
    const homePage = new HomePage(page);
    await mockAllApis(page);
    await homePage.goto();
    await homePage.waitForContentLoaded();

    // 验证 Hero 区域
    await expect(homePage.heroTitle).toBeVisible();

    // 验证快速访问卡片
    const cardCount = await homePage.getActionCardCount();
    expect(cardCount).toBeGreaterThanOrEqual(4);
  });

  test('平板端布局正确', async ({ page }) => {
    await page.setViewportSize({ width: 768, height: 1024 });
    
    const homePage = new HomePage(page);
    await mockAllApis(page);
    await homePage.goto();
    await homePage.waitForContentLoaded();

    // 验证内容正常显示
    await expect(homePage.heroTitle).toBeVisible();
  });
});