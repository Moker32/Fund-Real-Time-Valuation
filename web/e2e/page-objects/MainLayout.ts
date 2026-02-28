/**
 * 主布局页面对象
 * 包含侧边栏导航等功能
 */

import { Page, Locator } from '@playwright/test';
import { BasePage } from './BasePage';

export class MainLayout extends BasePage {
  // 定位器
  readonly sidebar: Locator;
  readonly navItems: Locator;
  readonly menuToggle: Locator;
  readonly overlay: Locator;

  constructor(page: Page) {
    super(page);

    this.sidebar = page.locator('.sidebar, nav');
    this.navItems = page.locator('.nav-item, .sidebar a');
    this.menuToggle = page.locator('.menu-toggle, .hamburger, [data-testid="menu-toggle"]');
    this.overlay = page.locator('.overlay, .sidebar-overlay');
  }

  /**
   * 导航到指定页面
   */
  async navigateTo(path: string): Promise<void> {
    // 点击对应的导航项
    const navItem = this.navItems.filter({ has: this.page.locator(`[href="${path}"]`) });
    if (await navItem.count() > 0) {
      await navItem.click();
    } else {
      await this.navigate(path);
    }
    await this.waitForLoad();
  }

  /**
   * 点击导航项
   */
  async clickNavItem(label: string): Promise<void> {
    await this.navItems.filter({ hasText: label }).click();
  }

  /**
   * 获取导航项数量
   */
  async getNavItemCount(): Promise<number> {
    return await this.navItems.count();
  }

  /**
   * 检查侧边栏是否可见
   */
  async isSidebarVisible(): Promise<boolean> {
    return await this.sidebar.isVisible();
  }

  /**
   * 切换菜单（移动端）
   */
  async toggleMenu(): Promise<void> {
    await this.menuToggle.click();
  }

  /**
   * 打开菜单（移动端）
   */
  async openMenu(): Promise<void> {
    if (!await this.isSidebarVisible()) {
      await this.toggleMenu();
      await this.waitForElement('.sidebar.visible, nav.visible, .sidebar.open');
    }
  }

  /**
   * 关闭菜单（移动端）
   */
  async closeMenu(): Promise<void> {
    if (await this.isSidebarVisible()) {
      // 点击遮罩关闭
      if (await this.overlay.isVisible()) {
        await this.overlay.click();
      } else {
        await this.toggleMenu();
      }
    }
  }

  /**
   * 获取所有导航项文本
   */
  async getNavItemTexts(): Promise<string[]> {
    const count = await this.navItems.count();
    const texts: string[] = [];

    for (let i = 0; i < count; i++) {
      const text = await this.navItems.nth(i).textContent();
      if (text) texts.push(text.trim());
    }

    return texts;
  }

  /**
   * 验证当前激活的导航项
   */
  async getActiveNavItem(): Promise<string> {
    const activeItem = this.navItems.locator('.active, .router-link-active');
    return await activeItem.textContent() || '';
  }
}