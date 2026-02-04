# AGENTS.md

**Generated:** 2026-02-04
**Module:** src/datasources - Data Source Layer

## OVERVIEW

Async data sources for fund, stock, commodity, crypto, bond, news, and sector data. Multi-source failover with load balancing.

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Base class | `base.py` | DataSource abstract, DataSourceResult, DataSourceType |
| Manager | `manager.py` | Multi-source orchestration |
| Aggregator | `aggregator.py` | Same-source, load-balanced aggregation |
| Fund data | `fund_source.py` | Fund valuations from akshare/yfinance |
| Stock data | `stock_source.py` | Stock prices from akshare |
| Commodity | `commodity_source.py` | Commodity prices (gold, oil, etc.) |
| Crypto | `crypto_source.py` | Crypto prices (BTC, ETH, etc.) |
| Bonds | `bond_source.py` | Bond yields from Sina/AKShare |
| News | `news_source.py` | Financial news aggregation |
| Sectors | `sector_source.py` | Sector performance data |
| Portfolio | `portfolio.py` | Portfolio analysis and metrics |

## CODE MAP

| Symbol | Type | Location | Role |
|--------|------|----------|------|
| DataSource | abstract class | base.py | Base for all data sources |
| DataSourceType | Enum | base.py | FUND, COMMODITY, NEWS, SECTOR, STOCK, BOND, CRYPTO |
| DataSourceResult | dataclass | base.py | success, data, error, timestamp, source |
| DataSourceError | Exception | base.py | Base exception class |
| DataSourceManager | class | manager.py | Multi-source registration, failover, load balancing |
| DataAggregator | abstract class | aggregator.py | Base for aggregators |
| SameSourceAggregator | class | aggregator.py | Single-source aggregation |
| LoadBalancedAggregator | class | aggregator.py | Multi-source load balancing |

## CONVENTIONS

### Data Source Pattern
- Inherit `DataSource` (abstract base class)
- Implement `async fetch(*args, **kwargs) -> DataSourceResult`
- Return `DataSourceResult` (success/data/error/timestamp)
- Use `DataSourceType` enum for source type

### Result Wrapping
```python
@dataclass
class DataSourceResult:
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    timestamp: float = 0.0
    source: str = ""
```

### Manager Pattern
- Register sources with `manager.register(source, config)`
- Failover: tries sources in priority order until success
- Load balancing: round-robin across sources if enabled
- Health tracking: error rate, request count, last error

### Error Handling
- Custom exceptions: NetworkError, DataParseError, TimeoutError, DataSourceUnavailableError
- All inherit from `DataSourceError`
- Wrap exceptions in `DataSourceResult(success=False, error=...)`

### Async Patterns
- All `fetch()` methods are async
- Use `asyncio.Semaphore` for concurrency control
- Use `asyncio.gather()` for batch requests

## ANTI-PATTERNS

- **Don't use sync fetch**: All data sources must be async
- **Don't skip error handling**: Always wrap in try/except, return DataSourceResult
- **Don't return raw data**: Wrap in DataSourceResult

## NOTES

- **HTTP client**: httpx (async) for all network requests
- **Timeout**: Default 10s, configurable via DataSource.__init__
- **Rate limiting**: Manager uses `asyncio.Semaphore(max_concurrent)`
- **Data sources**: akshare (primary), yfinance (fallback), Sina (stocks/bonds)
