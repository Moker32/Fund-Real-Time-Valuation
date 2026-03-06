# -*- coding: UTF-8 -*-
"""
实时数据推送器测试

测试 RealtimePusher 类的核心功能：
- 初始化和依赖注入
- start() 和 stop() 方法
- _push_funds_loop(), _push_commodities_loop(), _push_indices_loop() 循环
- _diff_data() 差量计算
- _get_fund_codes() 获取基金代码
- _is_trading_hours() 交易时段检测
- 错误处理和重试逻辑
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.datasources.manager import DataSourceManager, DataSourceResult, DataSourceType
from src.utils.realtime_pusher import (
    NON_TRADING_COMMODITY_INTERVAL,
    NON_TRADING_FUND_INTERVAL,
    NON_TRADING_INDEX_INTERVAL,
    TRADING_COMMODITY_INTERVAL,
    TRADING_FUND_INTERVAL,
    TRADING_INDEX_INTERVAL,
    RealtimePusher,
    get_realtime_pusher,
    start_realtime_pusher,
    stop_realtime_pusher,
)
from src.utils.websocket_manager import (
    WebSocketManager,
    _convert_dict_to_camel_case,
    _to_camel_case,
    set_websocket_manager,
)


class TestToCamelCase:
    """snake_case 转 camelCase 测试"""

    def test_simple_snake_case(self):
        """测试简单 snake_case 转换"""
        assert _to_camel_case("fund_code") == "fundCode"
        assert _to_camel_case("net_value") == "netValue"
        assert _to_camel_case("change_percent") == "changePercent"

    def test_multiple_underscores(self):
        """测试多个下划线的情况"""
        assert _to_camel_case("net_value_date") == "netValueDate"
        assert _to_camel_case("a_b_c_d") == "aBCD"
        assert _to_camel_case("one_two_three_four") == "oneTwoThreeFour"

    def test_already_camel_case(self):
        """测试已经是 camelCase 的情况"""
        assert _to_camel_case("fundCode") == "fundCode"
        assert _to_camel_case("netValue") == "netValue"
        assert _to_camel_case("a") == "a"

    def test_empty_string(self):
        """测试空字符串"""
        assert _to_camel_case("") == ""

    def test_no_underscores(self):
        """测试没有下划线的字符串"""
        assert _to_camel_case("code") == "code"
        assert _to_camel_case("name") == "name"
        assert _to_camel_case("value") == "value"

    def test_single_underscore(self):
        """测试单个下划线"""
        assert _to_camel_case("a_b") == "aB"

    def test_trailing_underscore(self):
        """测试尾部下划线"""
        # 尾部下划线会产生空字符串组件，但 join 会忽略
        assert _to_camel_case("code_") == "code"

    def test_leading_underscore(self):
        """测试头部下划线"""
        # 头部下划线：第一个组件是空字符串
        assert _to_camel_case("_code") == "Code"

    def test_consecutive_underscores(self):
        """测试连续下划线"""
        # 连续下划线会产生空字符串组件
        assert _to_camel_case("a__b") == "aB"


class TestConvertDictToCamelCase:
    """字典键转换为 camelCase 测试"""

    def test_simple_dict(self):
        """测试简单字典转换"""
        data = {"fund_code": "000001", "net_value": 1.234}
        result = _convert_dict_to_camel_case(data)
        assert result == {"fundCode": "000001", "netValue": 1.234}

    def test_nested_dict(self):
        """测试嵌套字典转换"""
        data = {
            "fund_code": "000001",
            "detail_info": {"manager_name": "张三", "company_name": "测试公司"}
        }
        result = _convert_dict_to_camel_case(data)
        assert result == {
            "fundCode": "000001",
            "detailInfo": {"managerName": "张三", "companyName": "测试公司"}
        }

    def test_dict_with_list(self):
        """测试包含列表的字典转换"""
        data = {
            "fund_list": [
                {"fund_code": "000001", "fund_name": "基金A"},
                {"fund_code": "000002", "fund_name": "基金B"}
            ]
        }
        result = _convert_dict_to_camel_case(data)
        assert result == {
            "fundList": [
                {"fundCode": "000001", "fundName": "基金A"},
                {"fundCode": "000002", "fundName": "基金B"}
            ]
        }

    def test_dict_with_primitive_list(self):
        """测试包含基本类型列表的字典"""
        data = {"tag_list": ["tag1", "tag2", "tag3"]}
        result = _convert_dict_to_camel_case(data)
        assert result == {"tagList": ["tag1", "tag2", "tag3"]}

    def test_mixed_data_types(self):
        """测试混合数据类型"""
        data = {
            "string_value": "test",
            "int_value": 123,
            "float_value": 45.67,
            "bool_value": True,
            "none_value": None,
            "list_value": [1, 2, 3],
            "dict_value": {"inner_key": "inner_value"}
        }
        result = _convert_dict_to_camel_case(data)
        assert result == {
            "stringValue": "test",
            "intValue": 123,
            "floatValue": 45.67,
            "boolValue": True,
            "noneValue": None,
            "listValue": [1, 2, 3],
            "dictValue": {"innerKey": "inner_value"}
        }

    def test_empty_dict(self):
        """测试空字典"""
        result = _convert_dict_to_camel_case({})
        assert result == {}

    def test_deeply_nested_dict(self):
        """测试深度嵌套字典"""
        data = {
            "level_one": {
                "level_two": {
                    "level_three": {
                        "deep_value": "found"
                    }
                }
            }
        }
        result = _convert_dict_to_camel_case(data)
        assert result == {
            "levelOne": {
                "levelTwo": {
                    "levelThree": {
                        "deepValue": "found"
                    }
                }
            }
        }

    def test_list_of_lists(self):
        """测试嵌套列表"""
        data = {
            "matrix": [[1, 2], [3, 4]]
        }
        result = _convert_dict_to_camel_case(data)
        assert result == {"matrix": [[1, 2], [3, 4]]}

    def test_complex_nested_structure(self):
        """测试复杂嵌套结构"""
        data = {
            "fund_code": "000001",
            "holdings": [
                {
                    "stock_code": "600000",
                    "stock_name": "浦发银行",
                    "position_ratio": 5.23
                },
                {
                    "stock_code": "000001",
                    "stock_name": "平安银行",
                    "position_ratio": 3.45
                }
            ],
            "performance": {
                "one_month": 2.3,
                "three_month": 5.6,
                "one_year": 12.5
            }
        }
        result = _convert_dict_to_camel_case(data)
        assert result == {
            "fundCode": "000001",
            "holdings": [
                {
                    "stockCode": "600000",
                    "stockName": "浦发银行",
                    "positionRatio": 5.23
                },
                {
                    "stockCode": "000001",
                    "stockName": "平安银行",
                    "positionRatio": 3.45
                }
            ],
            "performance": {
                "oneMonth": 2.3,
                "threeMonth": 5.6,
                "oneYear": 12.5
            }
        }


class TestIntervalConstants:
    """推送间隔常量测试"""

    def test_trading_intervals(self):
        """测试交易时段间隔"""
        assert TRADING_FUND_INTERVAL == 30
        assert TRADING_COMMODITY_INTERVAL == 10
        assert TRADING_INDEX_INTERVAL == 10

    def test_non_trading_intervals(self):
        """测试非交易时段间隔"""
        assert NON_TRADING_FUND_INTERVAL == 60
        assert NON_TRADING_COMMODITY_INTERVAL == 30
        assert NON_TRADING_INDEX_INTERVAL == 30

    def test_non_trading_intervals_greater(self):
        """测试非交易时段间隔大于交易时段"""
        assert NON_TRADING_FUND_INTERVAL > TRADING_FUND_INTERVAL
        assert NON_TRADING_COMMODITY_INTERVAL > TRADING_COMMODITY_INTERVAL
        assert NON_TRADING_INDEX_INTERVAL > TRADING_INDEX_INTERVAL


class TestRealtimePusherInit:
    """RealtimePusher 初始化测试"""

    def test_init_default(self):
        """测试默认初始化"""
        pusher = RealtimePusher()

        assert pusher._data_manager is None
        assert pusher._ws_manager is None
        assert pusher._running is False
        assert pusher._tasks == []
        assert pusher._last_fund_data is None
        assert pusher._last_commodity_data is None
        assert pusher._last_index_data is None

    def test_init_with_dependencies(self):
        """测试依赖注入初始化"""
        mock_data_manager = MagicMock(spec=DataSourceManager)
        mock_ws_manager = MagicMock(spec=WebSocketManager)

        pusher = RealtimePusher(
            data_source_manager=mock_data_manager,
            websocket_manager=mock_ws_manager,
        )

        assert pusher._data_manager == mock_data_manager
        assert pusher._ws_manager == mock_ws_manager

    def test_data_manager_property_lazy_init(self):
        """测试 data_manager 属性延迟初始化"""
        pusher = RealtimePusher()

        with patch("api.dependencies.get_data_source_manager") as mock_get:
            mock_manager = MagicMock(spec=DataSourceManager)
            mock_get.return_value = mock_manager

            result = pusher.data_manager

            assert result == mock_manager
            assert pusher._data_manager == mock_manager

    def test_ws_manager_property_lazy_init(self):
        """测试 ws_manager 属性延迟初始化"""
        pusher = RealtimePusher()

        with patch("src.utils.realtime_pusher.get_websocket_manager") as mock_get:
            mock_manager = MagicMock(spec=WebSocketManager)
            mock_get.return_value = mock_manager

            result = pusher.ws_manager

            assert result == mock_manager
            assert pusher._ws_manager == mock_manager


class TestRealtimePusherDiffData:
    """RealtimePusher._diff_data 方法测试"""

    @pytest.fixture
    def pusher(self):
        """创建 RealtimePusher 实例"""
        return RealtimePusher()

    def test_diff_data_first_time(self, pusher):
        """测试首次数据（无旧数据）"""
        new_data = [{"code": "000001", "value": 1.0}]

        result = pusher._diff_data("funds", [], new_data)

        assert result == new_data

    def test_diff_data_no_changes(self, pusher):
        """测试数据无变化"""
        old_data = [{"code": "000001", "value": 1.0}]
        new_data = [{"code": "000001", "value": 1.0}]

        result = pusher._diff_data("funds", old_data, new_data)

        assert result is None

    def test_diff_data_with_changes(self, pusher):
        """测试数据有变化"""
        old_data = [{"code": "000001", "value": 1.0}]
        new_data = [{"code": "000001", "value": 1.5}]

        result = pusher._diff_data("funds", old_data, new_data)

        assert result == new_data

    def test_diff_data_new_item(self, pusher):
        """测试新增数据项"""
        old_data = [{"code": "000001", "value": 1.0}]
        new_data = [
            {"code": "000001", "value": 1.0},
            {"code": "000002", "value": 2.0},
        ]

        result = pusher._diff_data("funds", old_data, new_data)

        assert result == new_data

    def test_diff_data_removed_item(self, pusher):
        """测试删除数据项"""
        old_data = [
            {"code": "000001", "value": 1.0},
            {"code": "000002", "value": 2.0},
        ]
        new_data = [{"code": "000001", "value": 1.0}]

        result = pusher._diff_data("funds", old_data, new_data)

        assert result == new_data

    def test_diff_data_with_symbol_key(self, pusher):
        """测试使用 symbol 作为键"""
        old_data = [{"symbol": "AU9999", "price": 400.0}]
        new_data = [{"symbol": "AU9999", "price": 410.0}]

        result = pusher._diff_data("commodities", old_data, new_data)

        assert result == new_data

    def test_diff_data_with_fund_code_key(self, pusher):
        """测试使用 fund_code 作为键"""
        old_data = [{"fund_code": "000001", "value": 1.0}]
        new_data = [{"fund_code": "000001", "value": 1.2}]

        result = pusher._diff_data("funds", old_data, new_data)

        assert result == new_data

    def test_diff_data_multiple_changes(self, pusher):
        """测试多项数据变化"""
        old_data = [
            {"code": "000001", "value": 1.0},
            {"code": "000002", "value": 2.0},
        ]
        new_data = [
            {"code": "000001", "value": 1.5},
            {"code": "000002", "value": 2.5},
        ]

        result = pusher._diff_data("funds", old_data, new_data)

        assert len(result) == 2


class TestRealtimePusherTradingHours:
    """RealtimePusher 交易时段检测测试"""

    @pytest.fixture
    def pusher(self):
        """创建 RealtimePusher 实例"""
        return RealtimePusher()

    def test_is_trading_hours_open(self, pusher):
        """测试交易时段内"""
        with patch.object(
            pusher._trading_calendar,
            "is_within_trading_hours",
            return_value={"status": "open"},
        ):
            result = pusher._is_trading_hours()

            assert result is True

    def test_is_trading_hours_closed(self, pusher):
        """测试交易时段外"""
        with patch.object(
            pusher._trading_calendar,
            "is_within_trading_hours",
            return_value={"status": "closed"},
        ):
            result = pusher._is_trading_hours()

            assert result is False

    def test_is_trading_hours_exception(self, pusher):
        """测试交易时段检测异常"""
        with patch.object(
            pusher._trading_calendar,
            "is_within_trading_hours",
            side_effect=Exception("Network error"),
        ):
            result = pusher._is_trading_hours()

            assert result is False

    def test_get_intervals_trading(self, pusher):
        """测试获取交易时段间隔"""
        with patch.object(pusher, "_is_trading_hours", return_value=True):
            fund_int, commodity_int, index_int = pusher._get_intervals()

            assert fund_int == TRADING_FUND_INTERVAL
            assert commodity_int == TRADING_COMMODITY_INTERVAL
            assert index_int == TRADING_INDEX_INTERVAL

    def test_get_intervals_non_trading(self, pusher):
        """测试获取非交易时段间隔"""
        with patch.object(pusher, "_is_trading_hours", return_value=False):
            fund_int, commodity_int, index_int = pusher._get_intervals()

            assert fund_int == NON_TRADING_FUND_INTERVAL
            assert commodity_int == NON_TRADING_COMMODITY_INTERVAL
            assert index_int == NON_TRADING_INDEX_INTERVAL


class TestRealtimePusherFundCodes:
    """RealtimePusher._get_fund_codes 方法测试"""

    @pytest.fixture
    def pusher(self):
        """创建 RealtimePusher 实例"""
        return RealtimePusher()

    def test_get_fund_codes_success(self, pusher):
        """测试成功获取基金代码"""
        mock_config_manager = MagicMock()
        mock_fund_list = MagicMock()
        mock_fund_list.get_all_codes.return_value = ["000001", "000002"]

        with patch(
            "src.config.get_config_manager",
            return_value=mock_config_manager,
        ):
            mock_config_manager.load_funds.return_value = mock_fund_list

            result = pusher._get_fund_codes()

            assert result == ["000001", "000002"]

    def test_get_fund_codes_empty(self, pusher):
        """测试空基金列表"""
        mock_config_manager = MagicMock()
        mock_fund_list = MagicMock()
        mock_fund_list.get_all_codes.return_value = []

        with patch(
            "src.config.get_config_manager",
            return_value=mock_config_manager,
        ):
            mock_config_manager.load_funds.return_value = mock_fund_list

            result = pusher._get_fund_codes()

            assert result == []

    def test_get_fund_codes_exception(self, pusher):
        """测试获取基金代码异常"""
        with patch(
            "src.config.get_config_manager",
            side_effect=Exception("Config error"),
        ):
            result = pusher._get_fund_codes()

            assert result == []


class TestRealtimePusherHasSubscribers:
    """RealtimePusher._has_subscribers 方法测试"""

    def test_has_subscribers_true(self):
        """测试有订阅者"""
        mock_ws_manager = MagicMock(spec=WebSocketManager)
        mock_ws_manager.get_subscriptions_info.return_value = {"funds": 2}

        pusher = RealtimePusher(websocket_manager=mock_ws_manager)

        result = pusher._has_subscribers("funds")

        assert result is True

    def test_has_subscribers_false(self):
        """测试无订阅者"""
        mock_ws_manager = MagicMock(spec=WebSocketManager)
        mock_ws_manager.get_subscriptions_info.return_value = {}

        pusher = RealtimePusher(websocket_manager=mock_ws_manager)

        result = pusher._has_subscribers("funds")

        assert result is False

    def test_has_subscribers_zero_count(self):
        """测试订阅者数量为零"""
        mock_ws_manager = MagicMock(spec=WebSocketManager)
        mock_ws_manager.get_subscriptions_info.return_value = {"funds": 0}

        pusher = RealtimePusher(websocket_manager=mock_ws_manager)

        result = pusher._has_subscribers("funds")

        assert result is False


class TestRealtimePusherStartStop:
    """RealtimePusher start/stop 方法测试"""

    @pytest.fixture
    def pusher(self):
        """创建 RealtimePusher 实例"""
        return RealtimePusher()

    @pytest.mark.asyncio
    async def test_start(self, pusher):
        """测试启动推送器"""
        await pusher.start()

        assert pusher._running is True
        assert len(pusher._tasks) == 3

        # 清理
        await pusher.stop()

    @pytest.mark.asyncio
    async def test_start_twice(self, pusher):
        """测试重复启动"""
        await pusher.start()
        first_tasks = pusher._tasks.copy()

        await pusher.start()  # 应该被忽略

        assert pusher._tasks == first_tasks

        # 清理
        await pusher.stop()

    @pytest.mark.asyncio
    async def test_stop(self, pusher):
        """测试停止推送器"""
        await pusher.start()
        await pusher.stop()

        assert pusher._running is False
        assert pusher._tasks == []

    @pytest.mark.asyncio
    async def test_stop_not_running(self, pusher):
        """测试停止未运行的推送器"""
        # 不应该抛出异常
        await pusher.stop()

        assert pusher._running is False


class TestRealtimePusherPushLoops:
    """RealtimePusher 推送循环测试"""

    @pytest.fixture
    def mock_dependencies(self):
        """创建模拟依赖"""
        mock_data_manager = MagicMock(spec=DataSourceManager)
        mock_ws_manager = MagicMock(spec=WebSocketManager)
        mock_ws_manager.broadcast_to_subscription = AsyncMock(return_value=1)
        mock_ws_manager.get_subscriptions_info = MagicMock(return_value={})

        return mock_data_manager, mock_ws_manager

    @pytest.mark.asyncio
    async def test_push_funds_loop_no_subscribers(self, mock_dependencies):
        """测试基金推送循环 - 无订阅者"""
        mock_data_manager, mock_ws_manager = mock_dependencies
        mock_ws_manager.get_subscriptions_info = MagicMock(return_value={})

        pusher = RealtimePusher(
            data_source_manager=mock_data_manager,
            websocket_manager=mock_ws_manager,
        )
        pusher._running = True

        # 运行一次循环迭代
        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            mock_sleep.side_effect = [None, Exception("Stop loop")]
            try:
                await pusher._push_funds_loop()
            except Exception:
                pass

        mock_ws_manager.broadcast_to_subscription.assert_not_called()

    @pytest.mark.asyncio
    async def test_push_funds_loop_no_fund_codes(self, mock_dependencies):
        """测试基金推送循环 - 无基金代码"""
        mock_data_manager, mock_ws_manager = mock_dependencies
        mock_ws_manager.get_subscriptions_info = MagicMock(return_value={"funds": 1})

        pusher = RealtimePusher(
            data_source_manager=mock_data_manager,
            websocket_manager=mock_ws_manager,
        )
        pusher._running = True

        with patch.object(pusher, "_get_fund_codes", return_value=[]):
            with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
                mock_sleep.side_effect = [None, Exception("Stop loop")]
                try:
                    await pusher._push_funds_loop()
                except Exception:
                    pass

        mock_ws_manager.broadcast_to_subscription.assert_not_called()

    @pytest.mark.asyncio
    async def test_push_funds_loop_success(self, mock_dependencies):
        """测试基金推送循环 - 成功推送"""
        mock_data_manager, mock_ws_manager = mock_dependencies
        mock_ws_manager.get_subscriptions_info = MagicMock(return_value={"funds": 1})

        # 模拟数据源返回
        mock_result = DataSourceResult(
            success=True,
            data={"code": "000001", "net_value": 1.5},
            source="test",
        )
        mock_data_manager.fetch_batch = AsyncMock(return_value=[mock_result])

        pusher = RealtimePusher(
            data_source_manager=mock_data_manager,
            websocket_manager=mock_ws_manager,
        )
        pusher._running = True

        with patch.object(pusher, "_get_fund_codes", return_value=["000001"]):
            with patch.object(pusher, "_is_trading_hours", return_value=True):
                with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
                    # 第一次 sleep 后停止循环
                    mock_sleep.side_effect = [None, Exception("Stop loop")]
                    try:
                        await pusher._push_funds_loop()
                    except Exception:
                        pass

        # 验证广播被调用
        assert mock_ws_manager.broadcast_to_subscription.call_count >= 1

    @pytest.mark.asyncio
    async def test_push_funds_loop_partial_failure(self, mock_dependencies):
        """测试基金推送循环 - 部分失败"""
        mock_data_manager, mock_ws_manager = mock_dependencies
        mock_ws_manager.get_subscriptions_info = MagicMock(return_value={"funds": 1})

        # 模拟部分成功
        success_result = DataSourceResult(
            success=True,
            data={"code": "000001", "net_value": 1.5},
            source="test",
        )
        fail_result = DataSourceResult(
            success=False,
            error="Network error",
            source="test",
        )
        mock_data_manager.fetch_batch = AsyncMock(
            return_value=[success_result, fail_result]
        )

        pusher = RealtimePusher(
            data_source_manager=mock_data_manager,
            websocket_manager=mock_ws_manager,
        )
        pusher._running = True

        with patch.object(pusher, "_get_fund_codes", return_value=["000001", "000002"]):
            with patch.object(pusher, "_is_trading_hours", return_value=True):
                with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
                    # 第一次 sleep 后停止循环
                    mock_sleep.side_effect = [None, Exception("Stop loop")]
                    try:
                        await pusher._push_funds_loop()
                    except Exception:
                        pass

        # 应该只推送成功的数据，验证广播被调用
        assert mock_ws_manager.broadcast_to_subscription.call_count >= 1

    @pytest.mark.asyncio
    async def test_push_commodities_loop_success(self, mock_dependencies):
        """测试商品推送循环 - 成功推送"""
        mock_data_manager, mock_ws_manager = mock_dependencies
        mock_ws_manager.get_subscriptions_info = MagicMock(
            return_value={"commodities": 1}
        )

        mock_result = DataSourceResult(
            success=True,
            data=[{"symbol": "AU9999", "price": 400.0}],
            source="test",
        )
        mock_data_manager.fetch = AsyncMock(return_value=mock_result)

        pusher = RealtimePusher(
            data_source_manager=mock_data_manager,
            websocket_manager=mock_ws_manager,
        )
        pusher._running = True

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            mock_sleep.side_effect = [None, Exception("Stop loop")]
            try:
                await pusher._push_commodities_loop()
            except Exception:
                pass

        mock_ws_manager.broadcast_to_subscription.assert_called()

    @pytest.mark.asyncio
    async def test_push_commodities_loop_no_changes(self, mock_dependencies):
        """测试商品推送循环 - 数据无变化"""
        mock_data_manager, mock_ws_manager = mock_dependencies
        mock_ws_manager.get_subscriptions_info = MagicMock(
            return_value={"commodities": 1}
        )

        mock_result = DataSourceResult(
            success=True,
            data=[{"symbol": "AU9999", "price": 400.0}],
            source="test",
        )
        mock_data_manager.fetch = AsyncMock(return_value=mock_result)

        pusher = RealtimePusher(
            data_source_manager=mock_data_manager,
            websocket_manager=mock_ws_manager,
        )
        pusher._running = True
        pusher._last_commodity_data = [{"symbol": "AU9999", "price": 400.0}]

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            mock_sleep.side_effect = [None, Exception("Stop loop")]
            try:
                await pusher._push_commodities_loop()
            except Exception:
                pass

        # 数据无变化，不应该广播
        mock_ws_manager.broadcast_to_subscription.assert_not_called()

    @pytest.mark.asyncio
    async def test_push_indices_loop_success(self, mock_dependencies):
        """测试指数推送循环 - 成功推送"""
        mock_data_manager, mock_ws_manager = mock_dependencies
        mock_ws_manager.get_subscriptions_info = MagicMock(return_value={"indices": 1})

        mock_result = DataSourceResult(
            success=True,
            data={"code": "sh000001", "price": 3000.0},
            source="test",
        )
        mock_data_manager.fetch_batch = AsyncMock(return_value=[mock_result])

        pusher = RealtimePusher(
            data_source_manager=mock_data_manager,
            websocket_manager=mock_ws_manager,
        )
        pusher._running = True

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            mock_sleep.side_effect = [None, Exception("Stop loop")]
            try:
                await pusher._push_indices_loop()
            except Exception:
                pass

        mock_ws_manager.broadcast_to_subscription.assert_called()

    @pytest.mark.asyncio
    async def test_push_loop_exception_handling(self, mock_dependencies):
        """测试推送循环异常处理"""
        mock_data_manager, mock_ws_manager = mock_dependencies
        mock_ws_manager.get_subscriptions_info = MagicMock(
            return_value={"funds": 1}
        )
        mock_data_manager.fetch_batch = AsyncMock(
            side_effect=Exception("Network error")
        )

        pusher = RealtimePusher(
            data_source_manager=mock_data_manager,
            websocket_manager=mock_ws_manager,
        )
        pusher._running = True

        with patch.object(pusher, "_get_fund_codes", return_value=["000001"]):
            with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
                mock_sleep.side_effect = [None, Exception("Stop loop")]
                try:
                    await pusher._push_funds_loop()
                except Exception:
                    pass

        # 异常后循环应该继续运行（不会崩溃）


class TestRealtimePusherGlobal:
    """全局推送器函数测试"""

    def teardown_method(self):
        """每个测试后清理全局实例"""
        import src.utils.realtime_pusher as module

        module._pusher = None

    def test_get_realtime_pusher_singleton(self):
        """测试获取单例推送器"""
        pusher1 = get_realtime_pusher()
        pusher2 = get_realtime_pusher()

        assert pusher1 is pusher2

    def test_get_realtime_pusher_new_instance(self):
        """测试获取新实例"""
        import src.utils.realtime_pusher as module

        module._pusher = None

        pusher = get_realtime_pusher()

        assert isinstance(pusher, RealtimePusher)

    @pytest.mark.asyncio
    async def test_start_realtime_pusher(self):
        """测试启动全局推送器"""
        import src.utils.realtime_pusher as module

        module._pusher = None

        await start_realtime_pusher()

        assert module._pusher is not None
        assert module._pusher._running is True

        await module._pusher.stop()

    @pytest.mark.asyncio
    async def test_stop_realtime_pusher(self):
        """测试停止全局推送器"""
        import src.utils.realtime_pusher as module

        module._pusher = None

        await start_realtime_pusher()
        await stop_realtime_pusher()

        assert module._pusher._running is False

    @pytest.mark.asyncio
    async def test_stop_realtime_pusher_none(self):
        """测试停止未初始化的推送器"""
        import src.utils.realtime_pusher as module

        module._pusher = None

        # 不应该抛出异常
        await stop_realtime_pusher()


class TestRealtimePusherSupportedIndices:
    """RealtimePusher 支持的指数列表测试"""

    def test_supported_indices_not_empty(self):
        """测试支持的指数列表不为空"""
        assert len(RealtimePusher.SUPPORTED_INDICES) > 0

    def test_supported_indices_contains_main_indices(self):
        """测试支持的指数包含主要指数"""
        assert "sh000001" in RealtimePusher.SUPPORTED_INDICES  # 上证指数
        assert "sz399001" in RealtimePusher.SUPPORTED_INDICES  # 深证成指
        assert "sz399006" in RealtimePusher.SUPPORTED_INDICES  # 创业板指

    def test_supported_indices_contains_international(self):
        """测试支持的指数包含国际指数"""
        assert "hkHSI" in RealtimePusher.SUPPORTED_INDICES  # 恒生指数
        assert "usDJI" in RealtimePusher.SUPPORTED_INDICES  # 道琼斯
        assert "usIXIC" in RealtimePusher.SUPPORTED_INDICES  # 纳斯达克