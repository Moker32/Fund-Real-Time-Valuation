/**
 * 基础页面类
 * 所有页面对象的父类，提供通用方法
 */

import { Page, Locator, expect } from '@playwright/test';

export abstract class BasePage {
  readonly page: Page;

  constructor(page: Page) {
    this.page = page;
  }

  /**
   * 导航到指定路径
   */
  async navigate(path: string): Promise<void> {
    await this.page.goto(path);
  }

  /**
   * 等待页面加载完成
   * 注意：不使用 'networkidle'，因为 WebSocket 连接会阻止该状态
   */
  async waitForLoad(): Promise<void> {
    // 等待 DOM 内容加载完成
    await this.page.waitForLoadState('domcontentloaded');
    // 等待页面基本元素渲染
    await this.page.waitForLoadState('load');
  }

  /**
   * 等待 URL 变化
   */
  async waitForUrl(expected: string | RegExp): Promise<void> {
    await this.page.waitForURL(expected);
  }

  /**
   * 获取页面标题
   */
  async getTitle(): Promise<string> {
    return await this.page.title();
  }

  /**
   * 获取当前 URL
   */
  getCurrentUrl(): string {
    return this.page.url();
  }

  /**
   * 点击元素
   */
  async clickElement(selector: string): Promise<void> {
    await this.page.click(selector);
  }

  /**
   * 填写输入框
   */
  async fillInput(selector: string, value: string): Promise<void> {
    await this.page.fill(selector, value);
  }

  /**
   * 等待元素可见
   */
  async waitForElement(selector: string, timeout = 30000): Promise<void> {
    await this.page.waitForSelector(selector, { state: 'visible', timeout });
  }

  /**
   * 等待元素隐藏
   */
  async waitForElementHidden(
    selector: string,
    timeout = 30000
  ): Promise<void> {
    await this.page.waitForSelector(selector, { state: 'hidden', timeout });
  }

  /**
   * 检查元素是否存在
   */
  async elementExists(selector: string): Promise<boolean> {
    const count = await this.page.locator(selector).count();
    return count > 0;
  }

  /**
   * 获取元素文本
   */
  async getElementText(selector: string): Promise<string> {
    return (await this.page.textContent(selector)) || '';
  }

  /**
   * 获取元素数量
   */
  async getElementCount(selector: string): Promise<number> {
    return await this.page.locator(selector).count();
  }

  /**
   * 截图
   */
  async screenshot(name: string): Promise<void> {
    await this.page.screenshot({ path: `screenshots/${name}.png` });
  }

  /**
   * 断言元素可见
   */
  async assertElementVisible(selector: string): Promise<void> {
    await expect(this.page.locator(selector)).toBeVisible();
  }

  /**
   * 断言元素包含文本
   */
  async assertElementText(
    selector: string,
    expected: string | RegExp
  ): Promise<void> {
    await expect(this.page.locator(selector)).toContainText(expected);
  }

  /**
   * 断言 URL 包含路径
   */
  async assertUrlContains(path: string): Promise<void> {
    expect(this.page.url()).toContain(path);
  }
}