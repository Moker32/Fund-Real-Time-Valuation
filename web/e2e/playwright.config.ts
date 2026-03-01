import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright E2E 测试配置
 * @see https://playwright.dev/docs/test-configuration
 *
 * 测试策略说明：
 * - 默认使用"完全 Mock 模式"，所有 API 请求被拦截并返回预定义数据
 * - 若需真实 API 集成测试，可在本地启动后端服务 (pnpm run dev:api)
 * - CI 环境会自动启动后端服务，支持真实 API 测试
 */
export default defineConfig({
  // 测试目录
  testDir: './tests',

  // 完全并行运行测试
  fullyParallel: true,

  // CI 环境禁止 only
  forbidOnly: !!process.env.CI,

  // CI 环境重试 2 次
  retries: process.env.CI ? 2 : 0,

  // CI 环境单线程，本地可以并行
  workers: process.env.CI ? 1 : undefined,

  // 报告器
  reporter: [
    ['html', { outputFolder: 'playwright-report' }],
    ['list'],
  ],

  // 全局配置
  use: {
    // 基础 URL - CI 环境使用 8000（后端服务），本地使用 3000
    baseURL: process.env.CI ? 'http://localhost:8000' : 'http://localhost:3000',

    // 失败时收集 trace
    trace: 'on-first-retry',

    // 失败时截图
    screenshot: 'only-on-failure',

    // 视频录制（CI 环境）
    video: process.env.CI ? 'on-first-retry' : 'off',

    // 超时设置
    actionTimeout: 10000,
    navigationTimeout: 30000,
  },

  // 浏览器项目配置
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
    },
    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'] },
    },
    // 移动端测试
    {
      name: 'Mobile Chrome',
      use: { ...devices['Pixel 5'] },
    },
    {
      name: 'Mobile Safari',
      use: { ...devices['iPhone 12'] },
    },
  ],

  // 开发服务器配置
  // 注意: CI 环境由 GitHub Actions 启动后端服务 (端口 8000)，不需要启动 webServer
  // 本地开发时使用 Vite 开发服务器 (端口 3000)
  webServer: process.env.CI ? undefined : {
    command: 'pnpm run dev',
    url: 'http://localhost:3000',
    reuseExistingServer: true,
    timeout: 120000,
    stdout: 'ignore',
    stderr: 'pipe',
  },

  // 超时设置
  timeout: 30000,
  expect: {
    timeout: 5000,
  },
});