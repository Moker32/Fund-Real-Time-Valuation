/**
 * 商品页面页面对象
 */

import { Page, Locator, expect } from '@playwright/test';
import { BasePage } from './BasePage';

export class CommoditiesPage extends BasePage {
  // 定位器
  readonly categoryTabs: Locator;
  readonly commodityCards: Locator;
  readonly searchInput: Locator;
  readonly watchlistButton: Locator;

  constructor(page: Page) {
    super(page);

    this.categoryTabs = page.locator('.category-tab, .commodity-tab');
    this.commodityCards = page.locator('.commodity-card');
    this.searchInput = page.locator('.search-input, input[type="search"]');
    this.watchlistButton = page.locator('.watchlist-btn, .add-watchlist');
  }

  /**
   * 访问商品页面
   */
  async goto(): Promise<void> {
    await this.navigate('/commodities');
    await this.waitForLoad();
  }

  /**
   * 获取分类数量
   */
  async getCategoryCount(): Promise<number> {
    return await this.categoryTabs.count();
  }

  /**
   * 点击分类
   */
  async clickCategory(name: string): Promise<void> {
    await this.categoryTabs.filter({ hasText: name }).click();
  }

  /**
   * 获取商品卡片数量
   */
  async getCommodityCount(): Promise<number> {
    return await this.commodityCards.count();
  }

  /**
   * 搜索商品
   */
  async searchCommodity(keyword: string): Promise<void> {
    await this.searchInput.fill(keyword);
    await this.page.waitForTimeout(500);
  }

  /**
   * 添加到自选
   */
  async addToWatchlist(code: string): Promise<void> {
    const card = this.commodityCards.filter({ hasText: code });
    await card.locator('.watchlist-btn, .add-btn').click();
  }

  /**
   * 从自选移除
   */
  async removeFromWatchlist(code: string): Promise<void> {
    const card = this.commodityCards.filter({ hasText: code });
    await card.locator('.watchlist-btn.active, .remove-btn').click();
  }

  /**
   * 获取商品卡片信息
   */
  async getCommodityInfo(index: number): Promise<{
    code: string;
    name: string;
    price: string;
    change: string;
  }> {
    const card = this.commodityCards.nth(index);
    const code = await card.locator('.commodity-code, .code').textContent() || '';
    const name = await card.locator('.commodity-name, .name').textContent() || '';
    const price = await card.locator('.price').textContent() || '';
    const change = await card.locator('.change, .change-percent').textContent() || '';

    return { code, name, price, change };
  }

  /**
   * 等待商品列表加载
   */
  async waitForCommoditiesLoad(): Promise<void> {
    await this.waitForElement('.commodity-card', 30000);
  }
}