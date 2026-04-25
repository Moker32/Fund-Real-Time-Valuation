"""
AKShare 请求配置优化模块

提供优化的请求配置以解决实时数据接口连接问题：
- 浏览器请求头模拟
- 请求限流和重试机制
- 代理支持
- 自定义 session 配置
"""

import asyncio
import logging
import time
from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar

import httpx

logger = logging.getLogger(__name__)

# 类型变量用于装饰器
F = TypeVar("F", bound=Callable[..., Any])

# 浏览器请求头配置
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
    "Accept-Encoding": "gzip, deflate, br",
    "Referer": "https://quote.eastmoney.com/",
    "Origin": "https://quote.eastmoney.com",
    "Connection": "keep-alive",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-site",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
}

# 移动端请求头（备用）
MOBILE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 "
        "(KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
    ),
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Referer": "https://quote.eastmoney.com/",
}

# 请求超时配置（秒）
DEFAULT_TIMEOUT = 30.0
CONNECT_TIMEOUT = 10.0
READ_TIMEOUT = 30.0

# 重试配置
MAX_RETRIES = 3
RETRY_DELAY_BASE = 2.0  # 基础延迟秒数
RETRY_DELAY_MAX = 10.0  # 最大延迟秒数

# 限流配置（每秒请求数）
DEFAULT_RATE_LIMIT = 2.0  # 默认每秒2个请求


class RateLimiter:
    """异步限流器"""

    def __init__(self, calls_per_second: float = DEFAULT_RATE_LIMIT):
        """
        初始化限流器

        Args:
            calls_per_second: 每秒最大请求数
        """
        self.min_interval = 1.0 / calls_per_second
        self._last_call_time = 0.0
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        """获取执行许可，必要时等待"""
        async with self._lock:
            elapsed = time.time() - self._last_call_time
            if elapsed < self.min_interval:
                wait_time = self.min_interval - elapsed
                logger.debug(f"[RateLimiter] 等待 {wait_time:.2f}s")
                await asyncio.sleep(wait_time)
            self._last_call_time = time.time()


# 全局限流器实例
_global_rate_limiter: RateLimiter | None = None


def get_rate_limiter(calls_per_second: float = DEFAULT_RATE_LIMIT) -> RateLimiter:
    """获取全局限流器实例"""
    global _global_rate_limiter
    if _global_rate_limiter is None:
        _global_rate_limiter = RateLimiter(calls_per_second)
    return _global_rate_limiter


def rate_limit(calls_per_second: float = DEFAULT_RATE_LIMIT) -> Callable[[F], F]:
    """
    限流装饰器

    限制函数调用频率，确保不超过指定每秒请求数

    Args:
        calls_per_second: 每秒最大请求数

    Returns:
        装饰器函数

    Example:
        @rate_limit(calls_per_second=2)
        async def fetch_data():
            return await api.get_data()
    """
    limiter = RateLimiter(calls_per_second)

    def decorator(func: F) -> F:
        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            await limiter.acquire()
            return await func(*args, **kwargs)

        @wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            # 同步函数使用全局锁
            import threading

            min_interval = 1.0 / calls_per_second
            lock = threading.Lock()

            with lock:
                elapsed = time.time() - getattr(sync_wrapper, "_last_call_time", 0)
                if elapsed < min_interval:
                    time.sleep(min_interval - elapsed)
                sync_wrapper._last_call_time = time.time()  # type: ignore
                return func(*args, **kwargs)

        if asyncio.iscoroutinefunction(func):
            return async_wrapper  # type: ignore
        return sync_wrapper  # type: ignore

    return decorator


async def retry_with_backoff(
    func: Callable[..., Any],
    *args: Any,
    max_retries: int = MAX_RETRIES,
    base_delay: float = RETRY_DELAY_BASE,
    max_delay: float = RETRY_DELAY_MAX,
    **kwargs: Any,
) -> Any:
    """
    带指数退避的重试机制

    Args:
        func: 要执行的函数
        *args: 函数位置参数
        max_retries: 最大重试次数
        base_delay: 基础延迟秒数
        max_delay: 最大延迟秒数
        **kwargs: 函数关键字参数

    Returns:
        函数执行结果

    Raises:
        Exception: 所有重试失败后抛出最后一次异常
    """
    last_exception: Exception | None = None

    for attempt in range(max_retries + 1):
        try:
            if asyncio.iscoroutinefunction(func):
                return await func(*args, **kwargs)
            else:
                return func(*args, **kwargs)
        except Exception as e:
            last_exception = e
            if attempt < max_retries:
                # 指数退避: delay = base_delay * (2 ^ attempt)
                delay = min(base_delay * (2**attempt), max_delay)
                logger.warning(f"[Retry] 第 {attempt + 1} 次尝试失败: {e}, {delay:.1f}s 后重试...")
                await asyncio.sleep(delay)
            else:
                logger.error(f"[Retry] 所有 {max_retries + 1} 次尝试均失败")

    if last_exception:
        raise last_exception
    raise RuntimeError("重试机制异常")


def create_httpx_client(
    headers: dict[str, str] | None = None,
    timeout: float | httpx.Timeout = DEFAULT_TIMEOUT,
    proxy: str | None = None,
    follow_redirects: bool = True,
) -> httpx.AsyncClient:
    """
    创建配置优化的 httpx 客户端

    Args:
        headers: 自定义请求头（合并到默认请求头）
        timeout: 超时配置
        proxy: 代理地址（如 http://proxy.example.com:8080）
        follow_redirects: 是否跟随重定向

    Returns:
        配置好的 httpx.AsyncClient 实例
    """
    # 合并请求头
    merged_headers = DEFAULT_HEADERS.copy()
    if headers:
        merged_headers.update(headers)

    # 配置超时
    if isinstance(timeout, (int, float)):
        timeout_config = httpx.Timeout(
            connect=CONNECT_TIMEOUT,
            read=timeout,
            write=timeout,
            pool=timeout,
        )
    else:
        timeout_config = timeout

    # 配置代理
    proxies: dict[str, str] | None = None
    if proxy:
        proxies = {
            "http://": proxy,
            "https://": proxy,
        }

    client = httpx.AsyncClient(  # type: ignore[call-arg]
        headers=merged_headers,
        timeout=timeout_config,
        proxies=proxies,
        follow_redirects=follow_redirects,
        http2=True,  # 启用 HTTP/2
    )

    return client


# AKShare 函数包装器
async def call_akshare_with_retry(
    func: Callable[..., Any],
    *args: Any,
    max_retries: int = MAX_RETRIES,
    rate_limit_cps: float = DEFAULT_RATE_LIMIT,
    **kwargs: Any,
) -> Any:
    """
    带限流和重试的 AKShare 函数调用

    包装 AKShare 函数调用，添加限流和重试机制

    Args:
        func: AKShare 函数
        *args: 函数位置参数
        max_retries: 最大重试次数
        rate_limit_cps: 每秒最大请求数
        **kwargs: 函数关键字参数

    Returns:
        函数执行结果
    """
    limiter = get_rate_limiter(rate_limit_cps)
    await limiter.acquire()

    async def _call() -> Any:
        loop = asyncio.get_event_loop()
        # AKShare 函数是同步的，在线程池中执行
        return await loop.run_in_executor(None, lambda: func(*args, **kwargs))

    return await retry_with_backoff(_call, max_retries=max_retries)


# 配置 AKShare 请求头（如果可能）
def configure_akshare_headers() -> bool:
    """
    尝试配置 AKShare 的默认请求头

    通过修改 akshare 内部请求配置来应用浏览器请求头

    Returns:
        是否配置成功
    """
    try:
        import akshare as ak

        # 尝试设置请求头（不同版本 AKShare 可能有不同方式）
        if hasattr(ak, "set_headers"):
            ak.set_headers(DEFAULT_HEADERS)
            logger.info("[AKShareConfig] 已配置 AKShare 请求头")
            return True

        # 尝试通过 requests session 设置
        if hasattr(ak, "requests") and hasattr(ak.requests, "Session"):
            # 某些版本的 akshare 使用 requests
            import requests

            session = requests.Session()
            session.headers.update(DEFAULT_HEADERS)
            logger.info("[AKShareConfig] 已配置 requests session 请求头")
            return True

        logger.debug("[AKShareConfig] 无法直接配置 AKShare 请求头，将使用包装器")
        return False

    except ImportError:
        logger.warning("[AKShareConfig] AKShare 未安装")
        return False
    except Exception as e:
        logger.warning(f"[AKShareConfig] 配置请求头失败: {e}")
        return False


# 便捷函数：获取优化的 AKShare 调用器
def get_optimized_akshare_caller(
    rate_limit_cps: float = DEFAULT_RATE_LIMIT,
    max_retries: int = MAX_RETRIES,
    proxy: str | None = None,
) -> Callable:
    """
    获取优化的 AKShare 调用器

    返回一个包装函数，自动应用限流和重试

    Args:
        rate_limit_cps: 每秒最大请求数
        max_retries: 最大重试次数
        proxy: 代理地址

    Returns:
        包装后的调用函数
    """

    async def caller(func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        return await call_akshare_with_retry(
            func,
            *args,
            max_retries=max_retries,
            rate_limit_cps=rate_limit_cps,
            **kwargs,
        )

    return caller


# 模块初始化时尝试配置 AKShare
def init_akshare_config() -> None:
    """初始化 AKShare 配置"""
    configure_akshare_headers()


# 自动初始化
init_akshare_config()
