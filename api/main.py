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
from fastapi.responses import JSONResponse

from src.datasources.cache_cleaner import CacheCleaner, get_cache_cleaner
from src.datasources.cache_warmer import CacheWarmer
from src.datasources.manager import create_default_manager

logger = logging.getLogger(__name__)

from .dependencies import (
    close_data_source_manager,
    get_data_source_manager,
    set_data_source_manager,
)
from .models import DataSourceHealthItem, HealthDetailResponse, HealthResponse
from .routes import cache, commodities, funds, indices, overview, sectors

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
    global _cache_warmer, _cache_cleaner

    # 启动时初始化数据源管理器
    manager = create_default_manager()
    set_data_source_manager(manager)

    # 创建缓存预热器（用于后续操作）
    _cache_warmer = CacheWarmer(manager)

    # 立即预加载所有缓存数据到内存（不阻塞，快速同步读取）
    # 这样前端首次请求就能拿到缓存数据，而不必等待数据刷新
    await _cache_warmer.preload_all_cache(timeout=10)

    # 预热基金信息缓存（名称、类型等）- 并行获取，不阻塞服务启动
    asyncio.create_task(_cache_warmer.preload_fund_info_cache(timeout=60))

    # 启动后台健康检查（会立即执行一次检查）
    await manager.start_background_health_check()

    # 等待一段时间让健康检查完成初始化
    await asyncio.sleep(2)

    # 启动缓存预热（不阻塞服务启动）
    asyncio.create_task(_cache_warmer.start_background_warmup(interval=300))

    # 启动时清理过期缓存（不阻塞服务启动）
    try:
        from src.datasources.cache_cleaner import startup_cleanup

        startup_task = asyncio.create_task(startup_cleanup())
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
- **健康检查**: 服务状态监控

### 数据源

- **基金**: 天天基金、新浪财经
- **商品**: yfinance、AKShare
    """,
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
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
        }
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
        }
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
        }
    )


# ==================== 路由注册 ====================

# 注册路由
app.include_router(funds.router)
app.include_router(commodities.router)
app.include_router(indices.router)
app.include_router(sectors.router)
app.include_router(overview.router)
app.include_router(cache.router)


@app.get(
    "/",
    summary="API 根路径",
    description="返回 API 基本信息",
)
async def root():
    """
    API 根路径

    Returns:
        dict: API 基本信息
    """
    return {
        "name": "基金实时估值 API",
        "version": "0.1.0",
        "description": "基金实时估值 Web API 服务",
        "docs": "/docs",
        "health": "/api/health",
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
        data_sources.append(DataSourceHealthItem(
            source=source_name,
            status=result.get("status", "unknown"),
            response_time_ms=result.get("response_time_ms"),
        ))

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


# 导出应用实例
__all__ = ["app"]
