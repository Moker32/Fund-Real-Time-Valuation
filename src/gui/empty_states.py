# -*- coding: UTF-8 -*-
"""空状态组件模块

提供基金、商品、新闻等列表为空时显示的友好提示组件。
"""

from collections.abc import Callable, Any

import flet as ft
from flet import (
    Column,
    Container,
    Control,
    ElevatedButton,
    Icon,
    Icons,
    Text,
    IconData,
)

from .components import AppColors


# 预设空状态配置
EMPTY_STATES_CONFIG: dict[str, dict[str, Any]] = {
    "funds": {
        "icon": Icons.STAR_BORDER,
        "message": "暂无自选基金",
        "hint": "点击下方 + 按钮添加您关注的基金",
        "button_text": "添加基金",
        "button_icon": Icons.ADD,
    },
    "commodities": {
        "icon": Icons.TRENDING_UP,
        "message": "暂无商品数据",
        "hint": "在设置中添加您关注的商品品种",
        "button_text": "刷新",
        "button_icon": Icons.REFRESH,
    },
    "news": {
        "icon": Icons.NEWSPAPER,
        "message": "暂无新闻",
        "hint": "点击刷新获取最新财经新闻",
        "button_text": "刷新新闻",
        "button_icon": Icons.REFRESH,
    },
}


def empty_funds_state(
    message: str | None = None,
    hint: str | None = None,
    on_add: Callable[[Any], None] | None = None,
) -> Container:
    """创建空基金状态组件

    Args:
        message: 主提示文本 (默认为预设值)
        hint: 辅助说明文本 (默认为预设值)
        on_add: 添加按钮点击回调

    Returns:
        Container: 空状态容器组件
    """
    config = EMPTY_STATES_CONFIG["funds"]
    return create_empty_state(
        icon_name=config["icon"],
        message=config["message"] if message is None else message,
        hint=config["hint"] if hint is None else hint,
        button_text=config["button_text"],
        button_icon=config["button_icon"],
        on_button_click=on_add,
    )


def empty_commodities_state(
    message: str | None = None,
    hint: str | None = None,
    on_refresh: Callable[[Any], None] | None = None,
) -> Container:
    """创建空商品状态组件

    Args:
        message: 主提示文本 (默认为预设值)
        hint: 辅助说明文本 (默认为预设值)
        on_refresh: 刷新按钮点击回调

    Returns:
        Container: 空状态容器组件
    """
    config = EMPTY_STATES_CONFIG["commodities"]
    return create_empty_state(
        icon_name=config["icon"],
        message=config["message"] if message is None else message,
        hint=config["hint"] if hint is None else hint,
        button_text=config["button_text"],
        button_icon=config["button_icon"],
        on_button_click=on_refresh,
    )


def empty_news_state(
    message: str | None = None,
    hint: str | None = None,
    on_refresh: Callable[[Any], None] | None = None,
) -> Container:
    """创建空新闻状态组件

    Args:
        message: 主提示文本 (默认为预设值)
        hint: 辅助说明文本 (默认为预设值)
        on_refresh: 刷新按钮点击回调

    Returns:
        Container: 空状态容器组件
    """
    config = EMPTY_STATES_CONFIG["news"]
    return create_empty_state(
        icon_name=config["icon"],
        message=config["message"] if message is None else message,
        hint=config["hint"] if hint is None else hint,
        button_text=config["button_text"],
        button_icon=config["button_icon"],
        on_button_click=on_refresh,
    )


def create_empty_state(
    icon_name: Icons,
    message: str,
    hint: str = "",
    button_text: str = "",
    button_icon: Icons | None = None,
    on_button_click: Callable[[Any], None] | None = None,
) -> Container:
    """创建通用空状态组件

    Args:
        icon_name: 图标名称 (Icons.XXX)
        message: 主提示文本
        hint: 辅助说明文本
        button_text: 按钮文本
        button_icon: 按钮图标
        on_button_click: 按钮点击回调

    Returns:
        Container: 空状态容器组件
    """
    # 主图标
    icon = Icon(
        icon=icon_name,  # type: ignore
        size=64,
        color=AppColors.TEXT_SECONDARY,
    )

    # 主提示文本
    main_text = Text(
        message,
        size=18,
        color=AppColors.TEXT_PRIMARY,
        weight=ft.FontWeight.W_500,
    )

    # 辅助说明
    hint_text: Text | None = None
    if hint:
        hint_text = Text(
            hint,
            size=14,
            color=AppColors.TEXT_SECONDARY,
        )

    # 按钮
    button: ElevatedButton | None = None
    if button_text and on_button_click:
        button = ElevatedButton(
            button_text,
            icon=button_icon,  # type: ignore
            on_click=on_button_click,
        )

    # 构建内容列
    content_controls: list[Control] = [icon, Container(height=16), main_text]
    if hint_text:
        content_controls.append(Container(height=8))
        content_controls.append(hint_text)
    if button:
        content_controls.append(Container(height=24))
        content_controls.append(button)

    content = Column(
        controls=content_controls,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=0,
    )

    # 返回容器
    return Container(
        content=content,
        padding=ft.padding.symmetric(horizontal=32, vertical=32),
        alignment=ft.Alignment(0.5, 0.5),
    )
