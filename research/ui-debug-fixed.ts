/**
 * UI 自动调试脚本 (修复版)
 * 检查各个页面的渲染状态
 */
import { chromium, type Browser } from '@playwright/test';

const BASE_URL = 'http://localhost:8000';

// 颜色代码
const colors = {
  reset: '\x1b[0m',
  green: '\x1b[32m',
  red: '\x1b[31m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
  cyan: '\x1b[36m',
};

interface CheckResult {
  name: string;
  passed: boolean;
  message: string;
}

// 实际的CSS类名映射
const pageConfigs = [
  {
    name: '首页',
    path: '/',
    selectors: ['.app-layout', '.sidebar', '.main-content'],
  },
  {
    name: '基金页',
    path: '/funds',
    selectors: ['.funds-view'],
  },
  {
    name: '商品页',
    path: '/commodities',
    selectors: ['.commodities-view'],
  },
  {
    name: '指数页',
    path: '/indices',
    selectors: ['.indices-view'],
  },
  {
    name: '板块页',
    path: '/sectors',
    selectors: ['.sectors-view'],
  },
];

async function checkPage(browser: Browser, config: typeof pageConfigs[0]): Promise<CheckResult[]> {
  const page = await browser.newPage();
  const results: CheckResult[] = [];

  try {
    console.log(`${colors.cyan}▶ 检查页面: ${config.name}${colors.reset}`);

    // 设置控制台错误监听
    const consoleErrors: string[] = [];
    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text());
      }
    });

    // 设置页面错误监听
    const pageErrors: string[] = [];
    page.on('pageerror', (error) => {
      pageErrors.push(error.message);
    });

    // 导航到页面，使用 domcontentloaded 而不是 networkidle
    const response = await page.goto(`${BASE_URL}${config.path}`, {
      waitUntil: 'domcontentloaded',
      timeout: 15000,
    });

    if (!response) {
      results.push({
        name: 'HTTP请求',
        passed: false,
        message: '无响应',
      });
      return results;
    }

    if (!response.ok()) {
      results.push({
        name: 'HTTP请求',
        passed: false,
        message: `HTTP ${response.status()}`,
      });
      return results;
    }

    results.push({
      name: 'HTTP请求',
      passed: true,
      message: `HTTP ${response.status()}`,
    });

    // 等待页面渲染
    await page.waitForTimeout(2000);

    // 检查选择器
    for (const selector of config.selectors) {
      try {
        const element = await page.$(selector);
        if (element) {
          const visible = await element.isVisible().catch(() => false);
          results.push({
            name: `元素 ${selector}`,
            passed: visible,
            message: visible ? '可见' : '存在但不可见',
          });
        } else {
          results.push({
            name: `元素 ${selector}`,
            passed: false,
            message: '未找到',
          });
        }
      } catch (e) {
        results.push({
          name: `元素 ${selector}`,
          passed: false,
          message: `检查出错: ${e}`,
        });
      }
    }

    // 截图
    const screenshotPath = `/tmp/ui-debug-${config.name.replace(/\s/g, '-')}.png`;
    await page.screenshot({ path: screenshotPath, fullPage: true }).catch(() => {});
    console.log(`  ${colors.blue}📸 截图: ${screenshotPath}${colors.reset}`);

    // 检查控制台错误
    if (consoleErrors.length > 0) {
      console.log(`  ${colors.yellow}⚠ 控制台错误 (${consoleErrors.length}个):${colors.reset}`);
      consoleErrors.slice(0, 2).forEach(err => {
        console.log(`    - ${err.substring(0, 80)}`);
      });
    }

    // 检查页面错误
    if (pageErrors.length > 0) {
      console.log(`  ${colors.red}✗ JavaScript错误 (${pageErrors.length}个):${colors.reset}`);
      pageErrors.slice(0, 2).forEach(err => {
        console.log(`    - ${err.substring(0, 80)}`);
      });
    }

  } catch (error) {
    const errorMsg = error instanceof Error ? error.message : String(error);
    results.push({
      name: '页面检查',
      passed: false,
      message: errorMsg,
    });
    console.log(`  ${colors.red}✗ 错误: ${errorMsg}${colors.reset}`);
  } finally {
    await page.close();
  }

  return results;
}

async function main() {
  console.log(`${colors.cyan}====================================${colors.reset}`);
  console.log(`${colors.cyan}  UI 自动调试工具 (修复版)${colors.reset}`);
  console.log(`${colors.cyan}====================================${colors.reset}`);
  console.log(`目标 URL: ${BASE_URL}\n`);

  const browser = await chromium.launch({ headless: true });

  try {
    const allResults: Map<string, CheckResult[]> = new Map();

    for (const config of pageConfigs) {
      const results = await checkPage(browser, config);
      allResults.set(config.name, results);

      // 显示结果
      for (const result of results) {
        const icon = result.passed ? `${colors.green}✓` : `${colors.red}✗`;
        console.log(`  ${icon} ${result.name}: ${result.message}${colors.reset}`);
      }
      console.log('');
    }

    // 汇总
    let totalPassed = 0;
    let totalFailed = 0;

    allResults.forEach((results) => {
      results.forEach(r => {
        if (r.passed) totalPassed++;
        else totalFailed++;
      });
    });

    console.log(`${colors.cyan}====================================${colors.reset}`);
    console.log(`${colors.green}通过: ${totalPassed}${colors.reset} | ${colors.red}失败: ${totalFailed}${colors.reset}`);
    console.log(`${colors.cyan}====================================${colors.reset}`);

    if (totalFailed > 0) {
      process.exit(1);
    }

  } finally {
    await browser.close();
  }
}

main().catch(console.error);