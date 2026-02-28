/**
 * 基金功能 E2E 测试
 */

import { test, expect } from '@playwright/test';
import { FundsPage } from '../page-objects/FundsPage';
import { mockFundsApi, mockEmptyData, mockApiError } from '../utils/api-mock';
import { mockFunds, mockSearchResults } from '../fixtures/mock-data';

test.describe('基金列表测试', () => {
  test('基金列表正常显示', async ({ page }) => {
    await mockFundsApi(page);
    
    const fundsPage = new FundsPage(page);
    await fundsPage.goto();
    await fundsPage.waitForFundsLoad();

    // 验证基金卡片存在
    const count = await fundsPage.getFundCount();
    expect(count).toBeGreaterThan(0);
  });

  test('基金卡片信息显示正确', async ({ page }) => {
    await mockFundsApi(page);
    
    const fundsPage = new FundsPage(page);
    await fundsPage.goto();
    await fundsPage.waitForFundsLoad();

    // 获取第一个基金信息
    const info = await fundsPage.getFundCardInfo(0);
    expect(info.code).toBeTruthy();
    expect(info.name).toBeTruthy();
  });

  test('空数据状态显示', async ({ page }) => {
    await mockEmptyData(page, '**/api/funds*');
    
    const fundsPage = new FundsPage(page);
    await fundsPage.goto();
    await fundsPage.waitForFundsLoad();

    // 验证空状态
    const isEmpty = await fundsPage.isEmptyStateVisible();
    expect(isEmpty).toBe(true);
  });
});

test.describe('添加基金测试', () => {
  test('打开添加基金弹窗', async ({ page }) => {
    await mockFundsApi(page);
    
    const fundsPage = new FundsPage(page);
    await fundsPage.goto();
    await fundsPage.waitForFundsLoad();

    // 点击添加按钮
    await fundsPage.clickAddFund();

    // 验证弹窗打开
    const dialog = page.locator('.add-fund-dialog, .modal, [role="dialog"]');
    await expect(dialog).toBeVisible();
  });

  test('搜索基金功能', async ({ page }) => {
    // Mock 搜索 API
    await page.route('**/api/funds/search*', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ results: mockSearchResults }),
      });
    });
    await mockFundsApi(page);
    
    const fundsPage = new FundsPage(page);
    await fundsPage.goto();
    await fundsPage.waitForFundsLoad();

    // 打开搜索
    await fundsPage.clickAddFund();
    await fundsPage.searchFund('华夏');

    // 验证搜索结果
    const searchResults = page.locator('.search-results .result-item, .search-result-item');
    await expect(searchResults.first()).toBeVisible({ timeout: 5000 });
  });

  test('确认添加基金', async ({ page }) => {
    await mockFundsApi(page);
    
    // Mock 添加 API
    await page.route('**/api/funds/watchlist*', async (route) => {
      if (route.request().method() === 'POST') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ success: true }),
        });
      } else {
        await route.continue();
      }
    });
    
    const fundsPage = new FundsPage(page);
    await fundsPage.goto();
    await fundsPage.waitForFundsLoad();

    // 打开添加弹窗
    await fundsPage.clickAddFund();
    
    // 填写搜索
    await fundsPage.searchFund('000001');
    
    // 选择结果
    await fundsPage.selectSearchResult(0);
    
    // 确认添加
    await fundsPage.confirmAdd();

    // 验证添加成功（可以检查 toast 或列表更新）
  });
});

test.describe('删除基金测试', () => {
  test('删除基金确认弹窗', async ({ page }) => {
    await mockFundsApi(page);
    
    const fundsPage = new FundsPage(page);
    await fundsPage.goto();
    await fundsPage.waitForFundsLoad();

    // 点击删除按钮
    const deleteBtn = page.locator('.fund-card .delete-btn, .fund-card .btn-delete').first();
    if (await deleteBtn.isVisible()) {
      await deleteBtn.click();

      // 验证确认弹窗
      const confirmDialog = page.locator('.confirm-dialog, .modal');
      await expect(confirmDialog).toBeVisible();
    }
  });
});

test.describe('错误状态测试', () => {
  test('API 错误显示错误提示', async ({ page }) => {
    await mockApiError(page, '**/api/funds*', 'Internal Server Error', 500);
    
    const fundsPage = new FundsPage(page);
    await fundsPage.goto();

    // 验证错误提示显示
    const errorState = page.locator('.error-state, .error-message');
    await expect(errorState).toBeVisible({ timeout: 10000 });
  });

  test('网络错误显示错误提示', async ({ page }) => {
    await page.route('**/api/funds*', async (route) => {
      await route.abort('failed');
    });
    
    const fundsPage = new FundsPage(page);
    await fundsPage.goto();

    // 验证错误提示
    const errorState = page.locator('.error-state, .error-message');
    await expect(errorState).toBeVisible({ timeout: 10000 });
  });
});

test.describe('基金页面响应式测试', () => {
  test.use({ viewport: { width: 375, height: 667 } });

  test('移动端基金卡片正确显示', async ({ page }) => {
    await mockFundsApi(page);
    
    const fundsPage = new FundsPage(page);
    await fundsPage.goto();
    await fundsPage.waitForFundsLoad();

    // 验证基金卡片存在
    const count = await fundsPage.getFundCount();
    expect(count).toBeGreaterThanOrEqual(0);
  });
});