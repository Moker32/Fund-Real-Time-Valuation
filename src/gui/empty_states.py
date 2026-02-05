# -*- coding: UTF-8 -*-
"""空状态组件模块

提供基金、商品、新闻等列表为空时显示的友好提示组件。
"""

import flet as ft
from flet import (
    Container,
    Column,
    Row,
    Text,
    Icon,
    Icons,
    ElevatedButton,
    Card,
    BorderRadius,
)
from .components import AppColors


def empty_funds_state(
    message: str = "暂无自选基金",
    hint: str = "点击下方 + 按钮添加您关注的基金",
    on_add: callable = None,
) -> Container:
    """创建空基金状态组件

    Args:
        message: 主提示文本
        hint: 辅助说明文本
        on_add: 添加按钮点击回调

    Returns:
        Container: 空状态容器组件
    """
    # 主图标
    icon = Icon(
        Icons.STAR_BORDER,
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
    hint_text = Text(
        hint,
        size=14,
        color=AppColors.TEXT_SECONDARY,
    )

    # 添加按钮
    add_button = None
    if on_add:
        add_button = ElevatedButton(
            "添加基金",
            icon=Icons.ADD,
            on_click=on_add,
        )

    # 构建内容列
    content_controls = [icon, Container(height=16), main_text]
    if hint:
        content_controls.append(Container(height=8))
        content_controls.append(hint_text)
    if add_button:
        content_controls.append(Container(height=24))
        content_controls.append(add_button)

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


def empty_commodities_state(
    message: str = "暂无商品数据",
    hint: str = "在设置中添加您关注的商品品种",
    on_refresh: callable = None,
) -> Container:
    """创建空商品状态组件

    Args:
        message: 主提示文本
        hint: 辅助说明文本
        on_refresh: 刷新按钮点击回调

    Returns:
        Container: 空状态容器组件
    """
    # 主图标
    icon = Icon(
        Icons.TRENDING_UP,
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
    hint_text = Text(
        hint,
        size=14,
        color=AppColors.TEXT_SECONDARY,
    )

    # 刷新按钮
    refresh_button = None
    if on_refresh:
        refresh_button = ElevatedButton(
            "刷新",
            icon=Icons.REFRESH,
            on_click=on_refresh,
        )

    # 构建内容列
    content_controls = [icon, Container(height=16), main_text]
    if hint:
        content_controls.append(Container(height=8))
        content_controls.append(hint_text)
    if refresh_button:
        content_controls.append(Container(height=24))
        content_controls.append(refresh_button)

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


def empty_news_state(
    message: str = "暂无新闻",
    hint: str = "点击刷新获取最新财经新闻",
    on_refresh: callable = None,
) -> Container:
    """创建空新闻状态组件

    Args:
        message: 主提示文本
        hint: 辅助说明文本
        on_refresh: 刷新按钮点击回调

    Returns:
        Container: 空状态容器组件
    """
    # 主图标
    icon = Icon(
        Icons.NEWSPAPER,
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
    hint_text = Text(
        hint,
        size=14,
        color=AppColors.TEXT_SECONDARY,
    )

    # 刷新按钮
    refresh_button = None
    if on_refresh:
        refresh_button = ElevatedButton(
            "刷新新闻",
            icon=Icons.REFRESH,
            on_click=on_refresh,
        )

    # 构建内容列
    content_controls = [icon, Container(height=16), main_text]
    if hint:
        content_controls.append(Container(height=8))
        content_controls.append(hint_text)
    if refresh_button:
        content_controls.append(Container(height=24))
        content_controls.append(refresh_button)

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


def create_empty_state(
    icon_name: str,
    message: str,
    hint: str = "",
    button_text: str = "",
    button_icon: str = "",
    on_button_click: callable = None,
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
        icon_name,
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
    hint_text = None
    if hint:
        hint_text = Text(
            hint,
            size=14,
            color=AppColors.TEXT_SECONDARY,
        )

    # 按钮
    button = None
    if button_text and on_button_click:
        button = ElevatedButton(
            button_text,
            icon=button_icon if button_icon else None,
            on_click=on_button_click,
        )

    # 构建内容列
    content_controls = [icon, Container(height=16), main_text]
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
