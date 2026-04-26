// Fund Types

// K 线历史数据类型（OHLCV）
export interface FundHistory {
  time: string;       // 日期时间 (YYYY-MM-DD)
  open: number;       // 开盘价
  high: number;       // 最高价
  low: number;        // 最低价
  close: number;      // 收盘价
  volume: number;     // 成交量
}

// 分时数据点类型
export interface FundIntraday {
  time: string;       // 时间 (HH:mm 格式)
  price: number;      // 实时价格
  change?: number;    // 估算增长率 (%)
}

// Fund 类型添加日内数据字段
export interface Fund {
  code: string;
  name: string;
  netValue: number;
  netValueDate: string;
  prevNetValue?: number;
  prevNetValueDate?: string;
  estimateValue: number;
  estimateChange: number;
  estimateChangePercent: number;
  estimateTime?: string;
  type?: string;
  source?: string;
  isHolding?: boolean;  // 是否持有
  hasRealTimeEstimate?: boolean;  // 是否有实时估值（QDII/FOF等为false）
  qdiiEstimateChangePercent?: number;  // QDII 基金基于海外指数的估算涨跌幅(%)
  marketStatus?: string;  // QDII 基金对应海外市场交易状态: 'open' | 'closed' | 'pre_market' | 'after_hours'
  underlyingIndices?: Array<{ type: string; name: string; weight: number }>;  // QDII 基金跟踪的海外指数
  intervalReturns?: Record<string, number>;
  peerRank?: { category: string; rank: number; total: number; percentile: number };
  manager?: { name: string; tenure: string };
  sector?: string;  // 投资主题标签（如：白酒、新能源、医药等）
  conceptTags?: string[];  // 概念板块标签（如：CPO概念、AI芯片、商业航天等）
  industries?: Array<{ name: string; proportion: number }>;  // 行业配置
  history?: FundHistory[];  // 可选的历史 K 线数据
  intraday?: FundIntraday[];  // 可选的日内分时数据
}

// Commodity History Types
export interface CommodityHistory {
  symbol: string;
  name: string;
  price: number;
  currency: string;
  change: number;
  changePercent: number;
  high: number;
  low: number;
  open: number;
  prevClose: number;
  source?: string;
  timestamp: string;
  tradingStatus?: string; // 交易状态: 'open', 'closed'
}

// Commodity Types
export interface Commodity {
  symbol: string;
  name: string;
  price: number;
  currency: string;
  change: number;
  changePercent: number;
  high: number;
  low: number;
  open: number;
  prevClose: number;
  source: string;
  timestamp: string;
  intraday?: FundIntraday[];  // 日内分时数据
}

// Commodity Category Types
export interface CommodityCategoryItem {
  symbol: string;
  name: string;
  price: number;
  currency: string;
  change: number | null;
  changePercent: number;
  high: number | null;
  low: number | null;
  open: number | null;
  prevClose: number | null;
  source: string;
  timestamp: string;
}

export interface CommodityCategory {
  id: string;
  name: string;
  icon: string;
  commodities: CommodityCategoryItem[];
}

export interface CommodityCategoriesResponse {
  categories: CommodityCategory[];
  timestamp: string;
}

// Commodity History Types
export interface CommodityHistoryItem {
  date: string;
  price: number;
  change: number;
  changePercent: number;
  high: number;
  low: number;
  open: number;
  prevClose: number;
}

// Watched Commodity Types
export interface WatchedCommodity {
  symbol: string;
  name: string;
  category: string;
  addedAt: string;
}

export interface WatchlistResponse {
  watchlist: WatchedCommodity[];
  count: number;
  timestamp: string;
}

export interface CommoditySearchResult {
  symbol: string;
  name: string;
  exchange: string;
  currency: string;
  category: string;
}

export interface CommoditySearchResponse {
  query: string;
  results: CommoditySearchResult[];
  count: number;
  timestamp: string;
}

// Index Intraday Types
export interface IndexIntraday {
  time: string;       // 时间 (HH:mm 格式)
  price: number;      // 实时价格
  change?: number;    // 涨跌幅 (%)
}

export interface IndexIntradayResponse {
  index: string;
  symbol: string;
  name: string;
  data: IndexIntraday[];
  timestamp: string;
  open: number;
  high: number;
  low: number;
  close: number;
}

// Market Index Types
export interface MarketIndex {
  index: string;
  symbol: string;
  name: string;
  price: number;
  change: number;
  changePercent: number;
  currency: string;
  exchange?: string;
  timestamp: string;
  dataTimestamp?: string;   // 数据更新时间（ISO 格式）
  source: string;
  high?: number;
  low?: number;
  open?: number;
  prevClose?: number;
  region?: string;          // 区域: 'america', 'asia', 'europe', 'china', 'hk'
  tradingStatus?: string;   // 交易状态: 'open', 'closed', 'pre'
  marketTime?: string;     // 市场当前时间（用于判断状态）
  isDelayed?: boolean;     // 是否为延时数据
  history?: IndexHistory[];  // 历史K线数据（用于图表展示）
  intraday?: IndexIntraday[];  // 日内分时数据
}

export interface IndexListResponse {
  indices: MarketIndex[];
  timestamp: string;
}

// Index History Types
export interface IndexHistory {
  time: string;
  open: number | null;
  high: number | null;
  low: number | null;
  close: number | null;
  volume: number | null;
}

export interface IndexHistoryResponse {
  index: string;
  symbol: string;
  name: string;
  period: string;
  data: IndexHistory[];
  count: number;
  currency: string;
}

// Sector Types
export interface Sector {
  rank: number;
  name: string;
  code: string;
  price: number;
  change: number;
  changePercent: number;
  stockCount?: number;
  totalMarket?: string;
  turnover?: string;
  upCount: number;
  downCount: number;
  leadStock?: string;
  leadChange: number;
  // 资金流向字段
  mainInflow?: number;
  mainInflowPct?: number;
  smallInflow?: number;
  smallInflowPct?: number;
  mediumInflow?: number;
  mediumInflowPct?: number;
  largeInflow?: number;
  largeInflowPct?: number;
  hugeInflow?: number;
  hugeInflowPct?: number;
  source?: string;
  timestamp?: string;
}

export interface SectorListResponse {
  sectors: Sector[];
  timestamp: string;
  type: 'industry' | 'concept';
}

export interface SectorStock {
  rank: number;
  code: string;
  name: string;
  price: number;
  changePercent: number;
}

export interface SectorDetailResponse {
  sectorName: string;
  stocks: SectorStock[];
  count: number;
  timestamp: string;
}

// Overview Types
export interface Overview {
  totalValue: number;
  totalChange: number;
  totalChangePercent: number;
  fundCount: number;
  lastUpdated: string;
}

// Health Types
export interface HealthStatus {
  status: 'healthy' | 'degraded' | 'unhealthy';
  message: string;
  version: string;
  timestamp: string;
}

// Store State Types

// Economic Calendar Types
export interface EconomicEventItem {
  日期: string;
  时间: string;
  地区: string;
  事件: string;
  公布: number | null;
  预期: number | null;
  前值: number | null;
  重要性: number;
}

export interface EconomicEventsData {
  events: EconomicEventItem[];
  timestamp: string;
  date: string;
  source: string;
}

export interface WeiboSentimentItem {
  name: string;
  rate: number;
}

export interface WeiboSentimentData {
  sentiment: WeiboSentimentItem[];
  timestamp: string;
  period: string;
  source: string;
}

export interface SentimentAllData {
  economic: EconomicEventItem[] | null;
  weibo: WeiboSentimentItem[] | null;
  timestamp: string;
  source: string;
  errors: string[] | null;
}

