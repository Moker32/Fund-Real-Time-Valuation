"""
AKShare 舆情数据源测试

测试:
1. AKShareEconomicNewsDataSource - 全球宏观事件（财经日历）
2. AKShareWeiboSentimentDataSource - 微博舆情
3. AKShareSentimentAggregatorDataSource - 舆情聚合
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.datasources.akshare_sentiment_source import (
    AKShareEconomicNewsDataSource,
    AKShareSentimentAggregatorDataSource,
    AKShareWeiboSentimentDataSource,
)
from src.datasources.base import DataSourceType


class TestAKShareEconomicNewsDataSource:
    """测试全球宏观事件数据源"""

    def test_init(self):
        """测试初始化"""
        ds = AKShareEconomicNewsDataSource(timeout=10.0)
        
        assert ds.name == "akshare_economic_news"
        assert ds.source_type == DataSourceType.NEWS
        assert ds.timeout == 10.0
        assert ds._cache_timeout == 300.0

    def test_init_default_timeout(self):
        """测试默认超时时间"""
        ds = AKShareEconomicNewsDataSource()
        assert ds.timeout == 15.0

    @pytest.mark.asyncio
    async def test_fetch_with_empty_cache(self):
        """测试无缓存时获取数据"""
        ds = AKShareEconomicNewsDataSource()
        
        # Mock akshare 调用
        mock_df = MagicMock()
        mock_df.empty = False
        mock_df.to_dict.return_value = [
            {"日期": "2024-01-01", "时间": "10:00", "地区": "美国", "事件": "非农数据", "公布": 3.5, "预期": 3.0, "前值": 2.8, "重要性": 3}
        ]
        
        with patch.object(ds, '_fetch_data', return_value=mock_df):
            result = await ds.fetch("20240101")
            
            assert result.success is True
            assert isinstance(result.data, list)
            assert len(result.data) == 1
            assert result.metadata["date"] == "20240101"
            assert result.metadata["count"] == 1

    @pytest.mark.asyncio
    async def test_fetch_with_cache(self):
        """测试缓存命中"""
        ds = AKShareEconomicNewsDataSource()
        
        # 预先填充缓存
        cached_data = [{"日期": "2024-01-01", "事件": "测试事件"}]
        ds._cache = cached_data
        ds._cache_time = 1000.0
        
        # 设置缓存时间戳为当前时间附近
        import time
        ds._cache_time = time.time() - 60  # 1分钟前，在5分钟缓存期内
        
        result = await ds.fetch("20240101")
        
        assert result.success is True
        assert result.data == cached_data
        assert result.metadata.get("from_cache") is True

    @pytest.mark.asyncio
    async def test_fetch_no_data(self):
        """测试无数据返回"""
        ds = AKShareEconomicNewsDataSource()
        
        with patch.object(ds, '_fetch_data', return_value=None):
            result = await ds.fetch("20240101")
            
            assert result.success is False
            assert result.error == "未获取到财经事件数据"

    @pytest.mark.asyncio
    async def test_fetch_empty_dataframe(self):
        """测试空DataFrame返回"""
        ds = AKShareEconomicNewsDataSource()
        
        mock_df = MagicMock()
        mock_df.empty = True
        
        with patch.object(ds, '_fetch_data', return_value=mock_df):
            result = await ds.fetch("20240101")
            
            assert result.success is False
            assert result.error == "未获取到财经事件数据"

    @pytest.mark.asyncio
    async def test_fetch_batch(self):
        """测试批量获取"""
        ds = AKShareEconomicNewsDataSource()
        
        mock_df = MagicMock()
        mock_df.empty = False
        mock_df.to_dict.return_value = [{"日期": "2024-01-01", "事件": "测试"}]
        
        with patch.object(ds, '_fetch_data', return_value=mock_df):
            results = await ds.fetch_batch(["20240101", "20240102"])
            
            assert len(results) == 2
            assert all(r.success for r in results)

    def test_is_cache_valid(self):
        """测试缓存有效性检查"""
        ds = AKShareEconomicNewsDataSource()
        
        # 空缓存
        assert ds._is_cache_valid() is False
        
        # 有缓存但超时
        ds._cache = [{}]
        ds._cache_time = 0
        assert ds._is_cache_valid() is False
        
        # 有效缓存
        import time
        ds._cache_time = time.time() - 60  # 1分钟前
        assert ds._is_cache_valid() is True

    def test_clear_cache(self):
        """测试清空缓存"""
        ds = AKShareEconomicNewsDataSource()
        
        ds._cache = [{"test": "data"}]
        ds._cache_time = 1000.0
        
        ds.clear_cache()
        
        assert ds._cache == []
        assert ds._cache_time == 0.0


class TestAKShareWeiboSentimentDataSource:
    """测试微博舆情数据源"""

    def test_init(self):
        """测试初始化"""
        ds = AKShareWeiboSentimentDataSource(timeout=10.0)
        
        assert ds.name == "akshare_weibo_sentiment"
        assert ds.source_type == DataSourceType.NEWS
        assert ds.timeout == 10.0
        assert ds._cache_timeout == 180.0

    def test_init_default_timeout(self):
        """测试默认超时时间"""
        ds = AKShareWeiboSentimentDataSource()
        assert ds.timeout == 15.0

    def test_time_periods(self):
        """测试时间周期映射"""
        ds = AKShareWeiboSentimentDataSource()
        
        assert ds.TIME_PERIODS["2h"] == "CNHOUR2"
        assert ds.TIME_PERIODS["6h"] == "CNHOUR6"
        assert ds.TIME_PERIODS["12h"] == "CNHOUR12"
        assert ds.TIME_PERIODS["24h"] == "CNHOUR24"
        assert ds.TIME_PERIODS["7d"] == "CNDAY7"
        assert ds.TIME_PERIODS["30d"] == "CNDAY30"
        assert ds.DEFAULT_PERIOD == "12h"

    @pytest.mark.asyncio
    async def test_fetch_with_period_2h(self):
        """测试获取2小时周期数据"""
        ds = AKShareWeiboSentimentDataSource()
        
        mock_df = MagicMock()
        mock_df.empty = False
        mock_df.to_dict.return_value = [
            {"name": "股票A", "rate": 85.5},
            {"name": "股票B", "rate": 72.3},
        ]
        
        with patch.object(ds, '_fetch_data', return_value=mock_df):
            result = await ds.fetch("2h")
            
            assert result.success is True
            assert len(result.data) == 2
            assert result.metadata["period"] == "2h"

    @pytest.mark.asyncio
    async def test_fetch_with_invalid_period(self):
        """测试无效周期参数，使用默认"""
        ds = AKShareWeiboSentimentDataSource()
        
        mock_df = MagicMock()
        mock_df.empty = False
        mock_df.to_dict.return_value = [{"name": "test", "rate": 50.0}]
        
        with patch.object(ds, '_fetch_data', return_value=mock_df) as mock_fetch:
            await ds.fetch("invalid_period")
            
            # 应该使用默认的12h周期
            mock_fetch.assert_called_once_with("CNHOUR12")

    @pytest.mark.asyncio
    async def test_fetch_with_cache(self):
        """测试缓存命中"""
        ds = AKShareWeiboSentimentDataSource()
        
        import time
        cached_data = [{"name": "test", "rate": 50.0}]
        ds._cache = cached_data
        ds._cache_time = time.time() - 60  # 1分钟前
        
        result = await ds.fetch("12h")
        
        assert result.success is True
        assert result.data == cached_data
        assert result.metadata.get("from_cache") is True

    @pytest.mark.asyncio
    async def test_fetch_batch(self):
        """测试批量获取"""
        ds = AKShareWeiboSentimentDataSource()
        
        mock_df = MagicMock()
        mock_df.empty = False
        mock_df.to_dict.return_value = [{"name": "test", "rate": 50.0}]
        
        with patch.object(ds, '_fetch_data', return_value=mock_df):
            results = await ds.fetch_batch(["2h", "6h", "12h"])
            
            assert len(results) == 3

    def test_clear_cache(self):
        """测试清空缓存"""
        ds = AKShareWeiboSentimentDataSource()
        
        ds._cache = [{"name": "test"}]
        ds._cache_time = 1000.0
        
        ds.clear_cache()
        
        assert ds._cache == []
        assert ds._cache_time == 0.0


class TestAKShareSentimentAggregatorDataSource:
    """测试舆情聚合数据源"""

    def test_init(self):
        """测试初始化"""
        ds = AKShareSentimentAggregatorDataSource(timeout=30.0)
        
        assert ds.name == "akshare_sentiment_aggregator"
        assert ds.source_type == DataSourceType.NEWS
        assert ds.timeout == 30.0
        assert ds._economic_news is not None
        assert ds._weibo_sentiment is not None

    @pytest.mark.asyncio
    async def test_fetch_economic_only(self):
        """测试仅获取财经事件"""
        ds = AKShareSentimentAggregatorDataSource()
        
        mock_economic = MagicMock()
        mock_economic.success = True
        mock_economic.data = [{"日期": "2024-01-01", "事件": "测试"}]
        
        ds._economic_news.fetch = AsyncMock(return_value=mock_economic)
        
        result = await ds.fetch("economic", date="20240101")
        
        assert result.success is True
        assert result.data is not None

    @pytest.mark.asyncio
    async def test_fetch_weibo_only(self):
        """测试仅获取微博舆情"""
        ds = AKShareSentimentAggregatorDataSource()
        
        mock_weibo = MagicMock()
        mock_weibo.success = True
        mock_weibo.data = [{"name": "股票A", "rate": 80.0}]
        
        ds._weibo_sentiment.fetch = AsyncMock(return_value=mock_weibo)
        
        result = await ds.fetch("weibo", period="12h")
        
        assert result.success is True

    @pytest.mark.asyncio
    async def test_fetch_all(self):
        """测试获取所有舆情数据"""
        from src.datasources.base import DataSourceResult
        
        ds = AKShareSentimentAggregatorDataSource()
        
        mock_economic = DataSourceResult(
            success=True,
            data=[{"日期": "2024-01-01"}],
            timestamp=1000.0,
            source="test"
        )
        
        mock_weibo = DataSourceResult(
            success=True,
            data=[{"name": "股票A", "rate": 80.0}],
            timestamp=1000.0,
            source="test"
        )
        
        ds._economic_news.fetch = AsyncMock(return_value=mock_economic)
        ds._weibo_sentiment.fetch = AsyncMock(return_value=mock_weibo)
        
        result = await ds.fetch("all")
        
        assert result.success is True
        assert result.data is not None
        assert result.data["economic"] is not None
        assert result.data["weibo"] is not None
        assert result.data["errors"] == []

    @pytest.mark.asyncio
    async def test_fetch_all_with_partial_failure(self):
        """测试部分失败的情况"""
        from src.datasources.base import DataSourceResult
        
        ds = AKShareSentimentAggregatorDataSource()
        
        # 成功的经济数据
        mock_economic = DataSourceResult(
            success=True,
            data=[{"日期": "2024-01-01"}],
            timestamp=1000.0,
            source="test"
        )
        
        # 微博舆情返回 Exception - 这会触发 gather 的 return_exceptions
        # 模拟网络错误的情况
        mock_weibo = Exception("Network error")
        
        ds._economic_news.fetch = AsyncMock(return_value=mock_economic)
        ds._weibo_sentiment.fetch = AsyncMock(return_value=mock_weibo)
        
        result = await ds.fetch("all")
        
        # 经济数据成功，应该返回成功
        assert result.success is True
        assert result.data["economic"] is not None
        assert result.data["weibo"] is None
        assert "weibo" in str(result.data["errors"])

    @pytest.mark.asyncio
    async def test_fetch_invalid_type(self):
        """测试无效数据类型"""
        ds = AKShareSentimentAggregatorDataSource()
        
        result = await ds.fetch("invalid_type")
        
        assert result.success is False
        assert "未知数据类型" in result.error

    @pytest.mark.asyncio
    async def test_fetch_batch(self):
        """测试批量获取"""
        ds = AKShareSentimentAggregatorDataSource()
        
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.data = {}
        
        ds.fetch = AsyncMock(return_value=mock_result)
        
        results = await ds.fetch_batch(["economic", "weibo"])
        
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_close(self):
        """测试关闭数据源"""
        ds = AKShareSentimentAggregatorDataSource()
        
        # 应该不会抛出异常
        await ds.close()
