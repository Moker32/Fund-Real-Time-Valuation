/**
 * UI 自动调试脚本
 * 检查各个页面的渲染状态
 */
import { chromium, type Page, type Browser } from '@playwright/test';

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

interface PageCheck {
  name: string;
  path: string;
  checks: {
    selector: string;
    description: string;
    required?: boolean;
  }[];
}

const pagesToCheck: PageCheck[] = [
  {
    name: '首页',
    path: '/',
    checks: [
      { selector: '.layout', description: '布局容器', required: true },
      { selector: '.sidebar', description: '侧边栏', required: true },
      { selector: '.main-content', description: '主内容区', required: true },
      { selector: '.dashboard-grid', description: '仪表板网格', required: false },
    ],
  },
  {
    name: '基金页',
    path: '/funds',
    checks: [
      { selector: '.funds-view', description: '基金视图', required: true },
      { selector: '.fund-card', description: '基金卡片', required: false },
    ],
  },
  {
    name: '商品页',
    path: '/commodities',
    checks: [
      { selector: '.commodities-view', description: '商品视图', required: true },
      { selector: '.commodity-card', description: '商品卡片', required: false },
    ],
  },
  {
    name: '指数页',
    path: '/indices',
    checks: [
      { selector: '.indices-view', description: '指数视图', required: true },
      { selector: '.index-card', description: '指数卡片', required: false },
    ],
  },
  {
    name: '板块页',
    path: '/sectors',
    checks: [
      { selector: '.sectors-view', description: '板块视图', required: true },
      { selector: '.sector-card', description: '板块卡片', required: false },
    ],
  },
];

async function checkPage(browser: Browser, pageCheck: PageCheck): Promise<boolean> {
  const page = await browser.newPage();
  let hasErrors = false;

  try {
    console.log(`${colors.cyan}▶ 检查页面: ${pageCheck.name}${colors.reset}`);

    // 导航到页面
    const response = await page.goto(`${BASE_URL}${pageCheck.path}`, {
      waitUntil: 'networkidle',
      timeout: 30000,
    });

    if (!response) {
      console.log(`  ${colors.red}✗ 页面加载失败: 无响应${colors.reset}`);
      hasErrors = true;
      return false;
    }

    if (!response.ok()) {
      console.log(`  ${colors.red}✗ HTTP 错误: ${response.status()}${colors.reset}`);
      hasErrors = true;
    } else {
      console.log(`  ${colors.green}✓ HTTP 状态: ${response.status()}${colors.reset}`);
    }

    // 等待页面加载
    await page.waitForTimeout(2000);

    // 检查控制台错误
    const consoleErrors: string[] = [];
    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text());
      }
    });

    // 检查 JavaScript 错误
    const jsErrors: string[] = [];
    page.on('pageerror', (error) => {
      jsErrors.push(error.message);
    });

    // 检查选择器
    for (const check of pageCheck.checks) {
      try {
        const element = await page.$(check.selector);
        if (element) {
          const visible = await element.isVisible().catch(() => false);
          if (visible) {
            console.log(`  ${colors.green}✓ ${check.description} (${check.selector})${colors.reset}`);
          } else {
            console.log(`  ${colors.yellow}⚠ ${check.description} 存在但不可见 (${check.selector})${colors.reset}`);
            if (check.required) hasErrors = true;
          }
        } else {
          if (check.required) {
            console.log(`  ${colors.red}✗ ${check.description} 未找到 (${check.selector})${colors.reset}`);
            hasErrors = true;
          } else {
            console.log(`  ${colors.yellow}⚠ ${check.description} 未找到 (可选) (${check.selector})${colors.reset}`);
          }
        }
      } catch (e) {
        console.log(`  ${colors.red}✗ 检查 ${check.description} 时出错: ${e}${colors.reset}`);
        hasErrors = true;
      }
    }

    // 截图
    const screenshotPath = `/tmp/ui-debug-${pageCheck.name.replace(/\s/g, '-').toLowerCase()}.png`;
    await page.screenshot({ path: screenshotPath, fullPage: true });
    console.log(`  ${colors.blue}📸 截图已保存: ${screenshotPath}${colors.reset}`);

    // 报告控制台错误
    if (consoleErrors.length > 0) {
      console.log(`  ${colors.red}✗ 控制台错误 (${consoleErrors.length}个):${colors.reset}`);
      consoleErrors.slice(0, 3).forEach(err => {
        console.log(`    - ${err.substring(0, 100)}${err.length > 100 ? '...' : ''}`);
      });
      hasErrors = true;
    }

    // 报告 JS 错误
    if (jsErrors.length > 0) {
      console.log(`  ${colors.red}✗ JavaScript 错误 (${jsErrors.length}个):${colors.reset}`);
      jsErrors.slice(0, 3).forEach(err => {
        console.log(`    - ${err.substring(0, 100)}${err.length > 100 ? '...' : ''}`);
      });
      hasErrors = true;
    }

    if (!hasErrors) {
      console.log(`  ${colors.green}✓ 页面检查通过${colors.reset}`);
    }

    return !hasErrors;
  } catch (error) {
    console.log(`  ${colors.red}✗ 检查页面时出错: ${error}${colors.reset}`);
    return false;
  } finally {
    await page.close();
  }
}

async function runDebug() {
  console.log(`${colors.cyan}====================================${colors.reset}`);
  console.log(`${colors.cyan}  UI 自动调试工具${colors.reset}`);
  console.log(`${colors.cyan}====================================${colors.reset}`);
  console.log(`目标 URL: ${BASE_URL}\n`);

  const browser = await chromium.launch({ headless: true });

  try {
    let passed = 0;
    let failed = 0;

    for (const pageCheck of pagesToCheck) {
      const success = await checkPage(browser, pageCheck);
      if (success) {
        passed++;
      } else {
        failed++;
      }
      console.log('');
    }

    console.log(`${colors.cyan}====================================${colors.reset}`);
    console.log(`${colors.green}通过: ${passed}${colors.reset} | ${colors.red}失败: ${failed}${colors.reset}`);
    console.log(`${colors.cyan}====================================${colors.reset}`);

    if (failed > 0) {
      process.exit(1);
    }
  } finally {
    await browser.close();
  }
}

runDebug().catch(console.error);
