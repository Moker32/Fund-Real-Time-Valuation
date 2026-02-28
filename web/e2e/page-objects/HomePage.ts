/**
 * 首页页面对象
 */

import { Page, Locator } from '@playwright/test';
import { BasePage } from './BasePage';

export class HomePage extends BasePage {
  // 定位器
  readonly heroTitle: Locator;
  readonly heroSubtitle: Locator;
  readonly statItems: Locator;
  readonly actionCards: Locator;
  readonly rankingsSection: Locator;
  readonly emptyState: Locator;
  readonly loadingState: Locator;

  constructor(page: Page) {
    super(page);

    // Hero 区域
    this.heroTitle = page.locator('.hero-title');
    this.heroSubtitle = page.locator('.hero-subtitle');
    this.statItems = page.locator('.stat-item');

    // 快速访问
    this.actionCards = page.locator('.action-card');

    // 涨跌幅排行
    this.rankingsSection = page.locator('.rankings-section');

    // 空状态
    this.emptyState = page.locator('.empty-state');

    // 加载状态
    this.loadingState = page.locator('.loading-state');
  }

  /**
   * 访问首页
   */
  async goto(): Promise<void> {
    await this.navigate('/');
    await this.waitForLoad();
  }

  /**
   * 获取 Hero 标题文本
   */
  async getHeroTitle(): Promise<string> {
    return await this.heroTitle.textContent() || '';
  }

  /**
   * 获取统计项数量
   */
  async getStatCount(): Promise<number> {
    return await this.statItems.count();
  }

  /**
   * 获取统计值
   */
  async getStatValue(index: number): Promise<string> {
    const item = this.statItems.nth(index);
    return await item.locator('.stat-value').textContent() || '';
  }

  /**
   * 点击快速访问卡片
   */
  async clickActionCard(title: string): Promise<void> {
    await this.actionCards
      .filter({ hasText: title })
      .click();
  }

  /**
   * 获取快速访问卡片数量
   */
  async getActionCardCount(): Promise<number> {
    return await this.actionCards.count();
  }

  /**
   * 检查是否有排行数据
   */
  async hasRankings(): Promise<boolean> {
    return await this.rankingsSection.isVisible();
  }

  /**
   * 获取涨跌幅排行
   */
  async getRankingItems(type: 'rising' | 'falling'): Promise<string[]> {
    const card = this.page.locator(`.ranking-card.${type}`);
    const items = card.locator('.ranking-item');
    const count = await items.count();
    const texts: string[] = [];

    for (let i = 0; i < count; i++) {
      const text = await items.nth(i).textContent();
      if (text) texts.push(text);
    }

    return texts;
  }

  /**
   * 检查是否显示空状态
   */
  async isEmptyStateVisible(): Promise<boolean> {
    return await this.emptyState.isVisible();
  }

  /**
   * 点击添加基金按钮
   */
  async clickAddFundButton(): Promise<void> {
    await this.emptyState.locator('.btn-primary').click();
  }

  /**
   * 等待加载完成
   */
  async waitForLoadingComplete(): Promise<void> {
    await this.waitForElementHidden('.loading-state', 30000);
  }

  /**
   * 检查快速访问卡片标题
   */
  async getActionCardTitles(): Promise<string[]> {
    const count = await this.actionCards.count();
    const titles: string[] = [];

    for (let i = 0; i < count; i++) {
      const title = await this.actionCards.nth(i).locator('.action-title').textContent();
      if (title) titles.push(title);
    }

    return titles;
  }

  /**
   * 等待内容加载
   */
  async waitForContentLoaded(): Promise<void> {
    // 等待 Hero 区域加载
    await this.waitForElement('.hero-section');
    // 等待加载状态消失
    const loadingVisible = await this.loadingState.isVisible().catch(() => false);
    if (loadingVisible) {
      await this.waitForElementHidden('.loading-state');
    }
  }
}