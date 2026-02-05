# -*- coding: UTF-8 -*-
"""设置对话框模块

提供应用配置界面
"""

import flet as ft
from flet import (
    AlertDialog,
    Column,
    Row,
    Container,
    Text,
    Icon,
    Icons,
    TextField,
    Switch,
    Dropdown,
    dropdown,
    ElevatedButton,
    TextButton,
    Divider,
    Slider,
)
from typing import Callable, TYPE_CHECKING

from src.config.models import AppConfig, Theme
from .components import AppColors

if TYPE_CHECKING:
    from .main import FundGUIApp


class SettingsDialog(AlertDialog):
    """设置对话框"""

    def __init__(
        self,
        app: "FundGUIApp",
        app_config: AppConfig,
        on_save: Callable[[AppConfig], None],
    ):
        super().__init__()
        self.app = app
        self.app_config = app_config
        self.on_save = on_save

        self.modal = True
        self.title = Row(
            [
                Icon(Icons.SETTINGS, color=AppColors.ACCENT_BLUE),
                Text("设置", weight=ft.FontWeight.BOLD, size=18),
            ],
            spacing=10,
        )

        # 刷新间隔
        self.refresh_interval = TextField(
            label="刷新间隔(秒)",
            value=str(app_config.refresh_interval),
            width=150,
            keyboard_type=ft.KeyboardType.NUMBER,
            hint_text="10-300",
        )

        # 主题选择
        self.theme_dropdown = Dropdown(
            label="主题",
            width=150,
            options=[
                dropdown.Option(Theme.DARK.value, "深色模式"),
                dropdown.Option(Theme.LIGHT.value, "浅色模式"),
            ],
            value=app_config.theme,
        )

        # 自动刷新开关
        self.auto_refresh_switch = Switch(
            label="自动刷新",
            value=app_config.enable_auto_refresh,
            active_color=AppColors.ACCENT_BLUE,
        )

        # 显示盈亏开关
        self.show_profit_switch = Switch(
            label="显示盈亏",
            value=app_config.show_profit_loss,
            active_color=AppColors.ACCENT_BLUE,
        )

        # 历史数据点数
        self.history_points = TextField(
            label="历史数据点数",
            value=str(app_config.max_history_points),
            width=150,
            keyboard_type=ft.KeyboardType.NUMBER,
            hint_text="50-500",
        )

        self.content = Container(
            content=Column(
                [
                    Text("数据设置", size=14, weight=ft.FontWeight.BOLD, color=AppColors.TEXT_SECONDARY),
                    Divider(height=1, color=AppColors.DIVIDER),
                    Row([self.refresh_interval, self.history_points], spacing=20),
                    self.auto_refresh_switch,
                    Container(height=10),
                    Text("显示设置", size=14, weight=ft.FontWeight.BOLD, color=AppColors.TEXT_SECONDARY),
                    Divider(height=1, color=AppColors.DIVIDER),
                    Row([self.theme_dropdown], spacing=20),
                    self.show_profit_switch,
                ],
                spacing=12,
            ),
            width=380,
            padding=10,
        )

        self.actions = [
            TextButton("恢复默认", on_click=self._reset_defaults),
            TextButton("取消", on_click=self._cancel),
            ElevatedButton("保存", on_click=self._save),
        ]

    def _reset_defaults(self, e):
        """恢复默认设置"""
        default_config = AppConfig()
        self.refresh_interval.value = str(default_config.refresh_interval)
        self.theme_dropdown.value = default_config.theme
        self.auto_refresh_switch.value = default_config.enable_auto_refresh
        self.show_profit_switch.value = default_config.show_profit_loss
        self.history_points.value = str(default_config.max_history_points)
        self.update()
        self.app._show_snackbar("已恢复默认设置")

    def _cancel(self, e):
        """取消"""
        self.open = False
        self.app.page.update()

    def _save(self, e):
        """保存设置"""
        # 验证刷新间隔
        try:
            refresh_interval = int(self.refresh_interval.value)
            if not 10 <= refresh_interval <= 300:
                self.app._show_snackbar("刷新间隔应在 10-300 秒之间")
                return
        except ValueError:
            self.app._show_snackbar("请输入有效的刷新间隔")
            return

        # 验证历史数据点数
        try:
            history_points = int(self.history_points.value)
            if not 50 <= history_points <= 500:
                self.app._show_snackbar("历史数据点数应在 50-500 之间")
                return
        except ValueError:
            self.app._show_snackbar("请输入有效的历史数据点数")
            return

        # 构建新配置
        new_config = AppConfig(
            refresh_interval=refresh_interval,
            theme=self.theme_dropdown.value,
            default_fund_source=self.app_config.default_fund_source,
            max_history_points=history_points,
            enable_auto_refresh=self.auto_refresh_switch.value,
            show_profit_loss=self.show_profit_switch.value,
        )

        # 保存配置
        self.on_save(new_config)

        self.open = False
        self.app.page.update()
        self.app._show_snackbar("设置已保存")
