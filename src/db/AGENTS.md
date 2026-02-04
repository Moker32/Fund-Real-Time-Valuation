# AGENTS.md

**Generated:** 2026-02-04
**Module:** src/db - Database Persistence

## OVERVIEW

SQLite database for fund/commodity configuration, history data, and news caching.

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| DB Manager | `database.py` | DatabaseManager, ConfigDAO, table schemas |
| Fund config | `database.py` (FundConfig) | Fund with shares, cost, is_hold, sector |
| Commodity config | `database.py` (CommodityConfig) | Commodity with source, enabled flag |
| History records | `database.py` (FundHistoryRecord) | Net value history |
| News cache | `database.py` (NewsRecord) | News with timestamp |

## CODE MAP

| Symbol | Type | Location | Role |
|--------|------|----------|------|
| DatabaseManager | class | database.py | Connection management, table creation, migrations |
| ConfigDAO | class | database.py | CRUD operations for fund/commodity config |
| FundConfig | dataclass | database.py | Fund config (code, name, shares, cost, is_hold, sector) |
| CommodityConfig | dataclass | database.py | Commodity config (symbol, name, source, enabled) |
| FundHistoryRecord | dataclass | database.py | Fund net value history |
| NewsRecord | dataclass | database.py | News cache record |

## CONVENTIONS

### Data Models
- `@dataclass` for all models (FundConfig, CommodityConfig, etc.)
- SQLite integers (0/1) for booleans, convert via `@property`:
  ```python
  watchlist: int = 1  # SQLite integer
  @property
  def is_watchlist(self) -> bool:
      return bool(self.watchlist)
  ```

### Schema
- `fund_config` table: code, name, watchlist, shares, cost, is_hold, sector, notes, created_at, updated_at
- `commodity_config` table: symbol, name, source, enabled, notes, created_at, updated_at
- `fund_history` table: fund_code, date, unit_net_value, estimated_value, growth_rate, fetched_at
- `news_cache` table: title, url, source, category, published_at, fetched_at

### Migrations
- Auto-migration in `DatabaseManager._migrate_database()`
- Checks for missing columns (is_hold, sector) and adds them via ALTER TABLE
- Called during `init_tables()`

### DAO Pattern
- ConfigDAO provides CRUD operations
- `add_fund()`, `update_fund()`, `get_all_funds()`, `get_fund()`
- `add_commodity()`, `get_all_commodities()`, etc.
- Default funds/commodities initialized via `init_default_funds()`, `init_default_commodities()`

## ANTI-PATTERNS

- **Don't use BOOLEAN columns**: SQLite native BOOL has issues, use INTEGER (0/1)
- **Don't skip @property**: Always use for int→bool conversion
- **Don't forget migrations**: Schema changes require `_migrate_database()` update

## NOTES

- **Database location**: Uses default SQLite path (not specified in code)
- **Connection**: Uses `sqlite3.Row` factory for dict-like access
- **Timestamp**: ISO format strings (`datetime.now().isoformat()`)
- **Migration**: Adds is_hold, sector columns if missing (backward compatibility)
