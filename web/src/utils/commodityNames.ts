// 商品名称中英文映射
export const commodityNameMap: Record<string, string> = {
  // 贵金属
  'GC=F': '黄金期货',
  'SI=F': '白银期货',
  'PT=F': '铂金期货',
  'PA=F': '钯金期货',
  'Gold Apr 26': '黄金期货',
  'Silver Mar 26': '白银期货',
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

  // 农产品
  'ZS=F': '大豆',
  'ZC=F': '玉米',
  'ZW=F': '小麦',
  'KC=F': '咖啡',
  'SB=F': '糖',
  'LE=F': '活牛',
  'HE=F': '瘦肉猪',
  'ZR=F': '大米',
  'OJ=F': '橙汁',

  // 加密货币
  'BTC-USD': '比特币',
  'ETH-USD': '以太坊',
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
