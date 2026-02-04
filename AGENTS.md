# AGENTS.md

**Generated:** 2026-02-04
**Project:** Fund Real-Time Valuation (Flet GUI)
**Language:** Python 3.10+

## OVERVIEW

Python-based fund real-time valuation GUI application using Flet 0.28.3 framework, inspired by Apple Stocks + Alipay design patterns.

## STRUCTURE

```
run_gui.py               # Entry point (dependency check + GUI startup)
src/
├── gui/                # Flet GUI layer (cards, charts, theme)
├── datasources/        # Data source layer (akshare, yfinance)
├── db/                 # SQLite persistence
└── config/             # Configuration models
tests/                  # pytest tests
docs/plans/             # Development plans
```

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Start app | `run_gui.py` | Checks deps, calls `src.gui.main.main()` |
| GUI entry | `src/gui/main.py` | FundGUIApp class, tab pages, event handlers |
| Cards/Components | `src/gui/components.py` | FundCard, FundPortfolioCard, MiniChart, etc. |
| Theme/Colors | `src/gui/theme.py` | AppColors, ChangeColors, formatting |
| Data sources | `src/datasources/` | All DataSource implementations |
| Source manager | `src/datasources/manager.py` | Multi-source failover, load balancing |
| Database | `src/db/database.py` | SQLite schema, FundConfig, CommodityConfig |
| Config models | `src/config/models.py` | Fund, Holding, Commodity dataclasses |
| Test fixtures | `tests/conftest.py` | Path setup for imports |

## CODE MAP

Key classes and their locations:

| Symbol | Type | Location | Role |
|--------|------|----------|------|
| FundGUIApp | class | src/gui/main.py | Main GUI application, tab management |
| FundCard | class | src/gui/components.py | Individual fund card component |
| FundPortfolioCard | class | src/gui/components.py | Portfolio summary card |
| DataSource | abstract class | src/datasources/base.py | Base for all data sources |
| DataSourceManager | class | src/datasources/manager.py | Multi-source orchestration |
| DatabaseManager | class | src/db/database.py | SQLite connection management |
| ConfigDAO | class | src/db/database.py | Data access for fund/commodity config |
| FundConfig | dataclass | src/db/database.py | Fund configuration (with is_hold, sector) |
| Fund | dataclass | src/config/models.py | Fund base model |
| Holding | dataclass | src/config/models.py | Fund with shares/cost |
| DataSourceResult | dataclass | src/datasources/base.py | Standardized result wrapper |

## CONVENTIONS (Deviations)

### Data Models
- `@dataclass` for all models (src/config/models.py, src/db/database.py)
- Enums inherit `str, Enum` for serialization (Theme, DataSource)
- SQLite integers (0/1) for booleans, convert via `@property` methods

### GUI Components
- Card-based layout (not table rows)
- Flet 0.28.3 API (specific imports: Column, Row, Container, etc.)
- Component classes in `src/gui/components.py`
- Color constants in `src/gui/theme.py` (AppColors)

### Data Source Pattern
- Abstract `DataSource` base class with `async fetch()` method
- Manager handles failover, round-robin load balancing
- Result wrapped in `DataSourceResult` dataclass

### Database Schema
- `fund_config` table: code, name, watchlist, shares, cost, is_hold, sector, notes
- `commodity_config` table: symbol, name, source, enabled, notes
- Migration handled in `_migrate_database()` (adds is_hold, sector columns)

### Entry Point
- `run_gui.py`: dependency check → `src.gui.main.main()`
- `src/gui/check_deps.py`: `check_environment()`, `verify_imports()`

## ANTI-PATTERNS (THIS PROJECT)

- **Don't use DataTable**: Project uses card-based layout (FundCard), not table rows
- **SQLite bool storage**: Use INTEGER (0/1), not native BOOLEAN, convert via @property
- **No pyproject.toml**: Only requirements.txt for dependencies
- **No CI/CD**: No .github/workflows, Makefile, or tox.ini
- **Direct GUI imports**: `sys.path.insert(0, ...)` in run_gui.py for module resolution

## COMMANDS

```bash
# Run GUI (default)
python run_gui.py

# Check dependencies only
python run_gui.py --check

# Run tests
pytest tests/ -v
pytest tests/test_gui.py -v
pytest tests/test_datasources.py -v
```

## NOTES

- **Flet 0.28.3**: Specific version required, newer versions may have API changes
- **Async patterns**: Data sources use `async/await`, but GUI uses synchronous Flet API
- **Theme colors**: Defined in `AppColors` (src/gui/theme.py), not from Flet theme
- **Database location**: Not specified in code (uses default SQLite path)
- **Migration**: Auto-migration in `DatabaseManager._migrate_database()` for is_hold/sector columns

## SUBDIRECTORIES

- `src/gui/AGENTS.md` - Flet GUI components and patterns
- `src/datasources/AGENTS.md` - Data source architecture
- `src/db/AGENTS.md` - Database schema and DAO patterns
- `tests/AGENTS.md` - Test conventions and fixtures
