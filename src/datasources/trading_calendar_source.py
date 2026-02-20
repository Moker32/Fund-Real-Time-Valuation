from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from enum import Enum

import httpx
from holidays import CountryHoliday

from src.datasources.base import DataSource, DataSourceResult, DataSourceType

SATURDAY = 5
SUNDAY = 6


class Market(Enum):
    CHINA = "china"
    HONG_KONG = "hk"
    USA = "usa"
    JAPAN = "japan"
    UK = "uk"
    GERMANY = "germany"
    FRANCE = "france"
    # 贵金属/大宗商品
    SGE = "sge"  # 上海黄金交易所
    COMEX = "comex"  # 纽约商品交易所
    CME = "cme"  # 芝加哥商品交易所
    LBMA = "lbma"  # 伦敦金银市场协会


MARKET_COUNTRY_MAP = {
    Market.CHINA: ("CN", ["CN", "HK"]),
    Market.HONG_KONG: ("HK", ["HK"]),
    Market.USA: ("US", ["US"]),
    Market.JAPAN: ("JP", ["JP"]),
    Market.UK: ("GB", ["UK"]),
    Market.GERMANY: ("DE", ["DE"]),
    Market.FRANCE: ("FR", ["FR"]),
}


MARKET_TRADING_HOURS = {
    Market.CHINA: {
        "open": time(9, 30),
        "close": time(15, 0),
        "break_start": time(11, 30),
        "break_end": time(13, 0),
    },
    Market.HONG_KONG: {
        "open": time(9, 30),
        "close": time(16, 0),
        "break_start": time(12, 0),
        "break_end": time(13, 0),
    },
    Market.USA: {
        "open": time(9, 30),
        "close": time(16, 0),
    },
    Market.JAPAN: {
        "open": time(9, 0),
        "close": time(15, 0),
        "break_start": time(11, 30),
        "break_end": time(12, 30),
    },
    Market.UK: {
        "open": time(8, 0),
        "close": time(16, 30),
    },
    Market.GERMANY: {
        "open": time(9, 0),
        "close": time(17, 30),
    },
    Market.FRANCE: {
        "open": time(9, 0),
        "close": time(17, 30),
    },
    # 贵金属交易所 - 日盘 + 夜盘连续交易
    Market.SGE: {  # 上海黄金交易所
        "day_open": time(9, 0),
        "day_close": time(15, 30),
        "night_open": time(19, 50),
        "night_close": time(2, 30),  # 次日
    },
    Market.COMEX: {  # 纽约商品交易所 (黄金、白银)
        "day_open": time(8, 0),
        "day_close": time(13, 30),
        "night_open": time(17, 0),  # 场后交易
        "night_close": time(8, 0),  # 次日
    },
    Market.CME: {  # 芝加哥商品交易所
        "day_open": time(8, 30),
        "day_close": time(13, 30),
        "night_open": time(15, 30),
        "night_close": time(8, 30),  # 次日
    },
    Market.LBMA: {  # 伦敦金银市场协会 - 每日定价两次
        "am_price": time(10, 30),  # 上午定价
        "pm_price": time(15, 0),  # 下午定价
    },
}


CHINA_SPECIAL_DATES: dict[date, str] = {}


class HolidayStrategy(Enum):
    """休市策略类型"""

    STOCK_MARKET = "stock"  # 股票市场: 使用Python holidays库
    CHINA_A_SHARE = "china_a"  # A股: 使用东方财富API获取真实交易日
    CHINA_SGE = "china_sge"  # 上海黄金交易所: 使用中国节假日配置
    US_COMMODITY = "us_commodity"  # 美国商品交易所: 使用美国节假日
    UK_PRECIOUS = "uk_precious"  # 伦敦金银: 使用英国节假日
    WEEKEND_ONLY = "weekend_only"  # 仅周末休市


EXCHANGE_HOLIDAY_STRATEGY: dict[Market, HolidayStrategy] = {
    Market.CHINA: HolidayStrategy.CHINA_A_SHARE,
    Market.HONG_KONG: HolidayStrategy.STOCK_MARKET,
    Market.USA: HolidayStrategy.STOCK_MARKET,
    Market.JAPAN: HolidayStrategy.STOCK_MARKET,
    Market.UK: HolidayStrategy.STOCK_MARKET,
    Market.GERMANY: HolidayStrategy.STOCK_MARKET,
    Market.FRANCE: HolidayStrategy.STOCK_MARKET,
    Market.SGE: HolidayStrategy.CHINA_SGE,
    Market.COMEX: HolidayStrategy.US_COMMODITY,
    Market.CME: HolidayStrategy.US_COMMODITY,
    Market.LBMA: HolidayStrategy.UK_PRECIOUS,
}


def update_china_special_dates(dates: dict[date, str]) -> None:
    global CHINA_SPECIAL_DATES
    CHINA_SPECIAL_DATES.update(dates)


@dataclass
class TradingDay:
    date: date
    is_trading_day: bool
    holiday_name: str | None = None
    is_makeup_day: bool = False
    market: str = ""


@dataclass
class CalendarResult:
    year: int
    market: str
    trading_days: list[TradingDay]
    total_trading_days: int
    total_holidays: int


class TradingCalendarSource(DataSource):
    CACHE_TTL = 24 * 60 * 60
    _china_real_trading_days: dict[int, set[date]] = {}

    def __init__(self, timeout: float = 10.0):
        super().__init__("trading_calendar", DataSourceType.STOCK, timeout)
        self._cache: dict[str, tuple[datetime, CalendarResult]] = {}
        from src.db.database import DatabaseManager

        self._db = DatabaseManager()
        self._dao = self._db.trading_calendar_dao

    def _fetch_china_real_trading_days(self, year: int) -> set[date]:
        """从东方财富获取A股真实交易日"""
        if year in self._china_real_trading_days:
            return self._china_real_trading_days[year]

        trading_days: set[date] = set()

        try:
            url = (
                f"https://push2his.eastmoney.com/api/qt/stock/kline/get"
                f"?secid=1.000001"
                f"&fields1=f1,f2,f3,f4,f5,f6"
                f"&fields2=f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61"
                f"&klt=101&fqt=0&beg={year}0101&end={year}1231"
            )
            resp = httpx.get(url, timeout=self.timeout)
            data = resp.json()

            if data.get("data") and data["data"].get("klines"):
                for line in data["data"]["klines"]:
                    day_str = line.split(",")[0]
                    d = date.fromisoformat(day_str)
                    if d.year == year:
                        trading_days.add(d)

            self._china_real_trading_days[year] = trading_days

        except Exception:
            pass

        return trading_days

    def _get_db_holidays(self, market: Market, year: int) -> tuple[set[date], dict[date, str]]:
        """从数据库获取节假日"""
        holiday_dates: set[date] = set()
        holiday_names: dict[date, str] = {}
        try:
            dao = self._db.holiday_dao
            holidays = dao.get_holidays(market=market.value, year=year, active_only=True)
            for h in holidays:
                try:
                    d = date.fromisoformat(h.holiday_date)
                    holiday_dates.add(d)
                    if h.holiday_name:
                        holiday_names[d] = h.holiday_name
                except Exception:
                    pass
        except Exception:
            pass
        return holiday_dates, holiday_names

    def _get_holidays(self, market: Market, year: int) -> set[date]:
        db_holidays, _ = self._get_db_holidays(market, year)
        if db_holidays:
            return db_holidays

        country_code, _ = MARKET_COUNTRY_MAP.get(market, ("US", ["US"]))

        try:
            holidays = CountryHoliday(country_code, years=year)
            holiday_dates = set(holidays.keys())

            if market == Market.CHINA:
                hk_holidays = CountryHoliday("HK", years=year)
                holiday_dates.update(hk_holidays.keys())

            return holiday_dates
        except Exception:
            return set()

    def _is_weekend(self, day: date) -> bool:
        return day.weekday() in (SATURDAY, SUNDAY)

    def _get_special_dates(self, market: Market, year: int) -> dict[date, str]:
        if market == Market.CHINA:
            return {k: v for k, v in CHINA_SPECIAL_DATES.items() if k.year == year}
        return {}

    def _get_crypto_calendar(self, year: int) -> CalendarResult:
        trading_days = []
        for month in range(1, 13):
            try:
                for day in range(1, 32):
                    d = date(year, month, day)
                    trading_days.append(TradingDay(date=d, is_trading_day=True, holiday_name=None))
            except ValueError:
                continue
        total_days = 366 if (year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)) else 365
        return CalendarResult(
            market="crypto",
            year=year,
            trading_days=trading_days,
            total_trading_days=total_days,
            total_holidays=0,
        )

    def is_within_trading_hours(
        self, market: Market | str, check_datetime: datetime | None = None
    ) -> dict:
        if isinstance(market, str):
            market = Market(market)

        if check_datetime is None:
            check_datetime = datetime.now()

        hours = MARKET_TRADING_HOURS.get(market)
        if not hours:
            return {"status": "unknown", "reason": "Unknown market"}

        current_time = check_datetime.time()
        current_date = check_datetime.date()

        is_trading_day = self.is_trading_day(market, current_date)
        if not is_trading_day:
            return {
                "status": "closed",
                "reason": "Non-trading day",
                "date": current_date.isoformat(),
            }

        if "break_start" in hours:
            if hours["break_start"] <= current_time < hours["break_end"]:
                return {
                    "status": "break",
                    "reason": "Lunch break",
                    "break_start": hours["break_start"].isoformat(),
                    "break_end": hours["break_end"].isoformat(),
                }

        if hours["open"] <= current_time < hours["close"]:
            return {
                "status": "open",
                "trading_start": hours["open"].isoformat(),
                "trading_end": hours["close"].isoformat(),
            }

        if current_time < hours["open"]:
            return {
                "status": "pre_market",
                "market_open": hours["open"].isoformat(),
            }

        return {
            "status": "closed",
            "reason": "After market hours",
            "trading_end": hours["close"].isoformat(),
        }

    def get_calendar(
        self,
        market: Market | str,
        year: int | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> CalendarResult:
        if isinstance(market, str):
            try:
                market = Market(market)
            except ValueError:
                if market.lower() == "crypto":
                    return self._get_crypto_calendar(year or datetime.now().year)
                raise ValueError(f"Unknown market: {market}")

        if year is None:
            year = datetime.now().year

        if start_date is None:
            start_date = date(year, 1, 1)
        if end_date is None:
            end_date = date(year, 12, 31)

        cache_key = f"{market.value}_{year}"
        if cache_key in self._cache:
            cached_time, cached_result = self._cache[cache_key]
            if (datetime.now() - cached_time).total_seconds() < self.CACHE_TTL:
                return cached_result

        db_records = self._dao.get_calendar(market.value, year)
        if db_records:
            trading_days = [
                TradingDay(
                    date=start_date + timedelta(days=i),
                    is_trading_day=r.is_trading_day,
                    holiday_name=r.holiday_name,
                    is_makeup_day=r.is_makeup_day,
                    market=market.value,
                )
                for i, r in enumerate(db_records)
            ]
            result = CalendarResult(
                year=year,
                market=market.value,
                trading_days=trading_days,
                total_trading_days=sum(1 for d in trading_days if d.is_trading_day),
                total_holidays=len(trading_days) - sum(1 for d in trading_days if d.is_trading_day),
            )
            self._cache[cache_key] = (datetime.now(), result)
            return result

        holidays = self._get_holidays(market, year)
        special_dates = self._get_special_dates(market, year)

        strategy = EXCHANGE_HOLIDAY_STRATEGY.get(market, HolidayStrategy.STOCK_MARKET)

        # 尝试获取A股真实交易日数据
        china_real_days: set[date] = set()
        if strategy == HolidayStrategy.CHINA_A_SHARE:
            china_real_days = self._fetch_china_real_trading_days(year)

        trading_days = []
        current = start_date
        while current <= end_date:
            is_trading, holiday_name, is_makeup_day = self._calculate_trading_day(
                current, strategy, year, holidays, china_real_days
            )

            trading_days.append(
                TradingDay(
                    date=current,
                    is_trading_day=is_trading,
                    holiday_name=holiday_name,
                    is_makeup_day=is_makeup_day,
                    market=market.value,
                )
            )

            current = self._next_day(current)

        result = CalendarResult(
            year=year,
            market=market.value,
            trading_days=trading_days,
            total_trading_days=sum(1 for d in trading_days if d.is_trading_day),
            total_holidays=len(trading_days) - sum(1 for d in trading_days if d.is_trading_day),
        )

        from src.db.database import TradingCalendarRecord

        db_records = [
            TradingCalendarRecord(
                market=market.value,
                year=year,
                is_trading_day=d.is_trading_day,
                holiday_name=d.holiday_name,
                is_makeup_day=d.is_makeup_day,
            )
            for d in trading_days
        ]
        self._dao.save_calendar(market.value, year, db_records)

        self._cache[cache_key] = (datetime.now(), result)

        return result

    def _next_day(self, d: date) -> date:
        return (
            d.replace(day=d.day + 1)
            if d.day < 28
            else d.replace(day=1, month=d.month + 1)
            if d.month < 12
            else d.replace(year=d.year + 1, month=1, day=1)
        )

    def _calculate_trading_day(
        self,
        current: date,
        strategy: HolidayStrategy,
        year: int,
        holidays: set[date],
        china_real_days: set[date],
    ) -> tuple[bool, str | None, bool]:
        """根据策略计算指定日期是否为交易日"""
        is_wknd = self._is_weekend(current)

        match strategy:
            case HolidayStrategy.CHINA_SGE:
                sge_holidays, holiday_names = self._get_db_holidays(Market.SGE, year)
                is_holiday = current in sge_holidays
                is_trading = not is_holiday and not is_wknd
                holiday_name = holiday_names.get(current)
                if not holiday_name and current in sge_holidays and current.month == 2:
                    holiday_name = "春节"
                return is_trading, holiday_name, False

            case HolidayStrategy.CHINA_A_SHARE:
                china_holidays, holiday_names = self._get_db_holidays(Market.CHINA, year)
                if china_holidays:
                    holidays = china_holidays
                if current in china_real_days:
                    return True, None, False
                is_holiday = current in holidays
                is_trading = not is_holiday and not is_wknd
                holiday_name = holiday_names.get(current) if holiday_names else None
                if not holiday_name and is_holiday:
                    try:
                        ch = CountryHoliday("CN", years=year)
                        holiday_name = ch.get(current)
                    except Exception:
                        holiday_name = "Holiday"
                return is_trading, holiday_name, False

            case HolidayStrategy.US_COMMODITY:
                is_holiday = current in holidays
                is_trading = not is_holiday and not is_wknd
                holiday_name = None
                if is_holiday:
                    try:
                        ch = CountryHoliday("US", years=year)
                        holiday_name = ch.get(current)
                    except Exception:
                        holiday_name = "Holiday"
                return is_trading, holiday_name, False

            case HolidayStrategy.UK_PRECIOUS:
                is_holiday = current in holidays
                is_trading = not is_holiday and not is_wknd
                holiday_name = None
                if is_holiday:
                    try:
                        ch = CountryHoliday("GB", years=year)
                        holiday_name = ch.get(current)
                    except Exception:
                        holiday_name = "Holiday"
                return is_trading, holiday_name, False

            case HolidayStrategy.STOCK_MARKET:
                is_holiday = current in holidays
                is_trading = not is_holiday and not is_wknd
                holiday_name = None
                return is_trading, holiday_name, False

            case HolidayStrategy.WEEKEND_ONLY:
                return not is_wknd, None, False

            case _:
                return not is_wknd, None, False

    def is_trading_day(self, market: Market | str, check_date: date | None = None) -> bool:
        if check_date is None:
            check_date = date.today()

        result = self.get_calendar(market, year=check_date.year)
        for day in result.trading_days:
            if day.date == check_date:
                return day.is_trading_day

        return False

    def get_next_trading_day(
        self,
        market: Market | str,
        from_date: date | None = None,
    ) -> date:
        if from_date is None:
            from_date = date.today()

        for i in range(10):
            check_date = from_date.replace(day=from_date.day + i)
            if check_date.year != from_date.year:
                result = self.get_calendar(market, year=check_date.year)
            else:
                result = self.get_calendar(market, year=from_date.year)

            for day in result.trading_days:
                if day.date >= from_date and day.is_trading_day:
                    return day.date

        return from_date

    def get_market_status(self, markets: list[Market] | None = None) -> dict[str, dict]:
        if markets is None:
            markets = list(Market)

        today = date.today()
        status = {}

        for market in markets:
            is_open = self.is_trading_day(market, today)

            if not is_open:
                next_open = self.get_next_trading_day(market, today)
            else:
                next_open = today

            status[market.value] = {
                "is_open": is_open,
                "date": today.isoformat(),
                "next_trading_day": next_open.isoformat(),
                "market": market.value,
            }

        return status

    async def fetch(self, *args, **kwargs) -> DataSourceResult:
        try:
            market = kwargs.get("market", "china")
            year = kwargs.get("year")
            start_date = kwargs.get("start_date")
            end_date = kwargs.get("end_date")

            if start_date:
                start_date = datetime.fromisoformat(start_date).date()
            if end_date:
                end_date = datetime.fromisoformat(end_date).date()

            result = self.get_calendar(
                market=market,
                year=year,
                start_date=start_date,
                end_date=end_date,
            )

            return DataSourceResult(
                success=True,
                data={
                    "year": result.year,
                    "market": result.market,
                    "total_trading_days": result.total_trading_days,
                    "total_holidays": result.total_holidays,
                    "days": [
                        {
                            "date": d.date.isoformat(),
                            "is_trading_day": d.is_trading_day,
                            "holiday_name": d.holiday_name,
                        }
                        for d in result.trading_days
                    ],
                },
                source=self.name,
            )
        except Exception as e:
            return self._handle_error(e, self.name)

    async def fetch_batch(self, *args, **kwargs) -> list[DataSourceResult]:
        result = await self.fetch(*args, **kwargs)
        return [result]
