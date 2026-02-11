// Fund Types
export interface Fund {
  code: string;
  name: string;
  netValue: number;
  netValueDate: string;
  estimateValue: number;
  estimateChange: number;
  estimateChangePercent: number;
  estimateTime?: string;
  type?: string;
  source?: string;
  isHolding?: boolean;  // 是否持有
  hasRealTimeEstimate?: boolean;  // 是否有实时估值（QDII/FOF等为false）
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
}
