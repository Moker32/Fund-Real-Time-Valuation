from datetime import date

from fastapi import APIRouter, Query
from pydantic import BaseModel

from src.datasources.trading_calendar_source import Market, TradingCalendarSource

router = APIRouter(prefix="/trading-calendar", tags=["Trading Calendar"])


class TradingDayResponse(BaseModel):
    date: str
    is_trading_day: bool
    holiday_name: str | None = None


class CalendarResponse(BaseModel):
    year: int
    market: str
    total_trading_days: int
    total_holidays: int
    days: list[TradingDayResponse]


class MarketStatusResponse(BaseModel):
    is_open: bool
    date: str
    next_trading_day: str
    market: str
    is_within_session: bool


_calendar_source: TradingCalendarSource | None = None


def get_calendar_source() -> TradingCalendarSource:
    global _calendar_source
    if _calendar_source is None:
        _calendar_source = TradingCalendarSource()
    return _calendar_source


@router.get(
    "/calendar/{market}",
    response_model=CalendarResponse,
    summary="获取市场日历",
    description="获取指定市场在指定年份的交易日期历，包括交易日和节假日",
)
async def get_calendar(
    market: str,
    year: int | None = Query(None, description="Year (default: current year)"),
    start_date: str | None = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: str | None = Query(None, description="End date (YYYY-MM-DD)"),
) -> CalendarResponse:
    source = get_calendar_source()

    start = date.fromisoformat(start_date) if start_date else None
    end = date.fromisoformat(end_date) if end_date else None

    result = source.get_calendar(
        market=market,
        year=year,
        start_date=start,
        end_date=end,
    )

    return CalendarResponse(
        year=result.year,
        market=result.market,
        total_trading_days=result.total_trading_days,
        total_holidays=result.total_holidays,
        days=[
            TradingDayResponse(
                date=d.date.isoformat(),
                is_trading_day=d.is_trading_day,
                holiday_name=d.holiday_name,
            )
            for d in result.trading_days
        ],
    )


@router.get(
    "/is-trading-day/{market}",
    summary="判断是否为交易日",
    description="判断指定市场在指定日期是否为交易日",
)
async def is_trading_day(
    market: str,
    check_date: str | None = Query(None, description="Date to check (YYYY-MM-DD, default: today)"),
) -> dict:
    source = get_calendar_source()

    d = date.fromisoformat(check_date) if check_date else date.today()
    is_open = source.is_trading_day(market, d)

    return {
        "market": market,
        "date": d.isoformat(),
        "is_trading_day": is_open,
    }


@router.get(
    "/next-trading-day/{market}",
    summary="获取下一个交易日",
    description="获取指定日期之后的下一个交易日",
)
async def get_next_trading_day(
    market: str,
    from_date: str | None = Query(None, description="Start from date (YYYY-MM-DD, default: today)"),
) -> dict:
    source = get_calendar_source()

    d = date.fromisoformat(from_date) if from_date else date.today()
    next_day = source.get_next_trading_day(market, d)

    return {
        "market": market,
        "from_date": d.isoformat(),
        "next_trading_day": next_day.isoformat(),
    }


@router.get(
    "/market-status",
    response_model=dict[str, MarketStatusResponse],
    summary="获取多市场状态",
    description="批量获取多个市场的当前交易状态",
)
async def get_market_status(
    markets: str | None = Query(None, description="Comma-separated markets (default: all)"),
) -> dict[str, MarketStatusResponse]:
    source = get_calendar_source()

    market_list = None
    if markets:
        market_list = [Market(m.strip()) for m in markets.split(",")]

    status = source.get_market_status(market_list)

    return {k: MarketStatusResponse(**v) for k, v in status.items()}


@router.get(
    "/markets",
    summary="获取支持的市场列表",
    description="获取所有支持的交易市场及其描述",
)
async def list_markets() -> dict:
    return {
        "markets": [m.value for m in Market],
        "descriptions": {
            "china": "A股 (上海/深圳)",
            "hk": "港股",
            "usa": "美股",
            "japan": "日股",
            "uk": "英股",
            "germany": "德股",
            "france": "法股",
        },
    }
