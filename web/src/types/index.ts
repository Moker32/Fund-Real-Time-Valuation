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
  history?: FundHistory[];  // 可选的历史 K 线数据
  intraday?: FundIntraday[];  // 可选的日内分时数据
}

export interface FundListResponse {
  funds: Fund[];
  total: number;
  timestamp: string;
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
  source?: string;
  timestamp: string;
}

export interface CommodityListResponse {
  commodities: Commodity[];
  timestamp: string;
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

export interface CommodityHistoryResponse {
  commodity_type: string;
  name: string;
  history: CommodityHistoryItem[];
  timestamp: string;
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
  source: string;
  high?: number;
  low?: number;
  open?: number;
  prevClose?: number;
  region?: string;          // 区域: 'america', 'asia', 'europe', 'china', 'hk'
  tradingStatus?: string;   // 交易状态: 'open', 'closed', 'pre'
  marketTime?: string;     // 市场当前时间（用于判断状态）
}

export interface IndexListResponse {
  indices: MarketIndex[];
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

// API Response Types
export interface ApiResponse<T> {
  data: T;
  success: boolean;
  error?: string;
}

// Store State Types
export interface FundState {
  funds: Fund[];
  loading: boolean;
  error: string | null;
  lastUpdated: string | null;
}

export interface CommodityState {
  commodities: Commodity[];
  categories: CommodityCategory[];
  activeCategory: string | null;
  loading: boolean;
  error: string | null;
  lastUpdated: string | null;
}

export interface IndexState {
  indices: MarketIndex[];
  loading: boolean;
  error: string | null;
  lastUpdated: string | null;
}

export interface AppState {
  overview: Overview | null;
  health: HealthStatus | null;
  sidebarCollapsed: boolean;
  refreshInterval: number;
  autoRefresh: boolean;
  showChart: boolean;
}
