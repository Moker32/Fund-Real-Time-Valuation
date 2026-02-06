# 基金实时估值 TUI 应用 - 数据源扩展计划

**创建日期**: 2026-02-03
**目标**: 扩展股票、债券、加密货币数据源

---

## 1. 新增数据源概览

### 1.1 股票行情数据源 (Stock)

| 数据源 | 来源 | 功能 | 优先级 |
|--------|------|------|--------|
| `SinaStockDataSource` | 新浪财经 | A股实时行情 | P0 |
| `AKShareStockSource` | AKShare | A股/港股/B股 | P0 |
| `YahooStockSource` | Yahoo Finance | 港股/美股 | P1 |
| `EastMoneyStockSource` | 东方财富 | A股补充 | P2 |

### 1.2 债券数据源 (Bond)

| 数据源 | 来源 | 功能 | 优先级 |
|--------|------|------|--------|
| `SinaBondDataSource` | 新浪财经 | 国债/企业债 | P0 |
| `AKShareBondSource` | AKShare | 可转债/地方债 | P1 |
| `EastMoneyBondSource` | 东方财富 | 债券详情 | P2 |

### 1.3 加密货币数据源 (Crypto)

| 数据源 | 来源 | 功能 | 优先级 |
|--------|------|------|--------|
| `BinanceCryptoSource` | Binance API | BTC/ETH 实时 | P0 |
| `CoinGeckoCryptoSource` | CoinGecko API | 全市场数据 | P1 |

---

## 2. 详细实现计划

### Task 1: 扩展 DataSourceType 枚举

**File**: `src/datasources/base.py`

```python
class DataSourceType(Enum):
    FUND = "fund"
    COMMODITY = "commodity"
    NEWS = "news"
    SECTOR = "sector"
    STOCK = "stock"        # 新增
    BOND = "bond"          # 新增
    CRYPTO = "crypto"      # 新增
```

---

### Task 2: 实现股票数据源

**File**: `src/datasources/stock_source.py`

#### 2.1 SinaStockDataSource (A 股)

```python
class SinaStockDataSource(DataSource):
    """新浪财经 A 股数据源"""

    async def fetch(self, stock_code: str) -> DataSourceResult:
        """获取 A 股实时行情

        Args:
            stock_code: 股票代码 (如: 000001, 600000)
        """
        # API: https://hq.sinajs.cn/list=sh600000
        # 返回: 股票名,今开,昨收,现价,最高,最低...
```

#### 2.2 YahooStockSource (港股/美股)

```python
class YahooStockSource(DataSource):
    """Yahoo Finance 数据源"""

    async def fetch(self, symbol: str) -> DataSourceResult:
        """获取股票行情

        Args:
            symbol: 股票代码
                - A股: 000001.SZ, 600000.SH
                - 港股: 0700.HK
                - 美股: AAPL, MSFT
        """
        # 使用 yfinance 库
        import yfinance as yf
        ticker = yf.Ticker(symbol)
```

---

### Task 3: 实现债券数据源

**File**: `src/datasources/bond_source.py`

#### 3.1 SinaBondDataSource

```python
class SinaBondDataSource(DataSource):
    """新浪财经债券数据源"""

    async def fetch(self, bond_code: str) -> DataSourceResult:
        """获取债券行情

        Args:
            bond_code: 债券代码 (如: 113052, 110053)
        """
        # API: https://hq.sinajs.cn/list=sh113052
```

#### 3.2 AKShareBondSource

```python
class AKShareBondSource(DataSource):
    """AKShare 可转债数据源"""

    async def fetch(self, bond_type: str = "cbond") -> DataSourceResult:
        """获取可转债数据

        Args:
            bond_type: "cbond" 可转债, "bond" 地方债
        """
        import akshare as ak
        # ak.bond_zh_hs_cov_daily() - 可转债
        # ak.bond_zh_hs_cov_spot() - 可转债实时
```

---

### Task 4: 实现加密货币数据源

**File**: `src/datasources/crypto_source.py`

#### 4.1 BinanceCryptoSource

```python
class BinanceCryptoSource(DataSource):
    """Binance API 加密货币数据源"""

    async def fetch(self, symbol: str = "BTCUSDT") -> DataSourceResult:
        """获取加密货币行情

        Args:
            symbol: 交易对 (BTCUSDT, ETHUSDT)
        """
        # API: https://api.binance.com/api/v3/ticker/24hr
```

#### 4.2 CoinGeckoCryptoSource

```python
class CoinGeckoCryptoSource(DataSource):
    """CoinGecko API 数据源"""

    async def fetch(self, coin_id: str = "bitcoin") -> DataSourceResult:
        """获取加密货币数据

        Args:
            coin_id: 币种 ID (bitcoin, ethereum)
        """
        # API: https://api.coingecko.com/api/v3/simple/price
```

---

### Task 5: 更新 DataSourceManager

**File**: `src/datasources/manager.py`

```python
def create_default_manager() -> DataSourceManager:
    manager = DataSourceManager()

    # ... 现有注册 ...

    # 新增股票数据源
    from .stock_source import SinaStockDataSource, YahooStockSource
    manager.register(SinaStockDataSource())
    manager.register(YahooStockSource())

    # 新增债券数据源
    from .bond_source import SinaBondDataSource, AKShareBondSource
    manager.register(SinaBondDataSource())
    manager.register(AKShareBondSource())

    # 新增加密货币数据源
    from .crypto_source import BinanceCryptoSource
    manager.register(BinanceCryptoSource())

    return manager
```

---

## 3. 依赖更新

**File**: `requirements.txt`

```txt
# 现有依赖...
textual>=0.50.0
httpx>=0.24.0
akshare>=1.10.0
yfinance>=0.2.0
pyyaml>=6.0
python-dateutil>=2.8.2
beautifulsoup4>=4.12.0
matplotlib>=3.7.0

# 新增依赖 (如需要)
# ccxt>=2.0.0  # Binance API 替代方案
```

---

## 4. 验证步骤

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 测试导入
python -c "
from datasources.stock_source import SinaStockDataSource, YahooStockSource
from datasources.bond_source import SinaBondDataSource
from datasources.crypto_source import BinanceCryptoSource
print('Import OK')
"

# 3. 运行测试
pytest tests/test_datasources.py -v
```

---

## 5. 时间估算

| Task | 复杂度 | 预估时间 |
|------|--------|----------|
| Task 1: DataSourceType 枚举 | 低 | 10min |
| Task 2: 股票数据源 | 中 | 2h |
| Task 3: 债券数据源 | 中 | 2h |
| Task 4: 加密货币数据源 | 低 | 1h |
| Task 5: 更新 Manager | 低 | 30min |

**总计**: ~6h
