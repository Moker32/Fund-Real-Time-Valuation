# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Fund Real-Time Valuation - A fund and financial market monitoring platform with real-time data push, multi-source aggregation, and caching optimization.

**Tech Stack**: Python 3.10+, FastAPI, Vue 3 + TypeScript, SQLite, akshare, yfinance

**Deployment**: Single-port deployment (FastAPI serves both frontend and backend)

## Common Commands

```bash
# Install dependencies
pnpm run install:all

# Start development server (single port 8000, serves both frontend and backend)
pnpm run dev

# Quick start (skip cache warmup)
uv run python run_app.py --fast --reload

# Frontend-only development (Vite, port 3000 with hot reload)
pnpm run dev:web

# Backend-only development (FastAPI, port 8000)
pnpm run dev:api

# Run tests
uv run pytest tests/ -v                              # All tests
uv run pytest tests/test_file.py::test_function -v  # Single test

# Lint and type check
uv run ruff check .           # Python lint
uv run ruff check --fix .     # Auto-fix
uv run mypy .                 # Python type check
cd web && pnpm run lint      # Frontend ESLint

# E2E tests
cd web && pnpm run test:e2e

# Build frontend
pnpm run build:web
```

## Architecture

```
api/           # FastAPI layer - HTTP/WebSocket entry points
src/datasources/  # Data source layer - all external data fetching
src/db/        # Database layer - SQLite DAOs
web/           # Frontend - Vue 3 SPA
tests/         # pytest test files
```

**Data Flow**: `WebSocket/HTTP → API Routes → DataSourceManager → DataSource → External API (akshare/yfinance)`

### Data Source Pattern

All data sources implement the `DataSource` interface with `fetch()` returning `DataSourceResult`:

```python
class MyDataSource(DataSource):
    async def fetch(self, *args) -> DataSourceResult:
        try:
            data = await self._fetch(...)
            return DataSourceResult(success=True, data=data, source=self.name)
        except Exception as e:
            logger.warning(f"Fetch failed: {e}")
            return DataSourceResult(success=False, error=str(e))
```

### Key Entry Points

- `run_app.py` - Application entry point; starts FastAPI server and serves frontend
- `api/main.py` - FastAPI application instance
- `src/datasources/manager.py` - DataSourceManager orchestrates all data sources

## Configuration

Configuration files located in `~/.fund-tui/`:

- `config.yaml` - Application settings
- `funds.yaml` - Watchlist funds
- `fund_data.db` - SQLite database (queryable directly with sqlite3)

## API Endpoints

**Core**: `/api/funds`, `/api/commodities`, `/api/indices`, `/api/sectors`  
**Management**: `/api/cache/stats`, `/api/datasource/*`, `/api/health/*`  
**Real-time**: `WS /ws/realtime`

Full endpoint documentation available at `/docs` (Swagger UI) when running.

## Testing

- Test files: `tests/test_*.py`
- Use fixtures from `conftest.py`
- Async tests: `@pytest.mark.asyncio`
- Naming convention: `test_<method_name>`

## Frontend Development

For frontend-only development with hot reload:

```bash
# Terminal 1: Start backend
pnpm run dev:api

# Terminal 2: Start frontend
pnpm run dev:web
```

Frontend runs on http://localhost:3000, API requests proxied to backend.

## Code Style

### Python
- Import order: stdlib → third-party → local (absolute imports)
- Line length: 100 characters
- Type hints: Python 3.10+ style (`str | None` not `Optional[str]`)
- No bare `except:`, return `DataSourceResult(success=False, error=...)` on failure

### TypeScript/Vue
- Absolute imports: `@/components/...`
- Composition API + `<script setup>`
- TypeScript strict mode
- No `as any`, `@ts-ignore`, or `@ts-expect-error`

## Notes

- mypy ignores type stubs for: akshare, yfinance, matplotlib, pandas, numpy
- src/datasources module has relaxed mypy rules due to dynamic data structures

## Commit Workflow

1. Run `git diff --stat` to show changes
2. Wait for user to review and approve
3. Run tests: `uv run pytest tests/` (Python) or `cd web && pnpm run lint` (frontend)
4. Commit with Chinese message: `git commit -m "fix: 修复XXX问题"`
5. Push if user approves

## Bug Fix Workflow

When debugging:
1. Check edge cases first (>0 vs >=0, boundary values like yScaleMax)
2. Verify API responses (look for None/null cases)
3. For chart issues: verify data pipeline before fixing display logic
4. Test with fresh state (clear localStorage) to verify fallback chains
