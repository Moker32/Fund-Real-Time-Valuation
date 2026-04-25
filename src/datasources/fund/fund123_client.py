"""Fund123 HTTP 客户端封装模块

提供 fund123.cn 的 HTTP 客户端管理，包括：
- AsyncClient 生命周期管理
- CSRF token 获取和缓存
- 并发控制（Semaphore）
- 向后兼容的静态方法接口

使用单例模式，通过 get_instance() 获取实例。
"""

import asyncio
import logging
import re
import time

import httpx

logger = logging.getLogger(__name__)

BASE_URL = "https://www.fund123.cn"
# 最大并发数（提升以加快批量获取速度）
MAX_CONCURRENT_REQUESTS = 15
# CSRF token 过期时间（秒）
CSRF_TOKEN_TTL = 1800  # 30 分钟


class Fund123Client:
    """Fund123 HTTP 客户端封装

    管理 AsyncClient 生命周期和 CSRF token，提供向后兼容的静态方法接口。
    """

    _instance: "Fund123Client | None" = None

    def __init__(self):
        """初始化客户端实例"""
        self._client: httpx.AsyncClient | None = None
        self._csrf_token: str | None = None
        self._csrf_token_time: float = 0.0
        self._semaphore: asyncio.Semaphore | None = None
        self._csrf_lock: asyncio.Lock | None = None
        self._close_lock: asyncio.Lock | None = None

    def __ensure_client(self) -> httpx.AsyncClient:
        """确保 AsyncClient 已初始化（内部方法）"""
        if self._client is None:
            self._client = httpx.AsyncClient(
                limits=httpx.Limits(
                    max_keepalive_connections=10,
                    max_connections=20,
                    keepalive_expiry=30.0,
                ),
verify=True,  # 始终验证 SSL 证书
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
                    "Accept": "application/json, text/plain, */*",
                    "Accept-Language": "zh-CN,zh;q=0.9",
                    "Referer": "https://www.fund123.cn/fund",
                    "Origin": "https://www.fund123.cn",
                    "X-API-Key": "foobar",
                },
            )
        return self._client

    def __get_semaphore(self) -> asyncio.Semaphore:
        """获取并发控制信号量（内部方法）"""
        if self._semaphore is None:
            self._semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)
        return self._semaphore

    def __get_csrf_lock(self) -> asyncio.Lock:
        """获取 CSRF token 刷新锁（内部方法）"""
        if self._csrf_lock is None:
            self._csrf_lock = asyncio.Lock()
        return self._csrf_lock

    def __get_close_lock(self) -> asyncio.Lock:
        """获取关闭锁（内部方法）"""
        if self._close_lock is None:
            self._close_lock = asyncio.Lock()
        return self._close_lock

    async def __csrf_token_getter(self) -> str | None:
        """获取 CSRF token（内部方法）"""
        now = time.time()

        # 检查缓存的 token 是否有效
        if self._csrf_token and (now - self._csrf_token_time) < CSRF_TOKEN_TTL:
            return self._csrf_token

        # 使用锁保护，防止多个请求同时刷新 token
        async with self.__get_csrf_lock():
            # 双重检查：可能在等待锁期间其他协程已经刷新了 token
            if self._csrf_token and (now - self._csrf_token_time) < CSRF_TOKEN_TTL:
                return self._csrf_token

            try:
                # 访问首页获取 token
                response = await self.__ensure_client().get(f"{BASE_URL}/fund", timeout=15.0)
                response.raise_for_status()

                # 从响应文本中提取 CSRF
                csrf_match = re.search(r'"csrf":"([^"]+)"', response.text)
                if csrf_match:
                    self._csrf_token = csrf_match.group(1)
                    self._csrf_token_time = time.time()
                    logger.debug(f"获取到新的 CSRF token: {self._csrf_token[:20]}...")
                    return self._csrf_token

                logger.warning("无法从响应中提取 CSRF token")
                return None

            except Exception as e:
                logger.error(f"获取 CSRF token 失败: {e}")
                return None

    async def __refresh_csrf_token(self) -> bool:
        """刷新 CSRF token（内部方法）"""
        self._csrf_token = None
        self._csrf_token_time = 0
        token = await self.__csrf_token_getter()
        return token is not None

    async def __close_async(self):
        """关闭客户端（内部方法）"""
        async with self.__get_close_lock():
            if self._client is not None:
                await self._client.aclose()
                self._client = None
                self._csrf_token = None

    # -------------------------------------------------------------------------
    # 向后兼容的静态方法接口（供 Fund123DataSource 使用）
    # -------------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "Fund123Client":
        """获取单例实例"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def _ensure_client(cls) -> httpx.AsyncClient:
        """向后兼容：确保存在全局 AsyncClient"""
        return cls.get_instance().__ensure_client()

    @classmethod
    def _get_semaphore(cls) -> asyncio.Semaphore:
        """向后兼容：获取并发控制信号量"""
        return cls.get_instance().__get_semaphore()

    @classmethod
    def _get_csrf_lock(cls) -> asyncio.Lock:
        """向后兼容：获取 CSRF token 刷新锁"""
        return cls.get_instance().__get_csrf_lock()

    @classmethod
    def _get_close_lock(cls) -> asyncio.Lock:
        """向后兼容：获取关闭锁"""
        return cls.get_instance().__get_close_lock()

    @classmethod
    async def _get_csrf_token(cls) -> str | None:
        """向后兼容：获取 CSRF token"""
        return await cls.get_instance().__csrf_token_getter()

    @classmethod
    async def _refresh_csrf_token(cls) -> bool:
        """向后兼容：刷新 CSRF token"""
        return await cls.get_instance().__refresh_csrf_token()

    @classmethod
    async def close(cls):
        """向后兼容：关闭客户端"""
        if cls._instance is not None:
            await cls.get_instance().__close_async()

    # ========================================================================
    # 共享的基金数据获取方法（消除重复代码）
    # ========================================================================

    @classmethod
    async def _search_fund(cls, fund_code: str, timeout: float = 15.0) -> tuple[str | None, str | None, str | None]:
        """
        搜索基金获取 fund_key、fund_name 和 dayOfGrowth

        Args:
            fund_code: 基金代码
            timeout: 请求超时时间

        Returns:
            (fund_key, fund_name, day_of_growth) 元组，获取失败返回 (None, None, None)
        """
        csrf_token = await cls._get_csrf_token()
        if not csrf_token:
            return (None, None, None)

        search_url = f"{BASE_URL}/api/fund/searchFund?_csrf={csrf_token}"
        response = await cls._ensure_client().post(
            search_url, json={"fundCode": fund_code}, timeout=timeout
        )

        if not response.is_success:
            return (None, None, None)

        data = response.json()
        if not data.get("success"):
            return (None, None, None)

        fund_info = data.get("fundInfo", {})
        fund_key = fund_info.get("key")
        fund_name = fund_info.get("fundName", f"基金 {fund_code}")
        day_of_growth = fund_info.get("dayOfGrowth", "")

        return (fund_key, fund_name, day_of_growth)

    @classmethod
    def _build_intraday_payload(cls, fund_key: str, today: str) -> dict:
        """
        构建获取日内数据的请求 payload

        Args:
            fund_key: 基金标识
            today: 当前日期 (YYYY-MM-DD)

        Returns:
            请求 payload 字典
        """
        return {
            "startTime": today,
            "endTime": today,
            "limit": 200,
            "productId": fund_key,
            "format": True,
            "source": "WEALTHBFFWEB",
        }
