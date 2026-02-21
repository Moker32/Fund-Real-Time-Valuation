"""
FastAPI 应用入口
基金实时估值 Web API 服务
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from src.datasources.cache_cleaner import CacheCleaner, get_cache_cleaner
from src.datasources.cache_warmer import CacheWarmer
from src.datasources.manager import create_default_manager
from src.utils.log_buffer import get_log_buffer

logger = logging.getLogger(__name__)

from .dependencies import (
    close_data_source_manager,
    get_data_source_manager,
    set_data_source_manager,
)
from .models import DataSourceHealthItem, HealthDetailResponse, HealthResponse
from .routes import (
    bonds,
    cache,
    commodities,
    datasource,
    funds,
    indices,
    news,
    overview,
    sectors,
    sentiment,
    stocks,
    trading_calendar,
)

# 配置日志：将日志同时输出到缓冲区和标准输出
_root_logger = logging.getLogger()
_buffer_handler = get_log_buffer()
_buffer_handler.setLevel(logging.DEBUG)
_root_logger.addHandler(_buffer_handler)
_root_logger.setLevel(logging.DEBUG)

# 全局预热器实例
_cache_warmer: CacheWarmer | None = None
# 全局缓存清理器实例
_cache_cleaner: CacheCleaner | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理

    Args:
        app: FastAPI 应用实例
    """
    import os

    global _cache_warmer, _cache_cleaner

    # 启动时初始化数据源管理器
    manager = create_default_manager()
    set_data_source_manager(manager)

    # 快速启动模式 - 跳过缓存预热
    skip_warmup = os.environ.get("SKIP_CACHE_WARMUP") == "1"

    if skip_warmup:
        logger.info("快速启动模式：跳过缓存预热")
    else:
        # 创建缓存预热器（用于后续操作）
        _cache_warmer = CacheWarmer(manager)

        # 预加载所有缓存数据到内存（不阻塞服务启动）
        asyncio.create_task(_cache_warmer.preload_all_cache(timeout=5))

        # 预热基金信息缓存（名称、类型等）- 并行获取，不阻塞服务启动
        asyncio.create_task(_cache_warmer.preload_fund_info_cache(timeout=60))

        # 启动缓存预热（不阻塞服务启动）
        asyncio.create_task(_cache_warmer.start_background_warmup(interval=300))

        # 启动时清理过期缓存（不阻塞服务启动）
        try:
            from src.datasources.cache_cleaner import startup_cleanup

            asyncio.create_task(startup_cleanup())
            logger.info("启动时缓存清理任务已提交")
        except Exception as e:
            logger.warning(f"启动清理任务失败: {e}")

        # 启动后台定时清理任务（每小时执行一次）
        try:
            from src.datasources.cache_cleaner import start_background_cleanup_task

            start_background_cleanup_task(interval=3600)
            logger.info("后台定时清理任务已启动")
        except Exception as e:
            logger.warning(f"启动后台清理任务失败: {e}")

    # 启动后台健康检查（非阻塞）
    asyncio.create_task(manager.start_background_health_check())

    yield

    # 停止后台预热
    if _cache_warmer:
        _cache_warmer.stop()

    # 停止后台清理任务
    try:
        cleaner = get_cache_cleaner()
        if cleaner:
            cleaner.stop()
    except Exception:
        pass

    # 关闭时清理资源
    await close_data_source_manager()


# 创建 FastAPI 应用
app = FastAPI(
    title="基金实时估值 API",
    description="""
## 基金实时估值 Web API 服务

提供以下功能:
- **基金数据**: 获取基金实时估值、历史净值等
- **商品行情**: 获取黄金、原油等大宗商品实时行情
- **全球指数**: 获取全球主要市场指数行情
- **行业板块**: 获取A股行业板块和概念板块行情
- **交易日历**: 查询全球市场交易/休市日期
- **财经新闻**: 获取最新财经新闻
- **舆情数据**: 获取市场舆情和情绪指标
- **健康检查**: 服务状态监控

### 数据源

- **基金**: 天天基金、新浪财经
- **商品**: yfinance、AKShare
- **指数**: yfinance、AKShare
- **板块**: 东方财富
    """,
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    terms_of_service="https://github.com",
    contact={
        "name": "API Support",
        "url": "https://github.com",
    },
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT",
    },
)

import os

# 配置 CORS
# 使用环境变量控制允许的来源，生产环境应设置为具体的域名
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== 全局异常处理器 ====================


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """
    处理 HTTP 异常 (400, 404, 500 等)

    Args:
        request: 请求对象
        exc: HTTP 异常

    Returns:
        JSONResponse: 错误响应
    """
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": exc.detail if isinstance(exc.detail, str) else "HTTP Error",
            "detail": str(exc.detail) if not isinstance(exc.detail, str) else None,
            "timestamp": datetime.now().isoformat() + "Z",
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    处理请求验证错误 (422)

    Args:
        request: 请求对象
        exc: 验证异常

    Returns:
        JSONResponse: 错误响应
    """
    errors = []
    for error in exc.errors():
        errors.append(f"{'.'.join(str(loc) for loc in error['loc'])}: {error['msg']}")

    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "error": "请求参数验证失败",
            "detail": "; ".join(errors),
            "timestamp": datetime.now().isoformat() + "Z",
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """
    处理通用异常 (500 Internal Server Error)

    Args:
        request: 请求对象
        exc: 通用异常

    Returns:
        JSONResponse: 错误响应
    """
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Internal Server Error",
            "detail": str(exc) if app.debug else "服务器内部错误，请稍后重试",
            "timestamp": datetime.now().isoformat() + "Z",
        },
    )


# ==================== 路由注册 ====================

# 注册路由
app.include_router(funds.router)
app.include_router(commodities.router)
app.include_router(indices.router)
app.include_router(sectors.router)
app.include_router(overview.router)
app.include_router(cache.router)
app.include_router(trading_calendar.router)
app.include_router(news.router)
app.include_router(sentiment.router)
app.include_router(datasource.router)
app.include_router(stocks.router)
app.include_router(bonds.router)


# ==================== 静态文件服务 ====================

import os
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

_dist_dir = "web/dist"


def setup_static_files(app: FastAPI):
    """配置静态文件服务和 SPA fallback"""

    if not os.path.isdir(_dist_dir):
        app.logger.warning(f"静态文件目录不存在: {_dist_dir}，跳过静态文件挂载")
        return

    # 挂载静态文件
    app.mount("/static", StaticFiles(directory=_dist_dir), name="static")

    # 注册异常处理器：404 时返回 index.html
    from fastapi.exceptions import RequestValidationError
    from starlette.exceptions import HTTPException as StarletteHTTPException

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        if exc.status_code == 404:
            path = request.url.path

            # /assets 路径：尝试返回实际的静态文件
            if path.startswith("/assets/") or path.startswith("/vite."):
                file_path = os.path.join(_dist_dir, path.lstrip("/"))
                if os.path.isfile(file_path):
                    return FileResponse(file_path)

            # 其他路径：返回 index.html（SPA fallback），排除 API 路径
            if (
                not path.startswith("/api/")
                and not path.startswith("/docs")
                and not path.startswith("/redoc")
            ):
                index_path = os.path.join(_dist_dir, "index.html")
                if os.path.isfile(index_path):
                    return FileResponse(index_path)
        # 其他错误让默认处理器处理
        from fastapi.responses import JSONResponse

        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
        )


setup_static_files(app)


@app.get(
    "/",
    summary="前端入口",
    description="返回前端 index.html",
)
async def root():
    """
    前端入口

    Returns:
        FileResponse: 前端 index.html
    """
    index_path = os.path.join(_dist_dir, "index.html")
    if os.path.isfile(index_path):
        return FileResponse(index_path)
    return {
        "name": "基金实时估值 API",
        "version": "0.1.0",
        "description": "前端未构建，请运行 pnpm run build:web",
    }


@app.get(
    "/api/info",
    summary="API 详细信息",
    description="返回 API 详细信息，包括所有可用端点",
)
async def api_info():
    """
    API 详细信息

    Returns:
        dict: API 详细信息
    """
    return {
        "name": "基金实时估值 API",
        "version": "0.1.0",
        "description": "基金实时估值 Web API 服务",
        "docs": "/docs",
        "redoc": "/redoc",
        "endpoints": {
            "health": {
                "simple": "/api/health/simple",
                "detailed": "/api/health",
            },
            "funds": {
                "list": "GET /api/funds",
                "detail": "GET /api/funds/{fund_code}",
                "estimate": "GET /api/funds/{fund_code}/estimate",
                "history": "GET /api/funds/{fund_code}/history",
                "intraday": "GET /api/funds/{fund_code}/intraday",
            },
            "commodities": {
                "list": "GET /api/commodities",
                "gold": "GET /api/commodities/gold",
                "oil": "GET /api/commodities/oil",
                "search": "GET /api/commodities/search",
            },
            "indices": "GET /api/indices",
            "sectors": "GET /api/sectors",
            "news": {
                "list": "GET /api/news",
                "categories": "GET /api/news/categories",
            },
            "sentiment": {
                "economic": "GET /api/sentiment/economic",
                "weibo": "GET /api/sentiment/weibo",
                "all": "GET /api/sentiment/all",
            },
            "trading_calendar": {
                "calendar": "GET /trading-calendar/calendar/{market}",
                "is_trading_day": "GET /trading-calendar/is-trading-day/{market}",
                "next_trading_day": "GET /trading-calendar/next-trading-day/{market}",
                "market_status": "GET /trading-calendar/market-status",
            },
            "cache": "GET /api/cache/stats",
            "datasource": {
                "statistics": "GET /api/datasource/statistics",
                "health": "GET /api/datasource/health",
                "sources": "GET /api/datasource/sources",
            },
            "logs": {
                "get": "GET /api/logs",
                "clear": "DELETE /api/logs",
            },
        },
    }


@app.get(
    "/api/health",
    response_model=HealthDetailResponse,
    summary="健康检查",
    description="检查服务状态和数据源健康状况",
    responses={
        200: {"description": "服务正常"},
        503: {"description": "服务异常"},
    },
)
async def health_check() -> HealthDetailResponse:
    """
    健康检查

    Returns:
        HealthDetailResponse: 健康检查结果
    """
    manager = get_data_source_manager()

    # 获取数据源健康状态
    health_result = await manager.health_check()

    # 构建数据源状态列表
    data_sources: list[DataSourceHealthItem] = []
    for source_name, result in health_result.get("sources", {}).items():
        data_sources.append(
            DataSourceHealthItem(
                source=source_name,
                status=result.get("status", "unknown"),
                response_time_ms=result.get("response_time_ms"),
            )
        )

    return HealthDetailResponse(
        status="healthy" if health_result.get("healthy_count", 0) > 0 else "degraded",
        version="0.1.0",
        timestamp=datetime.now(),
        total_sources=health_result.get("total_sources", 0),
        healthy_count=health_result.get("healthy_count", 0),
        unhealthy_count=health_result.get("unhealthy_count", 0),
        data_sources=data_sources,
    )


@app.get(
    "/api/health/simple",
    response_model=HealthResponse,
    summary="简单健康检查",
    description="仅返回服务基本状态",
)
async def simple_health_check() -> HealthResponse:
    """
    简单健康检查

    Returns:
        HealthResponse: 基本健康状态
    """
    return HealthResponse(
        status="healthy",
        version="0.1.0",
        timestamp=datetime.now(),
    )


class LogEntryResponse(BaseModel):
    """日志条目响应"""

    timestamp: datetime
    level: str
    logger: str
    message: str


class LogsResponse(BaseModel):
    """日志列表响应"""

    logs: list[LogEntryResponse]
    total: int


@app.get(
    "/api/logs",
    response_model=LogsResponse,
    summary="获取日志",
    description="获取最近的日志记录（支持过滤）",
)
async def get_logs(
    level: str | None = None,
    limit: int = 100,
    logger: str | None = None,
) -> LogsResponse:
    """
    获取日志

    Args:
        level: 日志级别 (DEBUG, INFO, WARNING, ERROR)
        limit: 返回数量 (默认 100)
        logger: 日志器名称过滤

    Returns:
        LogsResponse: 日志列表
    """
    buffer = get_log_buffer()
    logs = buffer.get_logs(level=level, limit=limit, logger=logger)
    return LogsResponse(
        logs=[
            LogEntryResponse(
                timestamp=log.timestamp,
                level=log.level,
                logger=log.logger,
                message=log.message,
            )
            for log in logs
        ],
        total=len(logs),
    )


@app.delete(
    "/api/logs",
    summary="清空日志",
    description="清空日志缓冲区",
)
async def clear_logs():
    """清空日志缓冲区"""
    buffer = get_log_buffer()
    buffer.clear()
    return {"message": "日志已清空"}


# 导出应用实例
__all__ = ["app"]
