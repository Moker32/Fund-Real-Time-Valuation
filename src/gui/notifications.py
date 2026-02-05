# -*- coding: UTF-8 -*-
"""通知管理模块

管理价格预警和通知功能
"""

from collections.abc import Callable
from datetime import datetime
from typing import TYPE_CHECKING

import flet as ft
from flet import (
    AlertDialog,
    Column,
    Container,
    Divider,
    Dropdown,
    ElevatedButton,
    Icon,
    IconButton,
    Icons,
    ListTile,
    ListView,
    Row,
    Text,
    TextButton,
    TextField,
    dropdown,
)

from src.config.models import AlertDirection, NotificationConfig, PriceAlert

from .components import AppColors

if TYPE_CHECKING:
    from .main import FundGUIApp


class NotificationManager:
    """通知管理器"""

    def __init__(self, config: NotificationConfig):
        self.config = config

    def check_price_alerts(self, fund_code: str, fund_name: str, current_price: float) -> list[PriceAlert]:
        """检查价格预警，返回触发的预警列表"""
        triggered = []
        for alert in self.config.price_alerts:
            if alert.fund_code == fund_code and not alert.triggered:
                if alert.check(current_price):
                    alert.triggered = True
                    triggered.append(alert)
        return triggered

    def add_alert(self, fund_code: str, fund_name: str, target_price: float, direction: str) -> PriceAlert:
        """添加新预警"""
        alert = PriceAlert(
            fund_code=fund_code,
            fund_name=fund_name,
            target_price=target_price,
            direction=direction,
            triggered=False,
            created_at=datetime.now(),
        )
        self.config.add_alert(alert)
        return alert

    def remove_alert(self, fund_code: str, target_price: float) -> bool:
        """移除预警"""
        return self.config.remove_alert(fund_code, target_price)

    def get_all_alerts(self) -> list[PriceAlert]:
        """获取所有预警"""
        return self.config.price_alerts

    def get_active_alerts(self) -> list[PriceAlert]:
        """获取未触发的预警"""
        return [a for a in self.config.price_alerts if not a.triggered]


class NotificationDialog(AlertDialog):
    """通知中心对话框"""

    def __init__(self, app: "FundGUIApp", notification_manager: NotificationManager):
        super().__init__()
        self.app = app
        self.notification_manager = notification_manager

        self.modal = True
        self.title = Row(
            [
                Icon(Icons.NOTIFICATIONS, color=AppColors.ACCENT_BLUE),
                Text("通知中心", weight=ft.FontWeight.BOLD, size=18),
            ],
            spacing=10,
        )

        # 预警列表
        self.alerts_list = ListView(
            spacing=8,
            height=300,
            width=400,
        )
        self._refresh_alerts_list()

        self.content = Container(
            content=Column(
                [
                    Text("价格预警", size=14, color=AppColors.TEXT_SECONDARY),
                    Divider(height=1, color=AppColors.DIVIDER),
                    self.alerts_list if self.notification_manager.get_all_alerts() else
                    Container(
                        content=Column(
                            [
                                Icon(Icons.NOTIFICATIONS_OFF, size=48, color=AppColors.TEXT_SECONDARY),
                                Text("暂无预警", color=AppColors.TEXT_SECONDARY),
                                Text("在基金详情中设置价格预警", size=12, color=AppColors.TEXT_SECONDARY),
                            ],
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            spacing=8,
                        ),
                        padding=30,
                        alignment=ft.alignment.center,
                    ),
                ],
                spacing=12,
            ),
            width=420,
            padding=10,
        )

        self.actions = [
            TextButton("清除已触发", on_click=self._clear_triggered),
            ElevatedButton("关闭", on_click=self._close),
        ]

    def _refresh_alerts_list(self):
        """刷新预警列表"""
        self.alerts_list.controls.clear()
        alerts = self.notification_manager.get_all_alerts()

        for alert in alerts:
            direction_text = "高于" if alert.direction == AlertDirection.ABOVE.value else "低于"
            status_color = AppColors.TEXT_SECONDARY if alert.triggered else AppColors.ACCENT_BLUE

            tile = ListTile(
                leading=Icon(
                    Icons.ALARM if not alert.triggered else Icons.ALARM_OFF,
                    color=status_color,
                ),
                title=Text(
                    f"{alert.fund_name} ({alert.fund_code})",
                    size=14,
                    color=AppColors.TEXT_PRIMARY,
                ),
                subtitle=Text(
                    f"{direction_text} {alert.target_price:.4f}" +
                    (" (已触发)" if alert.triggered else ""),
                    size=12,
                    color=status_color,
                ),
                trailing=IconButton(
                    icon=Icons.DELETE_OUTLINE,
                    icon_color=AppColors.UP_RED,
                    tooltip="删除",
                    on_click=lambda e, a=alert: self._delete_alert(a),
                ),
            )
            self.alerts_list.controls.append(tile)

    def _delete_alert(self, alert: PriceAlert):
        """删除预警"""
        self.notification_manager.remove_alert(alert.fund_code, alert.target_price)
        self._refresh_alerts_list()
        self.update()
        self.app._show_snackbar(f"已删除 {alert.fund_name} 的预警")

    def _clear_triggered(self, e):
        """清除已触发的预警"""
        count = self.notification_manager.config.clear_triggered()
        self._refresh_alerts_list()
        self.update()
        self.app._show_snackbar(f"已清除 {count} 条已触发的预警")

    def _close(self, e):
        """关闭对话框"""
        self.open = False
        self.app.page.update()


class AddAlertDialog(AlertDialog):
    """添加预警对话框"""

    def __init__(
        self,
        app: "FundGUIApp",
        notification_manager: NotificationManager,
        fund_code: str,
        fund_name: str,
        current_price: float,
        on_save: Callable | None = None,
    ):
        super().__init__()
        self.app = app
        self.notification_manager = notification_manager
        self.fund_code = fund_code
        self.fund_name = fund_name
        self.current_price = current_price
        self.on_save = on_save

        self.modal = True
        self.title = Row(
            [
                Icon(Icons.ADD_ALERT, color=AppColors.ACCENT_ORANGE),
                Text("添加价格预警", weight=ft.FontWeight.BOLD),
            ],
            spacing=10,
        )

        # 目标价格输入
        self.price_field = TextField(
            label="目标价格",
            value=f"{current_price:.4f}",
            width=200,
            keyboard_type=ft.KeyboardType.NUMBER,
        )

        # 方向选择
        self.direction_dropdown = Dropdown(
            label="预警条件",
            width=200,
            options=[
                dropdown.Option(AlertDirection.ABOVE.value, "高于目标价"),
                dropdown.Option(AlertDirection.BELOW.value, "低于目标价"),
            ],
            value=AlertDirection.ABOVE.value,
        )

        self.content = Container(
            content=Column(
                [
                    Text(f"基金: {fund_name}", size=12, color=AppColors.TEXT_SECONDARY),
                    Text(f"代码: {fund_code}", size=12, color=AppColors.TEXT_SECONDARY),
                    Text(f"当前价格: {current_price:.4f}", size=12, color=AppColors.ACCENT_BLUE),
                    Divider(height=1, color=AppColors.DIVIDER),
                    self.price_field,
                    self.direction_dropdown,
                ],
                spacing=12,
            ),
            width=300,
            padding=10,
        )

        self.actions = [
            TextButton("取消", on_click=self._cancel),
            ElevatedButton("添加", on_click=self._save),
        ]

    def _cancel(self, e):
        """取消"""
        self.open = False
        self.app.page.update()

    def _save(self, e):
        """保存预警"""
        try:
            target_price = float(self.price_field.value)
        except ValueError:
            self.app._show_snackbar("请输入有效的价格")
            return

        direction = self.direction_dropdown.value

        # 检查是否已存在相同预警
        existing = self.notification_manager.config.get_alerts_for_fund(self.fund_code)
        for alert in existing:
            if alert.target_price == target_price and alert.direction == direction:
                self.app._show_snackbar("该预警已存在")
                return

        # 添加预警
        self.notification_manager.add_alert(
            self.fund_code,
            self.fund_name,
            target_price,
            direction,
        )

        direction_text = "高于" if direction == AlertDirection.ABOVE.value else "低于"
        self.app._show_snackbar(f"已添加预警: {direction_text} {target_price:.4f}")

        if self.on_save:
            self.on_save()

        self.open = False
        self.app.page.update()
