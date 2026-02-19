# -*- coding: UTF-8 -*-
"""Trading Calendar Source Tests

测试交易日历数据源
"""

from datetime import date, datetime
from unittest.mock import patch

import pytest

from src.datasources.trading_calendar_source import (
    CHINA_SPECIAL_DATES,
    CalendarResult,
    Market,
    TradingCalendarSource,
    TradingDay,
    update_china_special_dates,
)


class TestMarket:
    """市场枚举测试"""

    def test_market_values(self):
        """测试市场枚举值"""
        assert Market.CHINA.value == "china"
        assert Market.HONG_KONG.value == "hk"
        assert Market.USA.value == "usa"
        assert Market.JAPAN.value == "japan"
        assert Market.UK.value == "uk"
        assert Market.GERMANY.value == "germany"
        assert Market.FRANCE.value == "france"
        assert Market.SGE.value == "sge"
        assert Market.COMEX.value == "comex"
        assert Market.CME.value == "cme"
        assert Market.LBMA.value == "lbma"


class TestTradingCalendarSource:
    """交易日历源测试"""

    @pytest.fixture
    def calendar_source(self):
        """返回交易日历源实例"""
        return TradingCalendarSource(timeout=5.0)

    def test_init(self, calendar_source):
        """测试初始化"""
        assert calendar_source.name == "trading_calendar"
        assert calendar_source.timeout == 5.0
        assert calendar_source.CACHE_TTL == 24 * 60 * 60

    def test_is_weekend(self, calendar_source):
        """测试周末判断"""
        # 周六
        saturday = date(2024, 1, 6)  # 2024年1月6日是周六
        assert calendar_source._is_weekend(saturday) is True

        # 周日
        sunday = date(2024, 1, 7)  # 2024年1月7日是周日
        assert calendar_source._is_weekend(sunday) is True

        # 周一
        monday = date(2024, 1, 8)
        assert calendar_source._is_weekend(monday) is False

    def test_get_holidays(self, calendar_source):
        """测试获取节假日"""
        holidays = calendar_source._get_holidays(Market.CHINA, 2024)
        assert isinstance(holidays, set)

        # 美国节假日
        us_holidays = calendar_source._get_holidays(Market.USA, 2024)
        assert isinstance(us_holidays, set)

    def test_get_special_dates(self, calendar_source):
        """测试获取特殊日期"""
        # 无特殊日期时返回空字典
        special = calendar_source._get_special_dates(Market.USA, 2024)
        assert special == {}

    def test_update_china_special_dates(self):
        """测试更新中国特殊日期"""
        test_dates = {
            date(2024, 2, 10): "春节",
            date(2024, 5, 1): "劳动节",
        }
        update_china_special_dates(test_dates)

        # 验证已更新
        assert date(2024, 2, 10) in CHINA_SPECIAL_DATES

    def test_next_day(self, calendar_source):
        """测试获取下一天"""
        # 常规日期
        d1 = date(2024, 1, 15)
        assert calendar_source._next_day(d1) == date(2024, 1, 16)

        # 月末
        d2 = date(2024, 1, 31)
        assert calendar_source._next_day(d2) == date(2024, 2, 1)

        # 年末
        d3 = date(2024, 12, 31)
        assert calendar_source._next_day(d3) == date(2025, 1, 1)

    def test_get_crypto_calendar(self, calendar_source):
        """测试获取加密货币日历"""
        result = calendar_source._get_crypto_calendar(2024)

        assert result.market == "crypto"
        assert result.year == 2024
        assert len(result.trading_days) > 0
        # 加密货币每天都交易
        assert result.total_trading_days == 366  # 2024是闰年

    def test_is_trading_day_china(self, calendar_source):
        """测试判断中国股市是否交易"""
        # 2024年1月1日是周一，但是元旦
        result = calendar_source.is_trading_day(Market.CHINA, date(2024, 1, 1))
        assert isinstance(result, bool)

        # 2024年1月2日应该交易
        result = calendar_source.is_trading_day(Market.CHINA, date(2024, 1, 2))
        assert isinstance(result, bool)

    def test_is_trading_day_crypto(self, calendar_source):
        """测试加密货币每天都交易"""
        # 加密货币每天都交易
        result = calendar_source.is_trading_day("crypto", date(2024, 1, 6))  # 周六
        assert result is True

        result = calendar_source.is_trading_day("crypto", date(2024, 1, 7))  # 周日
        assert result is True

    def test_get_calendar_crypto(self, calendar_source):
        """测试获取加密货币日历"""
        result = calendar_source.get_calendar("crypto", 2024)

        assert result.market == "crypto"
        assert result.year == 2024
        assert result.total_holidays == 0

    def test_get_calendar_with_cache(self, calendar_source):
        """测试日历缓存"""
        # 第一次获取
        result1 = calendar_source.get_calendar(Market.JAPAN, 2024)

        # 第二次获取应该使用缓存
        result2 = calendar_source.get_calendar(Market.JAPAN, 2024)

        assert result1.year == result2.year
        assert result1.market == result2.market

    def test_get_calendar_by_string(self, calendar_source):
        """测试通过字符串获取日历"""
        result = calendar_source.get_calendar("japan", 2024)
        assert result.market == "japan"

    def test_get_next_trading_day(self, calendar_source):
        """测试获取下一个交易日"""
        # 周五找下周一的交易日
        friday = date(2024, 1, 5)
        next_day = calendar_source.get_next_trading_day(Market.CHINA, friday)
        assert next_day >= friday
        assert calendar_source.is_trading_day(Market.CHINA, next_day)

    def test_get_market_status(self, calendar_source):
        """测试获取市场状态"""
        status = calendar_source.get_market_status([Market.CHINA, Market.USA])

        assert "china" in status
        assert "usa" in status
        assert "is_open" in status["china"]
        assert "is_open" in status["usa"]

    def test_get_market_status_all_markets(self, calendar_source):
        """测试获取所有市场状态"""
        status = calendar_source.get_market_status()

        assert len(status) > 0
        for market_status in status.values():
            assert "is_open" in market_status
            assert "date" in market_status

    def test_is_within_trading_hours(self, calendar_source):
        """测试交易时间判断"""
        # 测试中国股市交易时间
        with patch.object(calendar_source, 'is_trading_day', return_value=True):
            # 交易时间内 (10:00)
            dt = datetime(2024, 1, 15, 10, 0)
            result = calendar_source.is_within_trading_hours(Market.CHINA, dt)
            assert result["status"] == "open"

            # 盘前 (9:00)
            dt = datetime(2024, 1, 15, 9, 0)
            result = calendar_source.is_within_trading_hours(Market.CHINA, dt)
            assert result["status"] == "pre_market"

            # 盘后 (15:30)
            dt = datetime(2024, 1, 15, 15, 30)
            result = calendar_source.is_within_trading_hours(Market.CHINA, dt)
            assert result["status"] == "closed"

            # 午间休市 (12:00)
            dt = datetime(2024, 1, 15, 12, 0)
            result = calendar_source.is_within_trading_hours(Market.CHINA, dt)
            assert result["status"] == "break"

    def test_is_within_trading_hours_non_trading_day(self, calendar_source):
        """测试非交易日"""
        with patch.object(calendar_source, 'is_trading_day', return_value=False):
            dt = datetime(2024, 1, 15, 10, 0)
            result = calendar_source.is_within_trading_hours(Market.CHINA, dt)
            assert result["status"] == "closed"
            assert result["reason"] == "Non-trading day"

    def test_is_within_trading_hours_unknown_market(self, calendar_source):
        """测试未知市场"""
        # 使用一个不在 Market 枚举中的字符串，会抛出 ValueError
        # 测试当传入无效市场时能正确处理
        with pytest.raises(ValueError):
            calendar_source.is_within_trading_hours("unknown_market")

    @pytest.mark.asyncio
    async def test_fetch(self, calendar_source):
        """测试异步获取"""
        result = await calendar_source.fetch(market="japan", year=2024)

        assert result.success is True
        assert result.source == "trading_calendar"
        assert "year" in result.data

    @pytest.mark.asyncio
    async def test_fetch_batch(self, calendar_source):
        """测试批量异步获取"""
        results = await calendar_source.fetch_batch(market="japan", year=2024)

        assert len(results) == 1
        assert results[0].success is True


class TestTradingDay:
    """交易日数据类测试"""

    def test_trading_day_creation(self):
        """测试交易日创建"""
        day = TradingDay(
            date=date(2024, 1, 15),
            is_trading_day=True,
            holiday_name=None,
            is_makeup_day=False,
            market="china"
        )

        assert day.date == date(2024, 1, 15)
        assert day.is_trading_day is True
        assert day.holiday_name is None
        assert day.is_makeup_day is False
        assert day.market == "china"


class TestCalendarResult:
    """日历结果测试"""

    def test_calendar_result_creation(self):
        """测试日历结果创建"""
        trading_days = [
            TradingDay(date(2024, 1, 1), False, "元旦"),
            TradingDay(date(2024, 1, 2), True),
            TradingDay(date(2024, 1, 3), True),
        ]

        result = CalendarResult(
            year=2024,
            market="china",
            trading_days=trading_days,
            total_trading_days=2,
            total_holidays=1
        )

        assert result.year == 2024
        assert result.market == "china"
        assert len(result.trading_days) == 3
        assert result.total_trading_days == 2
        assert result.total_holidays == 1
