# -*- coding: UTF-8 -*-
"""Pytest configuration for TUI tests

提供测试 fixtures:
- app_config: 应用配置实例
- sample_funds: 测试基金列表
- sample_holdings: 测试持仓列表
- notification_config: 通知配置实例
"""

import sys
import os
from pathlib import Path
from datetime import datetime

# 添加项目根目录到 Python 路径
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# 添加 src 目录到 Python 路径
SRC_ROOT = os.path.join(PROJECT_ROOT, 'src')
if SRC_ROOT not in sys.path:
    sys.path.insert(0, SRC_ROOT)

# 确保 src 目录下的模块可以相互导入
# config 模块在 src/config 目录下
CONFIG_ROOT = os.path.join(SRC_ROOT, 'config')
if CONFIG_ROOT not in sys.path:
    sys.path.insert(0, CONFIG_ROOT)


import pytest

from src.config.models import (
    Fund,
    Holding,
    AppConfig,
    FundList,
    Commodity,
    CommodityList,
    NotificationConfig,
    PriceAlert,
    AlertDirection,
)


@pytest.fixture
def app_config():
    """返回 AppConfig 实例"""
    return AppConfig(
        refresh_interval=30,
        theme="dark",
        default_fund_source="sina",
        max_history_points=100,
        enable_auto_refresh=True,
        show_profit_loss=True,
    )


@pytest.fixture
def sample_funds():
    """返回测试基金列表"""
    return [
        Fund(code="000001", name="华夏成长混合"),
        Fund(code="000002", name="华夏回报混合"),
        Fund(code="110011", name="华夏大盘精选"),
        Fund(code="161039", name="富国中证新能源汽车指数"),
        Fund(code="161725", name="招商中证白酒指数"),
    ]


@pytest.fixture
def sample_holdings():
    """返回测试持仓列表"""
    return [
        Holding(code="000001", name="华夏成长混合", shares=1000.0, cost=1.5),
        Holding(code="000002", name="华夏回报混合", shares=500.0, cost=2.0),
        Holding(code="110011", name="华夏大盘精选", shares=2000.0, cost=1.2),
    ]


@pytest.fixture
def notification_config():
    """返回 NotificationConfig 实例"""
    return NotificationConfig(
        enabled=True,
        price_alerts=[
            PriceAlert(
                fund_code="000001",
                fund_name="华夏成长混合",
                target_price=1.6,
                direction=AlertDirection.ABOVE.value,
                triggered=False,
                created_at=datetime.now(),
            ),
            PriceAlert(
                fund_code="000002",
                fund_name="华夏回报混合",
                target_price=1.8,
                direction=AlertDirection.BELOW.value,
                triggered=False,
                created_at=datetime.now(),
            ),
        ],
        daily_summary=False,
        alert_sound=False,
    )


@pytest.fixture
def fund_list(sample_funds, sample_holdings):
    """返回 FundList 实例"""
    return FundList(
        watchlist=sample_funds,
        holdings=sample_holdings,
    )


@pytest.fixture
def sample_commodities():
    """返回测试商品列表"""
    return [
        Commodity(symbol="AU9999", name="黄金", source="akshare"),
        Commodity(symbol="AG9999", name="白银", source="akshare"),
        Commodity(symbol="CU", name="铜", source="alpha_vantage"),
    ]


@pytest.fixture
def temp_dir(tmp_path):
    """返回临时目录路径"""
    return tmp_path
