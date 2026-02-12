# 大宗商品关注管理功能设计

## 概述

允许用户通过输入任意 yfinance 代码自定义关注大宗商品，数据存储在本地配置文件 `~/.fund-tui/commodities.yaml`，支持代码和名称搜索，商品分类自动识别。

## 数据模型

### 配置文件格式

```yaml
# ~/.fund-tui/commodities.yaml
watched_commodities:
  - symbol: GC=F
    name: 黄金
    category: precious_metal
    added_at: 2026-02-12T10:00:00Z
  - symbol: SI=F
    name: 白银
    category: precious_metal
    added_at: 2026-02-12T10:05:00Z
```

### TypeScript 类型定义

```typescript
interface WatchedCommodity {
  symbol: string;      // 商品代码 (GC=F, ZS=F...)
  name: string;         // 显示名称
  category: string;     // 分类 (precious_metal/energy/base_metal/other)
  addedAt: string;     // 添加时间 (ISO 8601)
}

interface CommoditySearchResult {
  symbol: string;      // 商品代码
  name: string;         // 商品名称
  exchange: string;     // 交易所
  currency: string;     // 货币
  category: string;    // 识别的分类
}
```

## 分类自动识别规则

| 分类 | 商品代码 | 说明 |
|------|---------|------|
| precious_metal | `GC=F`, `SI=F`, `PL=F`, `PA=F` | 黄金、白银、铂金、钯金 |
| energy | `CL=F`, `BZ=F`, `NG=F`, `HO=F` | WTI原油、布伦特原油、天然气、燃油 |
| base_metal | `HG=F`, `AL=F`, `ZN=F`, `NI=F` | 铜、铝、锌、镍 |
| agriculture | `ZS=F`, `ZC=F`, `ZW=F`, `KC=F` | 大豆、玉米、小麦、咖啡 |
| other | - | 未识别的商品 |

## API 设计

| 端点 | 方法 | 功能 |
|------|------|------|
| `/api/commodities/search?q=gc` | GET | 搜索 yfinance 商品 |
| `/api/commodities/watchlist` | GET | 获取关注列表 |
| `/api/commodities/watchlist` | POST | 添加关注商品 |
| `/api/commodities/watchlist/{symbol}` | DELETE | 移除关注商品 |
| `/api/commodities/watchlist/{symbol}` | PUT | 更新商品名称 |
| `/api/commodities/available` | GET | 获取所有可用商品 |

### 搜索 API 响应

```json
{
  "query": "gc",
  "results": [
    {
      "symbol": "GC=F",
      "name": "COMEX Gold",
      "exchange": "CMX",
      "currency": "USD",
      "category": "precious_metal"
    }
  ]
}
```

## 后端实现

### 文件结构

```
src/
├── config/
│   └── commodities_config.py    # 关注商品配置管理
├── datasources/
│   └── commodity_source.py       # 添加 search_commodity() 方法
└── db/
    └── commodity_repo.py          # 添加仓储方法
api/
└── routes/
    └── commodities.py           # 添加关注列表相关端点
```

### 核心方法

```python
# config/commodities_config.py
class CommoditiesConfig:
    @staticmethod
    def get_watched_commodities() -> list[dict]:
        """获取关注列表"""

    @staticmethod
    def add_watched_commodity(symbol: str, name: str, category: str) -> bool:
        """添加关注商品"""

    @staticmethod
    def remove_watched_commodity(symbol: str) -> bool:
        """移除关注商品"""

    @staticmethod
    def update_watched_commodity_name(symbol: str, name: str) -> bool:
        """更新商品名称"""

    @staticmethod
    def identify_category(symbol: str) -> str:
        """自动识别商品分类"""
```

## 前端实现

### 组件结构

```
web/src/
├── stores/
│   └── commodityStore.ts      # 添加 watchlist 相关方法
├── components/
│   └── CommoditySearchDialog.vue  # 搜索添加对话框
│       ├── SearchInput.vue    # 搜索输入组件
│       └── SearchResult.vue   # 搜索结果列表
└── views/
    └── CommoditiesView.vue    # 添加添加按钮入口
```

### Store 方法扩展

```typescript
// commodityStore.ts
interface CommodityStore {
  // 现有方法...

  // 关注列表
  watchedCommodities: WatchedCommodity[];

  // 新增方法
  fetchWatchedCommodities(): Promise<void>;
  searchCommodities(query: string): Promise<CommoditySearchResult[]>;
  addToWatchlist(symbol: string, name: string, category: string): Promise<void>;
  removeFromWatchlist(symbol: string): Promise<void>;
  updateWatchlistName(symbol: string, name: string): Promise<void>;
}
```

## 交互流程

### 添加商品

1. 用户点击商品页面右上角 "+" 按钮
2. 弹出搜索对话框
3. 输入商品代码或名称（如 "GC" 或 "黄金"）
4. 实时搜索 yfinance 显示结果列表
5. 点击结果项添加到关注列表
6. 弹出成功提示

### 移除商品

1. 鼠标悬停在商品卡片上
2. 点击右上角 "..." 菜单
3. 选择"移除关注"
4. 弹出确认对话框
5. 确认后移除并显示提示

## 注意事项

- 配置文件修改后需要重新加载或监听文件变化
- 搜索需要防抖（300-500ms）
- 商品代码不区分大小写
- 重复添加同一代码应提示已存在
