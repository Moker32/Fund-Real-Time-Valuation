# AGENTS.md

**Generated:** 2026-02-04
**Module:** src/gui - Flet GUI Layer

## OVERVIEW

Flet-based GUI components for fund valuation app. Apple Stocks + Alipay design patterns.

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Main app | `main.py` | FundGUIApp, tab pages, data loading |
| Components | `components.py` | Reusable UI components |
| Theme/Colors | `theme.py` | AppColors, ChangeColors, formatting |
| Fund details | `detail.py` | FundDetailDialog component |
| Charts | `chart.py` | K-line, chart rendering |
| Dependency check | `check_deps.py` | Environment validation |

## CODE MAP

| Symbol | Type | Location | Role |
|--------|------|----------|------|
| FundGUIApp | class | main.py | Main application, tab management |
| FundDisplayData | dataclass | main.py | Display data with chart_data |
| FundCard | class | components.py | Individual fund card |
| FundPortfolioCard | class | components.py | Portfolio summary |
| MiniChart | class | components.py | Mini trend chart |
| SearchBar | class | components.py | Fund search component |
| QuickActionButton | class | components.py | Action button with accent |
| AppColors | class | components.py | Color constants |
| FundDetailDialog | class | detail.py | Fund details dialog |
| ChangeColors | class | theme.py | Red/green color scheme |

## CONVENTIONS

### Component Design
- Card-based layout (not DataTable rows)
- Stateful components with `update_data()` methods
- Colors from `AppColors` enum (not Flet theme)
- Components in `components.py`, not inline

### Theme
- Dark theme by default (ft.ThemeMode.DARK)
- Red for up/increase, green for down/decrease (Chinese convention)
- Colors defined in `theme.py`: AppColors, ChangeColors

### Data Flow
- Async data fetch in background (`_load_fund_data()`)
- UI updates via `page.run_task()` for async-to-UI bridge
- Cached components: `_fund_cards: dict[str, FundCard]`

### Tabs
- Three tabs: "自选" (watchlist), "商品" (commodities), "新闻" (news)
- Flet Tabs with animation_duration=350
- Tab content built via `_build_*_page()` methods

## ANTI-PATTERNS

- **Don't use DataTable**: Uses FundCard components instead
- **No direct page calls in async**: Use `page.run_task()` for async-to-UI updates
- **Don't use Flet theme colors**: Use `AppColors` constants

## NOTES

- **Flet 0.28.3 API**: Specific imports (Column, Row, Container, not generic widgets)
- **Async pattern**: Data sources async, but GUI sync (Flet limitation)
- **Component caching**: `_fund_cards` dict prevents full rebuilds
- **Search**: Filters by code/name, toggles `visible` property
