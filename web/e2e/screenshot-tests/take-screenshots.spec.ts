/**
 * 生成 README 展示截图
 * 运行: pnpm exec playwright test screenshot-tests/take-screenshots.spec.ts --config=e2e/playwright.screenshot.config.ts
 */

import { test } from '@playwright/test';
import { mockAllApis, mockFundsApi, mockCommoditiesApi, mockIndicesApi, mockSectorsApi } from '../utils/api-mock';

// 相对路径：从 web/e2e/screenshot-tests 到 docs/screenshots
// 路径: web/e2e/screenshot-tests/../../docs/screenshots = docs/screenshots
const screenshotsDir = '../../../docs/screenshots';

// 使用 baseURL 从配置中读取
test.use({
  baseURL: 'http://localhost:3000',
});

test.describe('生成 README 截图', () => {
  test.beforeEach(async ({ page }) => {
    // 设置视口为桌面尺寸
    await page.setViewportSize({ width: 1440, height: 900 });
  });

  test('首页截图', async ({ page }) => {
    await mockAllApis(page);
    await page.goto('/', { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(2000);
    
    await page.screenshot({ 
      path: `${screenshotsDir}/home.png`, 
      fullPage: true 
    });
  });

  test('基金页面截图', async ({ page }) => {
    await mockFundsApi(page);
    await page.goto('/funds', { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(2000);
    
    await page.screenshot({ 
      path: `${screenshotsDir}/funds.png`, 
      fullPage: true 
    });
  });

  test('商品页面截图', async ({ page }) => {
    await mockCommoditiesApi(page);
    await page.goto('/commodities', { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(2000);
    
    await page.screenshot({ 
      path: `${screenshotsDir}/commodities.png`, 
      fullPage: true 
    });
  });

  test('指数页面截图', async ({ page }) => {
    await mockIndicesApi(page);
    await page.goto('/indices', { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(2000);
    
    await page.screenshot({ 
      path: `${screenshotsDir}/indices.png`, 
      fullPage: true 
    });
  });

  test('板块页面截图', async ({ page }) => {
    await mockSectorsApi(page);
    await page.goto('/sectors', { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(2000);
    
    await page.screenshot({ 
      path: `${screenshotsDir}/sectors.png`, 
      fullPage: true 
    });
  });

  test('移动端首页截图', async ({ page }) => {
    await mockAllApis(page);
    await page.setViewportSize({ width: 375, height: 812 });
    await page.goto('/', { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(2000);
    
    await page.screenshot({ 
      path: `${screenshotsDir}/home-mobile.png`, 
      fullPage: true 
    });
  });
});
