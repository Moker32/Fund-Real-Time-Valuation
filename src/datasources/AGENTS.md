# AGENTS.md

**Generated:** 2026-02-04
**Module:** src/datasources - Data Source Layer

## OVERVIEW

Async data sources for fund, stock, commodity, bond, index, sector, and sentiment data. Multi-source failover with load balancing.

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Base class | `base.py` | DataSource abstract, DataSourceResult, DataSourceType |
| Manager | `manager.py` | Multi-source orchestration |
| Aggregator | `aggregator.py` | Same-source, load-balanced aggregation |
| Gateway | `gateway.py` | Unified data gateway with failover |
| Health check | `health.py` | Data source health monitoring |
| Hot backup | `hot_backup.py` | Hot backup data source switching |
| Unified models | `unified_models.py` | Shared data models |
| Fund data | `fund_source.py` | Fund valuations from akshare/yfinance |
| Fund cache strategy | `fund/cache_strategy.py` | Database-first caching with TTL layers |
| Stock data | `stock_source.py` | Stock prices from akshare |
| Commodity | `commodity_source.py` | Commodity prices (gold, oil, etc.) |
| Index | `index_source.py` | Global market indices |
| Bonds | `bond_source.py` | Bond yields from Sina/AKShare |
| Sectors | `sector_source.py` | Sector performance data |
| Sentiment | `akshare_sentiment_source.py` | Market sentiment data |
| Trading calendar | `trading_calendar_source.py` | Trading calendar for multiple markets |
| Cache | `cache.py` | In-memory caching layer |
| Dual cache | `dual_cache.py` | Two-tier cache (memory + database) |
| Cache warmer | `cache_warmer.py` | Preload cache on startup |
| Cache cleaner | `cache_cleaner.py` | Periodic cache cleanup |

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
| CacheLockManager | class | fund/cache_strategy.py | Cache lock manager to prevent cache stampede |
| FundCacheStrategy | class | fund/cache_strategy.py | Database-first caching strategy with TTL layers |
| CacheResult | dataclass | fund/cache_strategy.py | Cache fetch result with stale flag |
| CacheLockTimeoutError | Exception | fund/cache_strategy.py | Lock timeout exception |

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

### Cache Strategy Pattern
- Database-first approach: check DB before API
- TTL layers: Static (30d), Mid (7d), High (1d)
- Lock mechanism: `CacheLockManager.acquire(key, timeout=30.0)`
- Degradation: Return stale data if available when refresh fails
- Usage:
  ```python
  strategy = FundCacheStrategy(db_manager)
  result = await strategy.get_with_cache(
      fund_code="000001",
      fetch_func=lambda: api.fetch_fund("000001"),
      fields=["name", "net_value"]  # Auto-calculates TTL
  )
  if result.data:
      # Use result.data (may be stale, check result.is_stale)
  ```

## ANTI-PATTERNS

- **Don't use sync fetch**: All data sources must be async
- **Don't skip error handling**: Always wrap in try/except, return DataSourceResult
- **Don't return raw data**: Wrap in DataSourceResult

## NOTES

- **HTTP client**: httpx (async) for all network requests
- **Timeout**: Default 10s, configurable via DataSource.__init__
- **Rate limiting**: Manager uses `asyncio.Semaphore(max_concurrent)`
- **Data sources**: akshare (primary), yfinance (fallback), Sina (stocks/bonds)
