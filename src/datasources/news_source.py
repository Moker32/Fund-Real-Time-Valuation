"""
新闻数据源模块
实现从新浪财经获取财经新闻
"""

import asyncio
import re
import time
from typing import Any

import httpx
from bs4 import BeautifulSoup

from .base import DataSource, DataSourceResult, DataSourceType


class SinaNewsDataSource(DataSource):
    """新浪财经新闻数据源"""

    def __init__(self, timeout: float = 15.0, max_news: int = 20):
        """
        初始化新闻数据源

        Args:
            timeout: 请求超时时间
            max_news: 最大获取新闻数量
        """
        super().__init__(
            name="sina_news",
            source_type=DataSourceType.NEWS,
            timeout=timeout
        )
        self.max_news = max_news
        self.client = httpx.AsyncClient(
            timeout=timeout,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"
            }
        )
        self._news_cache: list[dict[str, Any]] = []
        self._cache_time: float = 0.0
        self._cache_timeout = 300.0  # 缓存5分钟

    async def fetch(self, category: str = "finance") -> DataSourceResult:
        """
        获取财经新闻

        Args:
            category: 新闻类别 (finance, stock, fund, economy)

        Returns:
            DataSourceResult: 新闻数据结果
        """
        # 检查缓存
        if self._is_cache_valid():
            return DataSourceResult(
                success=True,
                data=self._news_cache[:self.max_news],
                timestamp=self._cache_time,
                source=self.name,
                metadata={"from_cache": True, "category": category}
            )

        try:
            url = self._get_category_url(category)
            response = await self.client.get(url)
            response.raise_for_status()

            # 解析 HTML
            news_list = self._parse_news(response.text, category)

            if news_list:
                # 更新缓存
                self._news_cache = news_list
                self._cache_time = time.time()

                self._record_success()
                return DataSourceResult(
                    success=True,
                    data=news_list[:self.max_news],
                    timestamp=time.time(),
                    source=self.name,
                    metadata={"category": category}
                )

            return DataSourceResult(
                success=False,
                error="未获取到新闻数据",
                timestamp=time.time(),
                source=self.name,
                metadata={"category": category}
            )

        except httpx.HTTPStatusError as e:
            return DataSourceResult(
                success=False,
                error=f"新闻请求失败，状态码: {e.response.status_code}",
                timestamp=time.time(),
                source=self.name,
                metadata={"category": category, "status_code": e.response.status_code}
            )
        except httpx.RequestError as e:
            return DataSourceResult(
                success=False,
                error=f"新闻请求网络错误: {str(e)}",
                timestamp=time.time(),
                source=self.name,
                metadata={"category": category, "error_type": "RequestError"}
            )
        except Exception as e:
            return self._handle_error(e, self.name)

    async def fetch_batch(self, categories: list[str]) -> list[DataSourceResult]:
        """批量获取多类别新闻"""
        async def fetch_one(cat: str) -> DataSourceResult:
            return await self.fetch(cat)

        tasks = [fetch_one(cat) for cat in categories]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append(
                    DataSourceResult(
                        success=False,
                        error=str(result),
                        timestamp=time.time(),
                        source=self.name,
                        metadata={"category": categories[i]}
                    )
                )
            else:
                processed_results.append(result)

        return processed_results

    def _get_category_url(self, category: str) -> str:
        """获取各类别的新闻 URL"""
        urls = {
            "finance": "https://finance.sina.com.cn/",
            "stock": "https://finance.sina.com.cn/stock/",
            "fund": "https://finance.sina.com.cn/fund/",
            "economy": "https://finance.sina.com.cn/realstock/company/sz000001/nc.shtml",
            "global": "https://finance.sina.com.cn/forex/",
            "commodity": "https://finance.sina.com.cn/future/"
        }
        return urls.get(category, urls["finance"])

    def _parse_news(self, html: str, category: str) -> list[dict[str, Any]]:
        """
        解析新闻页面

        Args:
            html: 页面 HTML
            category: 新闻类别

        Returns:
            List[Dict]: 新闻列表
        """
        soup = BeautifulSoup(html, "lxml")
        news_list = []

        # 尝试多种选择器
        selectors = [
            ("财经要闻", ".news-list li a, .ctl00_ContentPlaceHolder1_MainNews_News1 tr a"),
            ("基金新闻", ".FundNewsList .news-item a, .list-nav li a"),
            ("股票新闻", ".StockNewsList .news-item a, .list_content a"),
        ]

        for name, selector in selectors:
            elements = soup.select(selector)
            if elements:
                for elem in elements[:self.max_news]:
                    try:
                        title = elem.get_text(strip=True)
                        link = elem.get("href", "")

                        if title and link and len(title) > 5:
                            # 提取发布时间
                            time_match = re.search(r"(\d{2}:\d{2}|\d{2}-\d{2})", title)
                            news_time = time_match.group(1) if time_match else ""

                            news_list.append({
                                "title": title,
                                "url": link if link.startswith("http") else f"https://finance.sina.com.cn{link}",
                                "time": news_time,
                                "category": category,
                                "source": "sina"
                            })
                    except Exception:
                        continue

                if news_list:
                    break

        # 如果选择器解析失败，尝试通用解析
        if not news_list:
            # 查找所有新闻链接
            all_links = soup.find_all("a", href=True)
            for link in all_links[:50]:
                try:
                    href = link.get("href", "")
                    text = link.get_text(strip=True)

                    # 筛选财经新闻链接
                    if self._is_finance_link(href, text):
                        news_list.append({
                            "title": text[:100] if len(text) > 100 else text,
                            "url": href if href.startswith("http") else f"https://finance.sina.com.cn{href}",
                            "time": "",
                            "category": category,
                            "source": "sina"
                        })
                except Exception:
                    continue

        return news_list[:self.max_news]

    def _is_finance_link(self, href: str, text: str) -> bool:
        """判断是否为财经新闻链接"""
        # 检查链接模式
        patterns = [
            r"finance\.sina\.com\.cn",
            r"stock\.sina\.com\.cn",
            r"fund\.sina\.com\.cn",
            r"/\d{4}-\d{2}/\d{2}/",
        ]

        # 排除非新闻链接
        exclude_patterns = [
            r"javascript:",
            r"#",
            r"login",
            r"register",
            r"app\.html"
        ]

        for pattern in exclude_patterns:
            if re.search(pattern, href.lower()):
                return False

        for pattern in patterns:
            if re.search(pattern, href):
                return True

        # 基于标题判断
        finance_keywords = ["基金", "股票", "A股", "港股", "美股", "大盘", "指数", "行情",
                           "涨幅", "跌幅", "涨停", "跌停", "IPO", "财报", "业绩", "央行"]
        for keyword in finance_keywords:
            if keyword in text:
                return True

        return False

    def _is_cache_valid(self) -> bool:
        """检查缓存是否有效"""
        if not self._news_cache:
            return False
        return (time.time() - self._cache_time) < self._cache_timeout

    def clear_cache(self):
        """清空缓存"""
        self._news_cache = []
        self._cache_time = 0.0

    async def close(self):
        """关闭 HTTP 客户端"""
        await self.client.aclose()

    def get_status(self) -> dict[str, Any]:
        """获取数据源状态"""
        status = super().get_status()
        status["cache_size"] = len(self._news_cache)
        status["cache_timeout"] = self._cache_timeout
        status["max_news"] = self.max_news
        return status


class NewsAggregatorDataSource(DataSource):
    """新闻聚合数据源 - 整合多个新闻源"""

    def __init__(self, timeout: float = 20.0):
        super().__init__(
            name="news_aggregator",
            source_type=DataSourceType.NEWS,
            timeout=timeout
        )
        self._sources: list[DataSource] = []
        self._default_source: DataSource | None = None

    def add_source(self, source: DataSource, is_default: bool = False):
        """
        添加新闻数据源

        Args:
            source: 数据源实例
            is_default: 是否为默认数据源
        """
        self._sources.append(source)
        if is_default or self._default_source is None:
            self._default_source = source

    async def fetch(self, category: str = "finance") -> DataSourceResult:
        """
        获取新闻数据

        Args:
            category: 新闻类别

        Returns:
            DataSourceResult: 新闻数据结果
        """
        errors = []

        # 优先使用默认数据源
        if self._default_source:
            try:
                result = await self._default_source.fetch(category)
                if result.success:
                    return result
                errors.append(f"{self._default_source.name}: {result.error}")
            except Exception as e:
                errors.append(f"{self._default_source.name}: {str(e)}")

        # 尝试其他数据源
        for source in self._sources:
            if source == self._default_source:
                continue
            try:
                result = await source.fetch(category)
                if result.success:
                    return result
                errors.append(f"{source.name}: {result.error}")
            except Exception as e:
                errors.append(f"{source.name}: {str(e)}")

        # 所有数据源都失败
        return DataSourceResult(
            success=False,
            error=f"所有新闻数据源均失败: {'; '.join(errors)}",
            timestamp=time.time(),
            source=self.name,
            metadata={"category": category, "errors": errors}
        )

    async def fetch_batch(self, categories: list[str]) -> list[DataSourceResult]:
        """批量获取多类别新闻"""
        async def fetch_one(cat: str) -> DataSourceResult:
            return await self.fetch(cat)

        tasks = [fetch_one(cat) for cat in categories]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append(
                    DataSourceResult(
                        success=False,
                        error=str(result),
                        timestamp=time.time(),
                        source=self.name,
                        metadata={"category": categories[i]}
                    )
                )
            else:
                processed_results.append(result)

        return processed_results

    def get_status(self) -> dict[str, Any]:
        """获取聚合器状态"""
        status = super().get_status()
        status["source_count"] = len(self._sources)
        status["default_source"] = self._default_source.name if self._default_source else None
        status["sources"] = [s.name for s in self._sources]
        return status

    async def close(self):
        """关闭所有数据源"""
        for source in self._sources:
            if hasattr(source, 'close'):
                try:
                    await source.close()
                except Exception:
                    pass


# 导出类
__all__ = ["SinaNewsDataSource", "NewsAggregatorDataSource"]
