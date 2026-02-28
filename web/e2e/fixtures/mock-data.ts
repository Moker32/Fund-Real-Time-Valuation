/**
 * Mock 数据定义
 * 用于 E2E 测试中模拟 API 响应
 */

// 基金 Mock 数据
export const mockFunds = [
  {
    code: '000001',
    name: '华夏成长混合',
    type: '混合型',
    estimateValue: 1.234,
    estimateChangePercent: 1.56,
    estimateAmount: 123.45,
    update_time: '2026-02-28 14:30:00',
  },
  {
    code: '000002',
    name: '华夏红利混合',
    type: '混合型',
    estimateValue: 2.345,
    estimateChangePercent: -0.89,
    estimateAmount: -234.56,
    update_time: '2026-02-28 14:30:00',
  },
  {
    code: '110022',
    name: '易方达消费行业',
    type: '股票型',
    estimateValue: 5.678,
    estimateChangePercent: 2.34,
    estimateAmount: 345.67,
    update_time: '2026-02-28 14:30:00',
  },
];

// 指数 Mock 数据
export const mockIndices = [
  {
    code: '000001',
    name: '上证指数',
    price: 3250.45,
    change: 25.67,
    changePercent: 0.79,
    volume: 4567890000,
    amount: 456789000000,
    time: '2026-02-28 15:00:00',
  },
  {
    code: '399001',
    name: '深证成指',
    price: 10890.23,
    change: -45.67,
    changePercent: -0.42,
    volume: 5678900000,
    amount: 567890000000,
    time: '2026-02-28 15:00:00',
  },
  {
    code: '399006',
    name: '创业板指',
    price: 2156.78,
    change: 12.34,
    changePercent: 0.57,
    volume: 1234567000,
    amount: 123456700000,
    time: '2026-02-28 15:00:00',
  },
];

// 商品 Mock 数据
export const mockCommodities = {
  gold: [
    {
      code: 'AU2506',
      name: '黄金2506',
      price: 485.56,
      change: 2.34,
      changePercent: 0.48,
      volume: 123456,
      time: '2026-02-28 15:00:00',
    },
  ],
  silver: [
    {
      code: 'AG2506',
      name: '白银2506',
      price: 6.234,
      change: -0.05,
      changePercent: -0.80,
      volume: 234567,
      time: '2026-02-28 15:00:00',
    },
  ],
  oil: [
    {
      code: 'SC2504',
      name: '原油2504',
      price: 567.8,
      change: 5.6,
      changePercent: 1.00,
      volume: 345678,
      time: '2026-02-28 15:00:00',
    },
  ],
};

// 商品分类 Mock 数据
export const mockCategories = [
  { id: 'precious_metals', name: '贵金属', count: 8 },
  { id: 'energy', name: '能源化工', count: 12 },
  { id: 'agricultural', name: '农产品', count: 15 },
  { id: 'nonferrous', name: '有色金属', count: 10 },
];

// 板块 Mock 数据
export const mockSectors = [
  {
    code: 'BK0001',
    name: '半导体',
    changePercent: 2.34,
    leadingStock: '中芯国际',
    leadingStockCode: '688981',
    leadingStockChange: 5.67,
    turnover: 123456789000,
    netInflow: 12345678900,
  },
  {
    code: 'BK0002',
    name: '新能源',
    changePercent: -1.23,
    leadingStock: '宁德时代',
    leadingStockCode: '300750',
    leadingStockChange: -2.34,
    turnover: 98765432100,
    netInflow: -8765432100,
  },
  {
    code: 'BK0003',
    name: '白酒',
    changePercent: 0.56,
    leadingStock: '贵州茅台',
    leadingStockCode: '600519',
    leadingStockChange: 1.23,
    turnover: 76543210000,
    netInflow: 5432100000,
  },
];

// 债券 Mock 数据
export const mockBonds = [
  {
    code: '019740',
    name: '24国债09',
    price: 102.35,
    change: 0.15,
    changePercent: 0.15,
    yield: 2.15,
  },
  {
    code: '110000',
    name: '24国债ETF',
    price: 125.67,
    change: 0.23,
    changePercent: 0.18,
    yield: 2.08,
  },
];

// 搜索基金 Mock 数据
export const mockSearchResults = [
  {
    code: '000001',
    name: '华夏成长混合',
    type: '混合型',
  },
  {
    code: '000002',
    name: '华夏红利混合',
    type: '混合型',
  },
  {
    code: '000003',
    name: '华夏优势增长混合',
    type: '混合型',
  },
];

// API 响应 Mock
export const mockApiResponses = {
  funds: {
    funds: mockFunds,
    total: mockFunds.length,
  },
  indices: {
    indices: mockIndices,
  },
  commodities: {
    categories: mockCategories,
    commodities: mockCommodities,
  },
  sectors: {
    sectors: mockSectors,
  },
  bonds: {
    bonds: mockBonds,
  },
  searchFunds: {
    results: mockSearchResults,
  },
};