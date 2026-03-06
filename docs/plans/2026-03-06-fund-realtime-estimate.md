# 基金实时估值功能用户故事

## 标题
基金实时估值查看功能

---

## 用户故事

**As a** 基金投资者，
**I want to** 在交易时段内实时查看基金的估算净值和涨跌幅，
**So that** 我可以及时了解持仓基金的收益情况，做出更及时的投资决策。

---

## 背景与价值

### 业务背景
基金投资者在交易日需要关注基金的实时估值变化，以便：
- 了解当日持仓基金的预估收益
- 判断是否需要调整投资策略
- 跟踪市场动态和基金表现

### 用户价值
- **及时性**：交易时段内获取最新估值数据
- **可视化**：通过图表直观展示估值走势
- **便捷性**：一站式查看多只基金的估值信息
- **准确性**：区分实时估值（普通基金）和前日净值（QDII基金）

---

## 验收标准 (Acceptance Criteria)

### 核心功能

1. **估值数据展示**
   - [ ] 显示基金的单位净值（昨日收盘净值）
   - [ ] 显示实时估算净值（交易时段内更新）
   - [ ] 显示估算涨跌幅（百分比和绝对值）
   - [ ] 显示估值更新时间

2. **基金卡片组件**
   - [ ] 每只基金以独立卡片形式展示
   - [ ] 卡片包含：基金代码、名称、类型标签
   - [ ] 卡片显示净值、估值、涨跌幅信息
   - [ ] QDII基金特殊处理：显示前日净值而非实时估值

3. **日内走势图**
   - [ ] 支持显示基金日内分时走势图
   - [ ] 图表以昨日净值为基准线
   - [ ] 上涨/下跌使用不同颜色标识
   - [ ] 用户可切换显示/隐藏图表

4. **实时更新机制**
   - [ ] 交易时段内自动刷新估值数据
   - [ ] 非交易时段使用缓存数据减少API调用
   - [ ] 支持WebSocket推送实时更新
   - [ ] 数据更新时有视觉反馈（动画效果）

5. **自选基金管理**
   - [ ] 支持添加基金到自选列表
   - [ ] 支持从自选列表移除基金
   - [ ] 支持标记/取消持有状态
   - [ ] 持有基金优先显示

### API接口

1. **后端端点**
   - `GET /api/funds` - 获取基金列表（含估值信息）
   - `GET /api/funds/{code}` - 获取单个基金详情
   - `GET /api/funds/{code}/estimate` - 获取基金实时估值
   - `GET /api/funds/{code}/intraday` - 获取日内分时数据
   - `POST /api/funds/watchlist` - 添加自选
   - `DELETE /api/funds/watchlist/{code}` - 移除自选
   - `PUT /api/funds/{code}/holding` - 标记持有状态

2. **数据模型**
   ```typescript
   interface Fund {
     code: string;              // 基金代码
     name: string;              // 基金名称
     type: string;              // 基金类型
     netValue: number;          // 单位净值
     netValueDate: string;      // 净值日期
     estimateValue: number;     // 估算净值
     estimateChange: number;    // 估算涨跌额
     estimateChangePercent: number; // 估算涨跌幅%
     estimateTime: string;      // 估值时间
     hasRealTimeEstimate: boolean; // 是否有实时估值
     isHolding: boolean;        // 是否持有
     intraday: FundIntraday[];  // 日内数据
   }
   ```

### 性能要求

1. **响应时间**
   - 基金列表加载 < 2秒
   - 单个基金估值查询 < 500ms
   - 日内数据加载 < 1秒

2. **更新频率**
   - 交易时段：每30秒自动刷新
   - WebSocket连接：实时推送更新
   - 非交易时段：使用缓存，不主动刷新

### 错误处理

1. **网络异常**
   - 网络断开时显示友好提示
   - 自动重试机制（最多3次）
   - 保留上次成功数据

2. **数据源异常**
   - 单个基金数据获取失败不影响其他基金显示
   - 记录错误日志
   - 显示降级数据（如仅显示净值）

---

## 技术实现要点

### 后端

1. **数据源管理**
   - 使用 [`DataSourceManager`](src/datasources/manager.py) 统一管理多个数据源
   - 支持 akshare、fund123 等多个数据源回退
   - 交易时段禁用缓存确保实时性

2. **交易日历集成**
   - 使用 [`TradingCalendarSource`](src/datasources/trading_calendar_source.py) 判断交易时段
   - 区分工作日/节假日
   - 处理不同市场的交易时间

3. **特殊基金处理**
   - QDII基金识别（类型以"QDII"开头）
   - FOF基金海外投资判断（名称含"QDII"/"海外"/"全球"）
   - 延迟净值基金显示前日数据

### 前端

1. **状态管理**
   - 使用 Pinia [`fundStore`](web/src/stores/fundStore.ts) 管理基金数据
   - 支持本地缓存和持久化
   - 响应式更新机制

2. **组件设计**
   - [`FundCard.vue`](web/src/components/FundCard.vue) - 基金卡片组件
   - [`LineChart.vue`](web/src/components/LineChart.vue) - 折线图组件
   - 支持骨架屏加载状态

3. **实时通信**
   - WebSocket连接 [`useWebSocket`](web/src/composables/useWebSocket.ts)
   - 订阅基金实时更新频道
   - 自动重连机制

---

## 边界情况

| 场景 | 预期行为 |
|------|----------|
| 非交易时段访问 | 显示缓存的最后一次估值数据，标注为非实时 |
| QDII基金 | 显示前日净值，不显示实时估值，标注延迟 |
| 新上市基金 | 显示基本信息，估值可能为空 |
| 基金清盘 | 显示最后可用数据，标注基金状态 |
| 网络中断 | 显示离线提示，保留已有数据 |
| 数据源故障 | 尝试备用数据源，显示降级信息 |

---

## 相关文件

### 后端
- [`api/routes/funds.py`](api/routes/funds.py) - 基金API路由
- [`src/datasources/fund_source.py`](src/datasources/fund_source.py) - 基金数据源
- [`src/datasources/trading_calendar_source.py`](src/datasources/trading_calendar_source.py) - 交易日历

### 前端
- [`web/src/stores/fundStore.ts`](web/src/stores/fundStore.ts) - 基金状态管理
- [`web/src/components/FundCard.vue`](web/src/components/FundCard.vue) - 基金卡片
- [`web/src/composables/useWebSocket.ts`](web/src/composables/useWebSocket.ts) - WebSocket

---

## 待办事项

- [ ] 确认估值数据更新频率需求
- [ ] 确定QDI I基金的特殊展示方案
- [ ] 评估是否需要估值预警功能
- [ ] 考虑添加基金对比功能
