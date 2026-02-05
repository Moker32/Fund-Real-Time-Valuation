"""
配置管理模块

提供基金实时估值 TUI 应用的配置管理功能：
- YAML 配置文件的加载和保存
- 基金和持仓的添加/删除/修改
- 商品的添加/删除/修改
- 读取应用主配置（刷新频率、主题等）

Usage:
    from src.config import ConfigManager

    # 初始化配置管理器
    manager = ConfigManager()

    # 加载配置
    app_config = manager.load_app_config()
    funds = manager.load_funds()
    commodities = manager.load_commodities()

    # 添加基金
    from src.config.models import Fund
    manager.add_watchlist(Fund(code="161725", name="招商中证白酒指数(LOF)A"))

    # 添加商品
    from src.config.models import Commodity
    manager.add_commodity(Commodity(symbol="XAUUSD", name="国际金价", source="alpha_vantage"))
"""

from .base import AppConfigLoader, BaseConfigLoader
from .manager import (
    CommodityConfigLoader,
    ConfigManager,
    FundConfigLoader,
)
from .models import (
    AppConfig,
    Commodity,
    CommodityList,
    DataSource,
    Fund,
    FundList,
    Holding,
    Theme,
)

__all__ = [
    # 模型
    'Fund',
    'Holding',
    'Commodity',
    'FundList',
    'CommodityList',
    'AppConfig',
    'Theme',
    'DataSource',
    # 配置加载器
    'BaseConfigLoader',
    'AppConfigLoader',
    'FundConfigLoader',
    'CommodityConfigLoader',
    # 配置管理器
    'ConfigManager',
]
