"""
商品 API 路由 - 向后兼容垫片

此文件是 api/routes/commodities/ 子包的向后兼容垫片。
新代码请直接从子包导入：
    from api.routes.commodities import router

旧导入路径（此文件）仍然可用：
    from api.routes.commodities import router
"""

# 重新导出所有内容，保持旧导入路径兼容
from api.routes.commodities import (
    commodities_data,
    commodities_watchlist,
    router,
)

__all__ = [
    "router",
    "commodities_data",
    "commodities_watchlist",
]
