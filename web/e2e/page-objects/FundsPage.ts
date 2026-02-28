/**
 * 基金页面页面对象
 */

import { Page, Locator, expect } from '@playwright/test';
import { BasePage } from './BasePage';

export class FundsPage extends BasePage {
  // 定位器
  readonly pageTitle: Locator;
  readonly fundCards: Locator;
  readonly addButton: Locator;
  readonly searchInput: Locator;
  readonly searchResults: Locator;
  readonly confirmDialog: Locator;
  readonly emptyState: Locator;
  readonly loadingState: Locator;

  constructor(page: Page) {
    super(page);

    this.pageTitle = page.locator('.section-title, h2').first();
    this.fundCards = page.locator('.fund-card');
    this.addButton = page.locator('.btn-add, .btn-primary, [data-testid="add-fund"]').first();
    this.searchInput = page.locator('.search-input, input[type="search"], input[placeholder*="搜索"], input[placeholder*="基金代码"]');
    this.searchResults = page.locator('.search-results .result-item, .search-result-item, .dialog-fund-item');
    this.confirmDialog = page.locator('.confirm-dialog, .modal, [role="dialog"]');
    this.emptyState = page.locator('.empty-state');
    this.loadingState = page.locator('.loading-state');
  }

  /**
   * 访问基金页面
   */
  async goto(): Promise<void> {
    await this.navigate('/funds');
    await this.waitForLoad();
  }

  /**
   * 获取基金卡片数量
   */
  async getFundCount(): Promise<number> {
    return await this.fundCards.count();
  }

  /**
   * 点击添加基金按钮
   */
  async clickAddFund(): Promise<void> {
    await this.addButton.click();
  }

  /**
   * 搜索基金
   */
  async searchFund(keyword: string): Promise<void> {
    await this.searchInput.fill(keyword);
    // 等待搜索结果
    await this.page.waitForTimeout(500);
  }

  /**
   * 选择搜索结果
   */
  async selectSearchResult(index: number = 0): Promise<void> {
    await this.searchResults.nth(index).click();
  }

  /**
   * 确认添加
   */
  async confirmAdd(): Promise<void> {
    const confirmBtn = this.confirmDialog.locator('.confirm-btn, .btn-confirm, button:has-text("确认")');
    await confirmBtn.click();
  }

  /**
   * 取消添加
   */
  async cancelAdd(): Promise<void> {
    const cancelBtn = this.confirmDialog.locator('.cancel-btn, .btn-cancel, button:has-text("取消")');
    await cancelBtn.click();
  }

  /**
   * 删除基金
   */
  async deleteFund(code: string): Promise<void> {
    const card = this.fundCards.filter({ hasText: code });
    const deleteBtn = card.locator('.delete-btn, .btn-delete, [data-testid="delete"]');
    await deleteBtn.click();
  }

  /**
   * 确认删除
   */
  async confirmDelete(): Promise<void> {
    const confirmBtn = this.confirmDialog.locator('.confirm-btn, button:has-text("确认")');
    await confirmBtn.click();
  }

  /**
   * 获取基金卡片信息
   */
  async getFundCardInfo(index: number): Promise<{
    code: string;
    name: string;
    change: string;
  }> {
    const card = this.fundCards.nth(index);
    const code = await card.locator('.fund-code, .code').textContent() || '';
    const name = await card.locator('.fund-name, .name').textContent() || '';
    const change = await card.locator('.change-percent, .percent').textContent() || '';

    return { code, name, change };
  }

  /**
   * 检查是否显示空状态
   */
  async isEmptyStateVisible(): Promise<boolean> {
    return await this.emptyState.isVisible();
  }

  /**
   * 等待基金列表加载
   */
  async waitForFundsLoad(): Promise<void> {
    await this.waitForElement('.fund-card, .empty-state', 30000);
  }

  /**
   * 刷新基金列表
   */
  async refreshFunds(): Promise<void> {
    const refreshBtn = this.page.locator('.refresh-btn, [data-testid="refresh"]');
    if (await refreshBtn.isVisible()) {
      await refreshBtn.click();
    }
  }

  /**
   * 验证基金存在
   */
  async assertFundExists(code: string): Promise<void> {
    const card = this.fundCards.filter({ hasText: code });
    await expect(card).toBeVisible();
  }

  /**
   * 验证基金不存在
   */
  async assertFundNotExists(code: string): Promise<void> {
    const card = this.fundCards.filter({ hasText: code });
    await expect(card).not.toBeVisible();
  }
}