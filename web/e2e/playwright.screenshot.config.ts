import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright 截图测试专用配置
 * 自动启动 Vite 开发服务器
 */
export default defineConfig({
  testDir: './screenshot-tests',
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: 0,
  workers: 1,
  reporter: [['list']],

  use: {
    baseURL: 'http://localhost:3000',
    trace: 'off',
    screenshot: 'off',
    actionTimeout: 10000,
    navigationTimeout: 30000,
  },

  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],

  // 自动启动开发服务器
  webServer: {
    command: 'cd .. && pnpm run dev',
    url: 'http://localhost:3000',
    reuseExistingServer: !process.env.CI,
    timeout: 120000,
    stdout: 'pipe',
    stderr: 'pipe',
  },

  timeout: 60000,
});
