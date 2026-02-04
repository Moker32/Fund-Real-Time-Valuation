# -*- coding: UTF-8 -*-
"""GUI 主题配置

统一颜色常量管理，支持涨跌颜色配置、主题切换等功能。
"""

import flet as ft
from dataclasses import dataclass
from typing import Optional


# ============== 涨跌颜色配置 ==============
# A股习惯：红涨绿跌 (与西方绿涨红跌相反)
class ChangeColors:
    """涨跌颜色配置"""

    POSITIVE = ft.Colors.RED  # 上涨/盈利
    NEGATIVE = ft.Colors.GREEN  # 下跌/亏损
    NEUTRAL = ft.Colors.GREY_500  # 持平/无变化


# ============== 辅助函数 ==============
def get_change_color(value: float) -> str:
    """根据数值返回涨跌颜色"""
    if value > 0:
        return ChangeColors.POSITIVE
    elif value < 0:
        return ChangeColors.NEGATIVE
    else:
        return ChangeColors.NEUTRAL


def format_change_text(value: float, suffix: str = "%") -> str:
    """格式化涨跌幅文本"""
    sign = "+" if value >= 0 else ""
    return f"{sign}{value:.2f}{suffix}"


def format_profit_text(value: float, prefix: str = "¥") -> str:
    """格式化盈亏文本"""
    sign = "+" if value >= 0 else ""
    return f"{sign}{prefix}{value:.2f}"


# ============== 主题切换管理 ==============
class ThemeManager:
    """主题管理器"""

    _instance: Optional["ThemeManager"] = None
    _is_dark: bool = True

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @property
    def is_dark(self) -> bool:
        return self._is_dark

    def toggle_theme(self) -> ft.ThemeMode:
        """切换主题，返回新的主题模式"""
        self._is_dark = not self._is_dark
        return ft.ThemeMode.DARK if self._is_dark else ft.ThemeMode.LIGHT

    def get_theme_mode(self) -> ft.ThemeMode:
        """获取当前主题模式"""
        return ft.ThemeMode.DARK if self._is_dark else ft.ThemeMode.LIGHT

    def get_theme(self) -> ft.Theme:
        """获取当前主题配置"""
        return self.create_finance_theme(self._is_dark)

    @staticmethod
    def create_finance_theme(is_dark: bool = True) -> ft.Theme:
        """创建金融应用主题"""
        if is_dark:
            return ft.Theme(
                color_scheme=ft.ColorScheme(
                    primary=ft.Colors.BLUE_900,
                    on_primary=ft.Colors.WHITE,
                    primary_container=ft.Colors.BLUE_700,
                    on_primary_container=ft.Colors.WHITE,
                    secondary=ft.Colors.TEAL_400,
                    on_secondary=ft.Colors.BLACK,
                    background=ft.Colors.SURFACE,
                    on_background=ft.Colors.WHITE,
                    surface=ft.Colors.SURFACE,
                    on_surface=ft.Colors.WHITE,
                    surface_variant=ft.Colors.GREY_800,
                    on_surface_variant=ft.Colors.WHITE70,
                    error=ft.Colors.RED,
                    on_error=ft.Colors.WHITE,
                ),
                use_material3=True,
            )
        else:
            return ft.Theme(
                color_scheme=ft.ColorScheme(
                    primary=ft.Colors.BLUE_900,
                    on_primary=ft.Colors.WHITE,
                    primary_container=ft.Colors.BLUE_100,
                    on_primary_container=ft.Colors.BLUE_900,
                    secondary=ft.Colors.TEAL_600,
                    on_secondary=ft.Colors.WHITE,
                    background=ft.Colors.GREY_50,
                    on_background=ft.Colors.GREY_900,
                    surface=ft.Colors.WHITE,
                    on_surface=ft.Colors.GREY_900,
                    surface_variant=ft.Colors.GREY_100,
                    on_surface_variant=ft.Colors.GREY_700,
                    error=ft.Colors.RED_600,
                    on_error=ft.Colors.WHITE,
                ),
                use_material3=True,
            )


# 全局主题管理器实例
theme_manager = ThemeManager()
