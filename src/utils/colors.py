# -*- coding: UTF-8 -*-
"""颜色和格式化工具函数

从原 src/gui/theme.py 迁移，提供涨跌颜色和格式化功能。
"""

# ============== 涨跌颜色配置 ==============
# A股习惯：红涨绿跌 (与西方绿涨红跌相反)
class ChangeColors:
    """涨跌颜色配置"""

    POSITIVE = "#FF3B30"  # 上涨/盈利 (红色)
    NEGATIVE = "#34C759"  # 下跌/亏损 (绿色)
    NEUTRAL = "#8E8E93"   # 持平/无变化 (灰色)


def get_change_color(value: float) -> str:
    """根据数值返回涨跌颜色"""
    if value > 0:
        return ChangeColors.POSITIVE
    elif value < 0:
        return ChangeColors.NEGATIVE
    return ChangeColors.NEUTRAL


def format_change_text(value: float, suffix: str = "%") -> str:
    """格式化涨跌幅文本"""
    sign = "+" if value >= 0 else ""
    return f"{sign}{value:.2f}{suffix}"


def format_profit_text(value: float, prefix: str = "¥") -> str:
    """格式化盈亏文本"""
    sign = "+" if value >= 0 else ""
    return f"{sign}{prefix}{value:.2f}"


def format_number(value: float, decimals: int = 2) -> str:
    """格式化数字"""
    if abs(value) >= 10000:
        return f"{value / 10000:.2f}万"
    elif abs(value) >= 1000:
        return f"{value:,.{decimals}f}"
    return f"{value:,.{decimals}f}"


def format_currency(value: float, prefix: str = "¥") -> str:
    """格式化货币"""
    return f"{prefix}{value:,.2f}"
