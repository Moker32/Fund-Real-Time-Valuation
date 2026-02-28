/**
 * API Mock 工具函数
 * 用于拦截和模拟 API 请求
 */

import { Page, Route } from '@playwright/test';
import { mockApiResponses } from '../fixtures/mock-data';

/**
 * Mock API 响应类型
 */
type MockApiOptions = {
  delay?: number;
  status?: number;
};

/**
 * Mock 基金 API
 */
export async function mockFundsApi(
  page: Page,
  options: MockApiOptions = {}
): Promise<void> {
  const { delay = 0, status = 200 } = options;

  await page.route('**/api/funds*', async (route: Route) => {
    const url = route.request().url();

    // 搜索基金
    if (url.includes('search')) {
      await route.fulfill({
        status,
        contentType: 'application/json',
        body: JSON.stringify(mockApiResponses.searchFunds),
      });
      return;
    }

    // 基金列表
    await new Promise((resolve) => setTimeout(resolve, delay));
    await route.fulfill({
      status,
      contentType: 'application/json',
      body: JSON.stringify(mockApiResponses.funds),
    });
  });
}

/**
 * Mock 指数 API
 */
export async function mockIndicesApi(
  page: Page,
  options: MockApiOptions = {}
): Promise<void> {
  const { delay = 0, status = 200 } = options;

  await page.route('**/api/indices*', async (route: Route) => {
    await new Promise((resolve) => setTimeout(resolve, delay));
    await route.fulfill({
      status,
      contentType: 'application/json',
      body: JSON.stringify(mockApiResponses.indices),
    });
  });
}

/**
 * Mock 商品 API
 */
export async function mockCommoditiesApi(
  page: Page,
  options: MockApiOptions = {}
): Promise<void> {
  const { delay = 0, status = 200 } = options;

  // Mock 商品分类 API
  await page.route('**/api/commodities/categories*', async (route: Route) => {
    await new Promise((resolve) => setTimeout(resolve, delay));
    await route.fulfill({
      status,
      contentType: 'application/json',
      body: JSON.stringify({ categories: mockApiResponses.commodities.categories }),
    });
  });

  // Mock 商品列表 API
  await page.route('**/api/commodities*', async (route: Route) => {
    await new Promise((resolve) => setTimeout(resolve, delay));
    await route.fulfill({
      status,
      contentType: 'application/json',
      body: JSON.stringify(mockApiResponses.commodities),
    });
  });
}

/**
 * Mock 板块 API
 */
export async function mockSectorsApi(
  page: Page,
  options: MockApiOptions = {}
): Promise<void> {
  const { delay = 0, status = 200 } = options;

  await page.route('**/api/sectors*', async (route: Route) => {
    await new Promise((resolve) => setTimeout(resolve, delay));
    await route.fulfill({
      status,
      contentType: 'application/json',
      body: JSON.stringify(mockApiResponses.sectors),
    });
  });
}

/**
 * Mock 债券 API
 */
export async function mockBondsApi(
  page: Page,
  options: MockApiOptions = {}
): Promise<void> {
  const { delay = 0, status = 200 } = options;

  await page.route('**/api/bonds*', async (route: Route) => {
    await new Promise((resolve) => setTimeout(resolve, delay));
    await route.fulfill({
      status,
      contentType: 'application/json',
      body: JSON.stringify(mockApiResponses.bonds),
    });
  });
}

/**
 * Mock 健康检查 API
 */
export async function mockHealthApi(
  page: Page,
  options: MockApiOptions = {}
): Promise<void> {
  const { delay = 0, status = 200 } = options;

  await page.route('**/api/health*', async (route: Route) => {
    await new Promise((resolve) => setTimeout(resolve, delay));
    await route.fulfill({
      status,
      contentType: 'application/json',
      body: JSON.stringify({ status: 'ok', timestamp: new Date().toISOString() }),
    });
  });
}

/**
 * Mock 所有 API
 * 一键 mock 所有数据源
 */
export async function mockAllApis(
  page: Page,
  options: MockApiOptions = {}
): Promise<void> {
  await Promise.all([
    mockFundsApi(page, options),
    mockIndicesApi(page, options),
    mockCommoditiesApi(page, options),
    mockSectorsApi(page, options),
    mockBondsApi(page, options),
    mockHealthApi(page, options),
  ]);
}

/**
 * Mock 错误响应
 */
export async function mockApiError(
  page: Page,
  apiPattern: string,
  errorMessage = 'Internal Server Error',
  status = 500
): Promise<void> {
  await page.route(apiPattern, async (route: Route) => {
    await route.fulfill({
      status,
      contentType: 'application/json',
      body: JSON.stringify({ error: errorMessage }),
    });
  });
}

/**
 * Mock 空数据响应
 */
export async function mockEmptyData(
  page: Page,
  apiPattern: string
): Promise<void> {
  await page.route(apiPattern, async (route: Route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ funds: [], total: 0 }),
    });
  });
}

/**
 * Mock 网络延迟
 */
export async function mockSlowNetwork(
  page: Page,
  apiPattern: string,
  delayMs: number
): Promise<void> {
  await page.route(apiPattern, async (route: Route) => {
    await new Promise((resolve) => setTimeout(resolve, delayMs));
    await route.continue();
  });
}

/**
 * 清除所有 mock
 */
export async function clearMocks(page: Page): Promise<void> {
  await page.unrouteAll();
}