# AGENTS.md

**Generated:** 2025-02-05
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
| **Notifications** | `notifications.py` | NotificationManager, AddAlertDialog |
| **Settings** | `settings.py` | SettingsDialog |
| **Error handling** | `error_handling.py` | ErrorHandler, show_error_dialog |
| **Empty states** | `empty_states.py` | empty_funds_state, etc. |
| Dependency check | `check_deps.py` | Environment validation |

## CODE MAP

| Symbol | Type | Location | Role |
|--------|------|----------|------|
| FundGUIApp | class | main.py | Main application, tab management |
| FundDisplayData | dataclass | main.py | Display data with chart_data |
| FundCard | class | components.py | Individual fund card with loading state |
| FundPortfolioCard | class | components.py | Portfolio summary |
| MiniChart | class | components.py | Mini trend chart |
| SearchBar | class | components.py | Fund search component |
| QuickActionButton | class | components.py | Action button with accent |
| AppColors | class | components.py | Color constants |
| FundDetailDialog | class | detail.py | Fund details dialog |
| ChangeColors | class | theme.py | Red/green color scheme |
| **NotificationManager** | class | notifications.py | Price alert management |
| **NotificationDialog** | class | notifications.py | Alert center dialog |
| **AddAlertDialog** | class | notifications.py | Add new price alert |
| **SettingsDialog** | class | settings.py | App settings dialog |
| **ErrorHandler** | class | error_handling.py | Global error handling |
| **empty_funds_state** | func | empty_states.py | Empty fund list UI |

## CONVENTIONS

### Component Design
- Card-based layout (not DataTable rows)
- Stateful components with `update_data()` methods
- Colors from `AppColors` enum (not Flet theme)
- Components in `components.py`, not inline
- **Loading states**: FundCard has `set_loading()` method

### Theme
- Dark theme by default (ft.ThemeMode.DARK)
- Red for up/increase, green for down/decrease (Chinese convention)
- Colors defined in `theme.py`: AppColors, ChangeColors

### Data Flow
- Async data fetch in background (`_load_fund_data()`)
- UI updates via `page.run_task()` for async-to-UI bridge
- Cached components: `_fund_cards: dict[str, FundCard]`
- **Price alerts**: Auto-check after data load via `_check_price_alerts()`

### Tabs
- Three tabs: "自选" (watchlist), "商品" (commodities), "新闻" (news)
- Flet 0.80.5 API: Uses `TabBar` + `Tabs` combination
  - `TabBar(tabs=[Tab(label=...), ...], on_click=handler)`
  - `Tabs(content=Column([...]), length=N)`
- Tab click event: `on_click` with `e.data` containing selected index
- Content visibility: Controls via `_tab_contents.controls[i].visible`
- Tab content built via `_build_*_page()` methods

### Dialogs (v2.0)
- **NotificationDialog**: Show/manage price alerts
- **SettingsDialog**: App configuration (refresh interval, theme, etc.)
- **AddAlertDialog**: Add new price alert for a fund
- All dialogs inherit from `AlertDialog`, use `page.overlay.append()`

### Error Handling (v2.0)
- **ErrorHandler**: Singleton class for error recording and stats
- **show_error_dialog()**: Display error dialog with severity
- Integration: `FundGUIApp` has `error_handler` attribute
- Usage: `self._show_error("message", ErrorSeverity.ERROR)`

### Empty States (v2.0)
- **empty_funds_state()**: Empty watchlist UI
- **empty_commodities_state()**: Empty commodity list UI
- **empty_news_state()**: Empty news list UI
- Support `on_add` and `on_refresh` callbacks

## ANTI-PATTERNS

- **Don't use DataTable**: Uses FundCard components instead
- **No direct page calls in async**: Use `page.run_task()` for async-to-UI updates
- **Don't use Flet theme colors**: Use `AppColors` constants

## NOTES

- **Flet 0.80.5 API**: Uses `TabBar` + `Tabs` combination (see Tabs section above)
- **Async pattern**: Data sources async, but GUI sync (Flet limitation)
- **Component caching**: `_fund_cards` dict prevents full rebuilds
- **Search**: Filters by code/name, toggles `visible` property
- **v2.0 Features**: Notifications, Settings, Error handling, Empty states, Loading states
