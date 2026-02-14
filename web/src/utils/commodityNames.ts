// 商品名称中英文映射
export const commodityNameMap: Record<string, string> = {
  // 贵金属
  'GC=F': '黄金 (COMEX)',
  'SG=f': '沪金 Au99.99',
  'PAXG-USD': 'Pax Gold',
  'SI=F': '白银 (COMEX)',
  'PT=F': '铂金',
  'PA=F': '钯金',
  'Gold Apr 26': '国际黄金',
  'Silver Mar 26': '国际白银',
  'Palladium Mar 26': '钯金期货',
  'Bitcoin Futures,Feb-2026': '比特币期货',
  'Ethereum Feb 26': '以太坊期货',
  'Corn Futures,Mar-2026': '玉米期货',

  // 能源
  'CL=F': 'WTI原油',
  'BZ=F': '布伦特原油',
  'NG=F': '天然气',
  'HO=F': '取暖油',
  'RB=F': '燃料油',

  // 基本金属
  'HG=F': '铜期货',
  'ALU': '铝现货',
  'ZN=F': '锌期货',
  'ZN=f': '锌',

  // 农产品
  'ZS=F': '大豆',
  'ZC=F': '玉米',
  'ZW=F': '小麦',
  'KC=F': '咖啡',
  'SB=F': '白糖',
  'LE=F': '活牛',
  'HE=F': '瘦肉猪',
  'ZR=F': '大米',
  'OJ=F': '橙汁',

  // 加密货币
  'BTC-USD': '比特币',
  'BTCUSDT': '比特币',
  'ETH-USD': '以太坊',
  'ETHUSDT': '以太坊',
  'BTC=F': '比特币期货',
  'ETH=F': '以太坊期货',
  'Bitcoin USD': '比特币',
  'Ethereum USD': '以太坊',

  // 通用
  'Bitcoin': '比特币',
  'Ethereum': '以太坊',
  'Gold': '黄金',
  'Silver': '白银',
  'Platinum': '铂金',
  'Palladium': '钯金',
  'Crude Oil': '原油',
  'Natural Gas': '天然气',
  'Copper': '铜',
  'Corn': '玉米',
  'Wheat': '小麦',
  'Soybeans': '大豆',
  'Coffee': '咖啡',
  'Sugar': '糖',
};

// 获取商品中文名称
export function getCommodityName(symbol: string, englishName: string): string {
  // 优先通过 symbol 查找
  if (commodityNameMap[symbol]) {
    return commodityNameMap[symbol];
  }
  // 通过英文名称查找
  if (commodityNameMap[englishName]) {
    return commodityNameMap[englishName];
  }
  // 模糊匹配
  for (const [key, value] of Object.entries(commodityNameMap)) {
    if (englishName.toLowerCase().includes(key.toLowerCase()) ||
        key.toLowerCase().includes(englishName.toLowerCase())) {
      return value;
    }
  }
  // 返回原始名称
  return englishName;
}

// 商品分类映射
export const commodityCategoryMap: Record<string, string> = {
  // 贵金属
  'GC=F': 'precious_metal',
  'SG=f': 'precious_metal',
  'SI=F': 'precious_metal',
  'PT=F': 'precious_metal',
  'PA=F': 'precious_metal',
  'PAXG-USD': 'precious_metal',
  // 能源
  'CL=F': 'energy',
  'BZ=F': 'energy',
  'NG=F': 'energy',
  // 基本金属
  'HG=F': 'base_metal',
  'ALU': 'base_metal',
  'ZN=f': 'base_metal',
  'NI=f': 'base_metal',
  // 农产品
  'ZS=F': 'agriculture',
  'ZC=F': 'agriculture',
  'ZW=F': 'agriculture',
  'KC=F': 'agriculture',
  'SB=F': 'agriculture',
  // 加密货币
  'BTC-USD': 'crypto',
  'BTCUSDT': 'crypto',
  'ETH-USD': 'crypto',
  'ETHUSDT': 'crypto',
  'BTC=F': 'crypto',
  'ETH=F': 'crypto',
};

// 根据 symbol 获取商品分类
export function getCommodityCategory(symbol: string): string {
  return commodityCategoryMap[symbol.toUpperCase()] || 'other';
}

// 商品对应的交易所映射
export const commodityExchangeMap: Record<string, string> = {
  // 上海黄金交易所
  'SG=f': 'sge',
  'Au99.99': 'sge',
  // COMEX 纽约商品交易所 (贵金属 + 能源 + 基本金属)
  'GC=F': 'comex',
  'SI=F': 'comex',
  'CL=F': 'comex',
  'BZ=F': 'comex',
  'HG=F': 'comex',
  'ZN=f': 'comex',
  // CME 芝加哥商品交易所
  'NG=F': 'cme',
  // CBOT 芝加哥期货交易所 (农产品) - 映射到 USA 市场
  'ZS=F': 'usa',
  'ZC=F': 'usa',
  'ZW=F': 'usa',
  // ICE 洲际交易所 (农产品) - 映射到 USA 市场
  'KC=F': 'usa',
  'SB=F': 'usa',
  // LBMA 伦敦金银市场协会
  'PAXG-USD': 'lbma',
  // 加密货币 (24/7)
  'BTC-USD': 'crypto',
  'BTCUSDT': 'crypto',
  'ETH-USD': 'crypto',
  'ETHUSDT': 'crypto',
  'BTC=F': 'crypto',
  'ETH=F': 'crypto',
};

// 根据 symbol 获取对应的市场
export function getCommodityMarket(symbol: string): string {
  return commodityExchangeMap[symbol.toUpperCase()] || 'china';
}
