# 数据字典

本文档记录基金实时估值 Web 应用的所有数据结构，包括 API 模型、配置模型、数据库表和前端类型定义。

---

## 1. API 响应模型 (api/models.py)

### 1.1 FundResponse - 基金响应模型

| 字段 | 类型 | 别名 | 描述 |
|------|------|------|------|
| code | string | fund_code | 基金代码 |
| name | string | - | 基金名称 |
| type | string \| null | - | 基金类型（股票型、混合型、债券型、QDII等） |
| netValue | float \| null | unit_net_value | 最新单位净值 |
| netValueDate | string \| null | net_value_date | 净值日期 |
| prevNetValue | float \| null | prev_net_value | 上一交易日净值 |
| prevNetValueDate | string \| null | prev_net_value_date | 上一交易日净值日期 |
| estimateValue | float \| null | estimated_net_value | 估值 |
| estimateChangePercent | float \| null | estimated_growth_rate | 估算增长率(%) |
| estimateChange | float \| null | - | 估算涨跌额 |
| estimateTime | string \| null | estimate_time | 估值时间 |
| source | string | - | 数据源 |
| isHolding | boolean | - | 是否持有该基金 |
| hasRealTimeEstimate | boolean | has_real_time_estimate | 是否有实时估值 |

### 1.2 CommodityResponse - 商品响应模型

| 字段 | 类型 | 描述 |
|------|------|------|
| commodity | string \| null | 商品类型 |
| symbol | string | 交易符号 |
| name | string | 商品名称 |
| price | float | 当前价格 |
| change | float \| null | 涨跌额 |
| changePercent | float \| null | change_percent - 涨跌幅(%) |
| currency | string \| null | 货币 |
| exchange | string \| null | 交易所 |
| timestamp | string \| null | 更新时间 |
| source | string | 数据源 |
| high | float \| null | 最高价 |
| low | float \| null | 最低价 |
| open | float \| null | 开盘价 |
| prevClose | float \| null | prev_close - 昨收价 |

### 1.3 HealthResponse - 健康检查响应模型

| 字段 | 类型 | 描述 |
|------|------|------|
| status | string | 服务状态 |
| version | string | 应用版本 |
| timestamp | datetime | 检查时间 |

### 1.4 DataSourceHealthItem - 数据源健康状态项

| 字段 | 类型 | 描述 |
|------|------|------|
| source | string | 数据源名称 |
| status | string | 健康状态 |
| response_time_ms | float \| null | 响应时间(ms) |

### 1.5 HealthDetailResponse - 详细健康检查响应模型

| 字段 | 类型 | 描述 |
|------|------|------|
| status | string | 服务状态 |
| version | string | 应用版本 |
| timestamp | datetime | 检查时间 |
| total_sources | int | 数据源总数 |
| healthy_count | int | 健康数据源数 |
| unhealthy_count | int | 不健康数据源数 |
| data_sources | list[DataSourceHealthItem] | 数据源健康状态列表 |

### 1.6 ErrorResponse - 错误响应模型

| 字段 | 类型 | 描述 |
|------|------|------|
| success | boolean | 是否成功（默认 false） |
| error | string | 错误类型 |
| detail | string \| null | 详细错误信息 |
| timestamp | string | 错误发生时间 |

### 1.7 OverviewResponse - 市场概览响应模型

| 字段 | 类型 | 别名 | 描述 |
|------|------|------|------|
| totalValue | float | - | 持仓总值 |
| totalChange | float | - | 今日涨跌金额 |
| totalChangePercent | float | - | 今日涨跌百分比 |
| fundCount | int | - | 基金数量 |
| lastUpdated | string | - | 更新时间 |

### 1.8 AddFundRequest - 添加基金请求模型

| 字段 | 类型 | 描述 |
|------|------|------|
| code | string | 基金代码（6位数字） |
| name | string | 基金名称（1-100字符） |

### 1.9 AddFundResponse - 添加基金响应模型

| 字段 | 类型 | 描述 |
|------|------|------|
| success | boolean | 是否成功（默认 true） |
| message | string | 响应消息 |
| fund | dict | 添加的基金信息 |

### 1.10 FundIntradayPoint - 基金日内分时数据点

| 字段 | 类型 | 描述 |
|------|------|------|
| time | string | 时间，格式: HH:mm |
| price | float | 估算净值/价格 |
| change | float \| null | 估算增长率(%) |

### 1.11 FundIntradayResponse - 基金日内分时数据响应模型

| 字段 | 类型 | 描述 |
|------|------|------|
| fund_code | string | 基金代码 |
| name | string | 基金名称 |
| date | string | 日期，格式: YYYY-MM-DD |
| data | list[FundIntradayPoint] | 日内分时数据点列表 |
| count | int | 数据点数量 |
| source | string | 数据源（默认 "fund123"） |

---

## 2. 配置模型 (src/config/models.py)

### 2.1 Theme - 主题枚举

| 值 | 描述 |
|------|------|
| light | 浅色主题 |
| dark | 深色主题 |

### 2.2 DataSource - 数据源标识枚举

| 值 | 描述 |
|------|------|
| sina | 新浪财经（基金） |
| eastmoney | 东方财富（基金） |
| alpha_vantage | Alpha Vantage（商品） |
| akshare | AKShare（商品/指数） |
| sina_news | 新浪财经（新闻） |
| eastmoney_news | 东方财富（新闻） |

### 2.3 Fund - 基金基础模型

| 字段 | 类型 | 描述 |
|------|------|------|
| code | string | 基金代码 |
| name | string | 基金名称 |

### 2.4 Holding - 持仓模型（继承 Fund）

| 字段 | 类型 | 描述 |
|------|------|------|
| code | string | 基金代码（继承） |
| name | string | 基金名称（继承） |
| shares | float | 持有份额（默认 0.0） |
| cost | float | 成本价（默认 0.0） |
| total_cost | property | 计算总成本 = shares * cost |

### 2.5 Commodity - 商品模型

| 字段 | 类型 | 描述 |
|------|------|------|
| symbol | string | 商品代码/符号 |
| name | string | 商品名称 |
| source | string | 数据源标识（默认 akshare） |

### 2.6 AppConfig - 应用主配置

| 字段 | 类型 | 描述 |
|------|------|------|
| refresh_interval | int | 刷新频率（秒，默认 30） |
| theme | string | 主题（默认 dark） |
| default_fund_source | string | 默认基金数据源（默认 sina） |
| max_history_points | int | 历史数据最大点数（默认 100） |
| enable_auto_refresh | bool | 是否启用自动刷新（默认 True） |
| show_profit_loss | bool | 是否显示盈亏（默认 True） |

### 2.7 FundList - 基金列表容器

| 字段 | 类型 | 描述 |
|------|------|------|
| watchlist | list[Fund] | 自选列表 |
| holdings | list[Holding] | 持仓列表 |

### 2.8 CommodityList - 商品列表容器

| 字段 | 类型 | 描述 |
|------|------|------|
| commodities | list[Commodity] | 商品列表 |

### 2.9 AlertDirection - 预警方向枚举

| 值 | 描述 |
|------|------|
| above | 高于目标价 |
| below | 低于目标价 |

### 2.10 PriceAlert - 价格预警模型

| 字段 | 类型 | 描述 |
|------|------|------|
| fund_code | string | 基金代码 |
| fund_name | string | 基金名称 |
| target_price | float | 目标价格 |
| direction | string | 预警方向（默认 above） |
| triggered | bool | 是否已触发（默认 False） |
| created_at | datetime | 创建时间 |

### 2.11 NotificationConfig - 通知配置模型

| 字段 | 类型 | 描述 |
|------|------|------|
| enabled | bool | 是否启用通知（默认 True） |
| price_alerts | list[PriceAlert] | 价格预警列表 |
| daily_summary | bool | 每日汇总（默认 False） |
| alert_sound | bool | 预警声音（默认 False） |

---

## 3. 数据库表 (src/db/database.py)

### 3.1 fund_config - 基金配置表

| 字段 | 类型 | 描述 |
|------|------|------|
| code | TEXT PRIMARY KEY | 基金代码 |
| name | TEXT NOT NULL | 基金名称 |
| watchlist | INTEGER DEFAULT 1 | 是否在自选（1=是，0=否） |
| shares | REAL DEFAULT 0 | 持有份额 |
| cost | REAL DEFAULT 0 | 成本价 |
| is_hold | INTEGER DEFAULT 0 | 持有标记（1=持有，0=不持有） |
| sector | TEXT DEFAULT '' | 板块标注 |
| notes | TEXT DEFAULT '' | 备注 |
| created_at | TEXT | 创建时间 |
| updated_at | TEXT | 更新时间 |

**索引**: PRIMARY KEY (code)

### 3.2 commodity_config - 商品配置表

| 字段 | 类型 | 描述 |
|------|------|------|
| symbol | TEXT PRIMARY KEY | 商品代码/符号 |
| name | TEXT NOT NULL | 商品名称 |
| source | TEXT DEFAULT 'akshare' | 数据源 |
| enabled | INTEGER DEFAULT 1 | 是否启用（1=启用，0=禁用） |
| notes | TEXT DEFAULT '' | 备注 |
| created_at | TEXT | 创建时间 |
| updated_at | TEXT | 更新时间 |

**索引**: PRIMARY KEY (symbol)

### 3.3 fund_history - 基金净值历史表

| 字段 | 类型 | 描述 |
|------|------|------|
| id | INTEGER PRIMARY KEY AUTOINCREMENT | 自增ID |
| fund_code | TEXT NOT NULL | 基金代码 |
| fund_name | TEXT | 基金名称 |
| date | TEXT NOT NULL | 日期 |
| unit_net_value | REAL | 单位净值 |
| accumulated_net_value | REAL | 累计净值 |
| estimated_value | REAL | 估算净值 |
| growth_rate | REAL | 增长率 |
| fetched_at | TEXT | 抓取时间 |

**索引**: UNIQUE (fund_code, date), FOREIGN KEY (fund_code) -> fund_config(code)

### 3.4 news_cache - 新闻缓存表

| 字段 | 类型 | 描述 |
|------|------|------|
| id | INTEGER PRIMARY KEY AUTOINCREMENT | 自增ID |
| title | TEXT NOT NULL | 标题 |
| url | TEXT UNIQUE | 链接 |
| source | TEXT | 来源 |
| category | TEXT | 分类 |
| publish_time | TEXT | 发布时间 |
| content | TEXT | 内容 |
| fetched_at | TEXT | 抓取时间 |
| created_at | TEXT DEFAULT (datetime('now')) | 创建时间 |

**索引**: UNIQUE (url)

### 3.5 fund_intraday_cache - 基金日内分时缓存表

| 字段 | 类型 | 描述 |
|------|------|------|
| id | INTEGER PRIMARY KEY AUTOINCREMENT | 自增ID |
| fund_code | TEXT NOT NULL | 基金代码 |
| date | TEXT NOT NULL | 日期 (YYYY-MM-DD) |
| time | TEXT NOT NULL | 时间 (HH:mm) |
| price | REAL NOT NULL | 估算净值 |
| change_rate | REAL | 涨跌率 |
| fetched_at | TEXT | 抓取时间 |

**索引**: UNIQUE (fund_code, date, time)

### 3.6 fund_daily_cache - 基金每日缓存表

| 字段 | 类型 | 描述 |
|------|------|------|
| id | INTEGER PRIMARY KEY AUTOINCREMENT | 自增ID |
| fund_code | TEXT NOT NULL | 基金代码 |
| date | TEXT NOT NULL | 日期 (YYYY-MM-DD) |
| unit_net_value | REAL | 单位净值 |
| accumulated_net_value | REAL | 累计净值 |
| estimated_value | REAL | 估算净值 |
| change_rate | REAL | 日增长率 |
| fetched_at | TEXT | 抓取时间 |

**索引**: UNIQUE (fund_code, date)

### 3.7 fund_basic_info - 基金基本信息表

| 字段 | 类型 | 描述 |
|------|------|------|
| code | TEXT PRIMARY KEY | 基金代码 |
| name | TEXT | 基金全称 |
| short_name | TEXT | 基金简称 |
| type | TEXT | 基金类型 |
| fund_key | TEXT | 基金关键字 |
| net_value | REAL | 单位净值 |
| net_value_date | TEXT | 净值日期 |
| establishment_date | TEXT | 成立日期 |
| manager | TEXT | 基金管理人 |
| custodian | TEXT | 基金托管人 |
| fund_scale | REAL | 基金规模 |
| scale_date | TEXT | 规模日期 |
| risk_level | TEXT | 风险等级 |
| full_name | TEXT | 基金完整名称 |
| fetched_at | TEXT | 抓取时间 |
| updated_at | TEXT | 更新时间 |

**索引**: PRIMARY KEY (code)

### 3.8 commodity_cache - 商品行情缓存表

| 字段 | 类型 | 描述 |
|------|------|------|
| id | INTEGER PRIMARY KEY AUTOINCREMENT | 自增ID |
| commodity_type | TEXT NOT NULL | 商品类型 |
| symbol | TEXT | 交易符号 |
| name | TEXT | 商品名称 |
| price | REAL DEFAULT 0 | 当前价格 |
| change | REAL DEFAULT 0 | 涨跌额 |
| change_percent | REAL DEFAULT 0 | 涨跌幅(%) |
| currency | TEXT DEFAULT 'USD' | 货币 |
| exchange | TEXT | 交易所 |
| high | REAL DEFAULT 0 | 最高价 |
| low | REAL DEFAULT 0 | 最低价 |
| open | REAL DEFAULT 0 | 开盘价 |
| prev_close | REAL DEFAULT 0 | 昨收价 |
| source | TEXT | 数据源 |
| timestamp | TEXT NOT NULL | 更新时间 |
| created_at | TEXT DEFAULT (datetime('now', 'localtime')) | 创建时间 |

**索引**: INDEX (commodity_type), INDEX (created_at)

---

## 4. 数据库模型类 (src/db/database.py)

### 4.1 FundConfig - 基金配置数据类

| 字段 | 类型 | 描述 |
|------|------|------|
| code | str | 基金代码 |
| name | str | 基金名称 |
| watchlist | int | SQLite 整数（1=True，0=False） |
| shares | float | 持有份额 |
| cost | float | 成本价 |
| is_hold | int | 持有标记（1=持有，0=不持有） |
| sector | str | 板块标注 |
| notes | str | 备注 |
| created_at | str | 创建时间 |
| updated_at | str | 更新时间 |

**属性**:
- `is_watchlist`: property -> bool - 将整数转换为布尔值
- `is_holding`: property -> bool - 检查是否标记为持有

### 4.2 CommodityConfig - 商品配置数据类

| 字段 | 类型 | 描述 |
|------|------|------|
| symbol | str | 商品代码/符号 |
| name | str | 商品名称 |
| source | str | 数据源（默认 "akshare"） |
| enabled | int | SQLite 整数（1=True，0=False） |
| notes | str | 备注 |
| created_at | str | 创建时间 |
| updated_at | str | 更新时间 |

**属性**:
- `is_enabled`: property -> bool - 将整数转换为布尔值

### 4.3 FundHistoryRecord - 基金净值历史记录

| 字段 | 类型 | 描述 |
|------|------|------|
| id | int \| None | 数据库自增ID |
| fund_code | str | 基金代码 |
| fund_name | str | 基金名称 |
| date | str | 日期 |
| unit_net_value | float | 单位净值 |
| accumulated_net_value | float \| None | 累计净值 |
| estimated_value | float \| None | 估算净值 |
| growth_rate | float \| None | 增长率 |
| fetched_at | str | 抓取时间 |

### 4.4 NewsRecord - 新闻记录

| 字段 | 类型 | 描述 |
|------|------|------|
| title | str | 标题 |
| url | str | 链接 |
| source | str | 来源 |
| category | str | 分类 |
| publish_time | str | 发布时间 |
| content | str | 内容 |
| fetched_at | str | 抓取时间 |

### 4.5 FundIntradayRecord - 基金日内分时数据记录

| 字段 | 类型 | 描述 |
|------|------|------|
| id | int \| None | 数据库自增ID |
| fund_code | str | 基金代码 |
| date | str | 日期 (YYYY-MM-DD) |
| time | str | 时间 (HH:mm) |
| price | float | 估算净值 |
| change_rate | float \| None | 涨跌率 |
| fetched_at | str | 抓取时间 |

### 4.6 FundDailyRecord - 基金每日缓存数据记录

| 字段 | 类型 | 描述 |
|------|------|------|
| id | int \| None | 数据库自增ID |
| fund_code | str | 基金代码 |
| date | str | 日期 (YYYY-MM-DD) |
| unit_net_value | float \| None | 单位净值 |
| accumulated_net_value | float \| None | 累计净值 |
| estimated_value | float \| None | 估算净值 |
| change_rate | float \| None | 日增长率 |
| fetched_at | str | 抓取时间 |

### 4.7 FundBasicInfo - 基金基本信息

| 字段 | 类型 | 描述 |
|------|------|------|
| code | str | 基金代码 |
| name | str | 基金全称 |
| short_name | str | 基金简称 |
| type | str | 基金类型 |
| fund_key | str | 基金关键字 |
| net_value | float \| None | 单位净值 |
| net_value_date | str | 净值日期 |
| establishment_date | str | 成立日期 |
| manager | str | 基金管理人 |
| custodian | str | 基金托管人 |
| fund_scale | float \| None | 基金规模 |
| scale_date | str | 规模日期 |
| risk_level | str | 风险等级 |
| full_name | str | 基金完整名称 |
| fetched_at | str | 抓取时间 |
| updated_at | str | 更新时间 |

---

## 5. 前端类型定义 (web/src/types/index.ts)

### 5.1 FundHistory - K线历史数据类型（OHLCV）

| 字段 | 类型 | 描述 |
|------|------|------|
| time | string | 日期时间 (YYYY-MM-DD) |
| open | number | 开盘价 |
| high | number | 最高价 |
| low | number | 最低价 |
| close | number | 收盘价 |
| volume | number | 成交量 |

### 5.2 FundIntraday - 分时数据点类型

| 字段 | 类型 | 描述 |
|------|------|------|
| time | string | 时间 (HH:mm 格式) |
| price | number | 实时价格 |

### 5.3 Fund - 基金类型

| 字段 | 类型 | 描述 |
|------|------|------|
| code | string | 基金代码 |
| name | string | 基金名称 |
| netValue | number | 单位净值 |
| netValueDate | string | 净值日期 |
| prevNetValue | number \| undefined | 上一交易日净值 |
| prevNetValueDate | string \| undefined | 上一交易日净值日期 |
| estimateValue | number | 估算净值 |
| estimateChange | number | 估算涨跌额 |
| estimateChangePercent | number | 估算涨跌幅(%) |
| estimateTime | string \| undefined | 估值时间 |
| type | string \| undefined | 基金类型 |
| source | string \| undefined | 数据源 |
| isHolding | boolean \| undefined | 是否持有 |
| hasRealTimeEstimate | boolean \| undefined | 是否有实时估值 |
| history | FundHistory[] \| undefined | 历史 K 线数据 |
| intraday | FundIntraday[] \| undefined | 日内分时数据 |

### 5.4 FundListResponse - 基金列表响应类型

| 字段 | 类型 | 描述 |
|------|------|------|
| funds | Fund[] | 基金列表 |
| total | number | 基金总数 |
| timestamp | string | 响应时间戳 |

### 5.5 Commodity - 商品类型

| 字段 | 类型 | 描述 |
|------|------|------|
| symbol | string | 商品代码 |
| name | string | 商品名称 |
| price | number | 当前价格 |
| currency | string | 货币 |
| change | number | 涨跌额 |
| changePercent | number | 涨跌幅(%) |
| high | number | 最高价 |
| low | number | 最低价 |
| open | number | 开盘价 |
| prevClose | number | 昨收价 |
| source | string \| undefined | 数据源 |
| timestamp | string | 更新时间 |
| tradingStatus | string \| undefined | 交易状态 ('open', 'closed') |

### 5.6 CommodityCategoryItem - 商品分类项类型

| 字段 | 类型 | 描述 |
|------|------|------|
| symbol | string | 商品代码 |
| name | string | 商品名称 |
| price | number | 当前价格 |
| currency | string | 货币 |
| change | number \| null | 涨跌额 |
| changePercent | number | 涨跌幅(%) |
| high | number \| null | 最高价 |
| low | number \| null | 最低价 |
| open | number \| null | 开盘价 |
| prevClose | number \| null | 昨收价 |
| source | string | 数据源 |
| timestamp | string | 更新时间 |

### 5.7 CommodityCategory - 商品分类类型

| 字段 | 类型 | 描述 |
|------|------|------|
| id | string | 分类ID |
| name | string | 分类名称 |
| icon | string | 图标 |
| commodities | CommodityCategoryItem[] | 商品列表 |

### 5.8 CommodityHistoryItem - 商品历史数据类型

| 字段 | 类型 | 描述 |
|------|------|------|
| date | string | 日期 |
| price | number | 价格 |
| change | number | 涨跌额 |
| changePercent | number | 涨跌幅(%) |
| high | number | 最高价 |
| low | number | 最低价 |
| open | number | 开盘价 |
| prevClose | number | 昨收价 |

### 5.9 WatchedCommodity - 关注商品类型

| 字段 | 类型 | 描述 |
|------|------|------|
| symbol | string | 商品代码 |
| name | string | 商品名称 |
| category | string | 分类 |
| added_at | string | 添加时间 |

### 5.10 MarketIndex - 市场指数类型

| 字段 | 类型 | 描述 |
|------|------|------|
| index | string | 指数代码 |
| symbol | string | 交易符号 |
| name | string | 指数名称 |
| price | number | 当前价格 |
| change | number | 涨跌额 |
| changePercent | number | 涨跌幅(%) |
| currency | string | 货币 |
| exchange | string \| undefined | 交易所 |
| timestamp | string | 更新时间 |
| dataTimestamp | string \| undefined | 数据更新时间 |
| timezone | string \| undefined | 市场时区 |
| source | string | 数据源 |
| high | number \| undefined | 最高价 |
| low | number \| undefined | 最低价 |
| open | number \| undefined | 开盘价 |
| prevClose | number \| undefined | 昨收价 |
| region | string \| undefined | 区域 ('america', 'asia', 'europe', 'china', 'hk') |
| tradingStatus | string \| undefined | 交易状态 ('open', 'closed', 'pre') |
| marketTime | string \| undefined | 市场当前时间 |
| isDelayed | boolean \| undefined | 是否为延时数据 |

### 5.11 Sector - 板块类型

| 字段 | 类型 | 描述 |
|------|------|------|
| rank | number | 排名 |
| name | string | 板块名称 |
| code | string | 板块代码 |
| price | number | 当前价格 |
| change | number | 涨跌额 |
| changePercent | number | 涨跌幅(%) |
| totalMarket | string \| undefined | 总市值 |
| turnover | string \| undefined | 成交额 |
| upCount | number | 上涨数量 |
| downCount | number | 下跌数量 |
| leadStock | string \| undefined | 领涨股票 |
| leadChange | number | 领涨涨幅 |
| mainInflow | number \| undefined | 主力净流入 |
| mainInflowPct | number \| undefined | 主力净流入占比 |
| smallInflow | number \| undefined | 小单净流入 |
| smallInflowPct | number \| undefined | 小单净流入占比 |
| mediumInflow | number \| undefined | 中单净流入 |
| mediumInflowPct | number \| undefined | 中单净流入占比 |
| largeInflow | number \| undefined | 大单净流入 |
| largeInflowPct | number \| undefined | 大单净流入占比 |
| hugeInflow | number \| undefined | 超大单净流入 |
| hugeInflowPct | number \| undefined | 超大单净流入占比 |
| source | string \| undefined | 数据源 |
| timestamp | string \| undefined | 更新时间 |

### 5.12 Overview - 市场概览类型

| 字段 | 类型 | 描述 |
|------|------|------|
| totalValue | number | 持仓总值 |
| totalChange | number | 今日涨跌金额 |
| totalChangePercent | number | 今日涨跌百分比 |
| fundCount | number | 基金数量 |
| lastUpdated | string | 更新时间 |

### 5.13 HealthStatus - 健康状态类型

| 字段 | 类型 | 描述 |
|------|------|------|
| status | 'healthy' \| 'degraded' \| 'unhealthy' | 服务状态 |
| message | string | 状态消息 |
| version | string | 应用版本 |
| timestamp | string | 检查时间 |

### 5.14 NewsItem - 新闻项类型

| 字段 | 类型 | 描述 |
|------|------|------|
| title | string | 标题 |
| url | string | 链接 |
| time | string | 发布时间 |
| source | string | 来源 |

### 5.15 Stock - 股票类型

| 字段 | 类型 | 描述 |
|------|------|------|
| code | string | 股票代码 |
| name | string | 股票名称 |
| price | number | 当前价格 |
| change | number | 涨跌额 |
| change_pct | number | 涨跌幅(%) |
| open | number | 开盘价 |
| high | number | 最高价 |
| low | number | 最低价 |
| volume | string | 成交量 |
| amount | string | 成交额 |
| pre_close | number | 昨收价 |
| timestamp | string | 更新时间 |

---

## 6. API 端点汇总

### 6.1 基金 API (api/routes/funds.py)

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/funds` | GET | 获取基金列表 |
| `/api/funds/{code}` | GET | 获取基金详情 |
| `/api/funds/{code}/estimate` | GET | 获取基金实时估值 |
| `/api/funds/{code}/history` | GET | 获取基金历史净值 |
| `/api/funds/{code}/intraday` | GET | 获取基金日内分时数据 |
| `/api/funds/watchlist` | POST | 添加基金到自选 |
| `/api/funds/watchlist/{code}` | DELETE | 从自选移除基金 |
| `/api/funds/{code}/holding` | PUT | 标记/取消持有基金 |

### 6.2 商品 API (api/routes/commodities.py)

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/commodities` | GET | 获取商品行情列表 |
| `/api/commodities/{type}` | GET | 获取单个商品行情 |
| `/api/commodities/categories` | GET | 获取商品分类 |
| `/api/commodities/history/{commodity_type}` | GET | 获取商品历史行情 |
| `/api/commodities/search` | GET | 搜索商品 |
| `/api/commodities/available` | GET | 获取所有可用商品 |
| `/api/commodities/watchlist` | GET | 获取关注列表 |
| `/api/commodities/watchlist` | POST | 添加关注商品 |
| `/api/commodities/watchlist/{symbol}` | DELETE | 移除关注商品 |
| `/api/commodities/watchlist/{symbol}` | PUT | 更新关注商品 |
| `/api/commodities/gold/cny` | GET | 获取国内黄金行情 |
| `/api/commodities/gold/international` | GET | 获取国际黄金行情 |
| `/api/commodities/oil/wti` | GET | 获取 WTI 原油行情 |
| `/api/commodities/oil/brent` | GET | 获取布伦特原油行情 |
| `/api/commodities/silver` | GET | 获取白银行情 |
| `/api/commodities/crypto` | GET | 获取加密货币行情 |

### 6.3 指数 API (api/routes/indices.py)

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/indices` | GET | 获取全球市场指数 |
| `/api/indices/{index_type}` | GET | 获取单个指数 |
| `/api/indices/regions` | GET | 获取支持的区域 |

### 6.4 交易日历 API (api/routes/trading_calendar.py)

| 端点 | 方法 | 描述 |
|------|------|------|
| `/trading-calendar/calendar/{market}` | GET | 获取指定市场年度交易日历 |
| `/trading-calendar/is-trading-day/{market}` | GET | 判断是否为交易日 |
| `/trading-calendar/next-trading-day/{market}` | GET | 获取下一个交易日 |
| `/trading-calendar/market-status` | GET | 获取多市场状态 |

### 6.5 数据源 API (api/routes/datasource.py)

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/datasource/statistics` | GET | 获取数据源请求统计 |
| `/api/datasource/health` | GET | 获取数据源健康状态 |
| `/api/datasource/sources` | GET | 获取已注册的数据源列表 |

### 6.6 缓存 API (api/routes/cache.py)

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/cache/stats` | GET | 获取缓存统计信息 |

### 6.7 健康检查 API

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/health` | GET | 健康检查（详细） |
| `/api/health/simple` | GET | 健康检查（简单） |

### 6.8 概览 API (api/routes/overview.py)

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/overview` | GET | 市场概览 |
| `/api/overview/simple` | GET | 简版市场概览 |

---

## 7. 数据源标识

| 标识 | 名称 | 用途 |
|------|------|------|
| sina | 新浪财经 | 基金数据 |
| eastmoney | 东方财富 | 基金数据 |
| akshare | AKShare | 商品、指数、板块数据 |
| yfinance | Yahoo Finance | 国际市场数据 |
| sina_news | 新浪财经 | 新闻数据 |
| eastmoney_news | 东方财富 | 新闻数据 |

---

## 8. 市场标识 (交易日历)

| 标识 | 市场名称 |
|------|------|
| china | A股 |
| hk | 港股 |
| usa | 美股 |
| japan | 日股 |
| uk | 英股 |
| germany | 德股 |
| france | 法股 |
| sge | 上海黄金交易所 |
| comex | COMEX 黄金 |
| cme | CME 芝加哥 |
| lbma | LBMA 贵金属 |

---

*本文档最后更新于 2026-02-20*
