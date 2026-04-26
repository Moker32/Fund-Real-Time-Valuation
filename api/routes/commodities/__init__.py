"""
商品 API 路由模块

提供商品相关的 REST API 端点：
- commodities_data: 商品数据 (行情、分类、历史、详情)

向后兼容导出:
    from api.routes.commodities import router  # 导出组合后的路由
"""

from fastapi import APIRouter

# 导入所有子模块路由
from . import commodities_data

# 创建组合路由（不含 prefix，由子路由提供）
router = APIRouter()

# 添加所有子路由（每个子路由自带 /api/commodities prefix）
router.include_router(commodities_data.router)

__all__ = ["router", "commodities_data"]
