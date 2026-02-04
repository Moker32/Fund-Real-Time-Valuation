# -*- coding: UTF-8 -*-
"""数据库模块初始化

提供 SQLite 数据库支持，包括：
- 基金配置存储（自选、持仓）
- 商品配置存储
- 基金净值历史数据
- 新闻缓存

使用示例：
    from src.db.database import DatabaseManager

    db = DatabaseManager()
    db.add_fund_to_watchlist("161039", "富国中证新能源汽车指数")
    holdings = db.get_holdings()
"""

from .database import DatabaseManager, FundHistoryDAO, ConfigDAO

__all__ = ["DatabaseManager", "FundHistoryDAO", "ConfigDAO"]
