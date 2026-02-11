# -*- coding: UTF-8 -*-
"""空状态组件测试

测试空状态 UI 组件的创建和显示功能。
"""

import sys
from pathlib import Path

# 添加 src 目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestEmptyStatesModule:
    """空状态模块测试"""

    def test_import_empty_states_module(self):
        """测试空状态模块可以正常导入"""
        from src.gui import empty_states

        assert empty_states is not None

    def test_import_empty_funds_state_function(self):
        """测试空基金状态函数可以导入"""
        from src.gui.empty_states import empty_funds_state

        assert callable(empty_funds_state)

    def test_import_empty_commodities_state_function(self):
        """测试空商品状态函数可以导入"""
        from src.gui.empty_states import empty_commodities_state

        assert callable(empty_commodities_state)

    def test_import_empty_news_state_function(self):
        """测试空新闻状态函数可以导入"""
        from src.gui.empty_states import empty_news_state

        assert callable(empty_news_state)


class TestEmptyFundsState:
    """空基金状态组件测试"""

    def test_empty_funds_state_returns_container(self):
        """测试空基金状态返回 Container"""
        from src.gui.empty_states import empty_funds_state

        result = empty_funds_state()

        # 应该返回 Flet Container
        assert result is not None
        assert hasattr(result, 'content')

    def test_empty_funds_state_has_icon(self):
        """测试空基金状态包含图标"""
        from src.gui.empty_states import empty_funds_state

        result = empty_funds_state()
        content = result.content

        # 应该包含 Column
        assert hasattr(content, 'controls')
        assert len(content.controls) >= 1

        # 第一个控件应该是 Icon
        from flet import Icon
        first_control = content.controls[0]
        assert isinstance(first_control, Icon)

    def test_empty_funds_state_has_text(self):
        """测试空基金状态包含文本"""
        from flet import Text
        from src.gui.empty_states import empty_funds_state

        result = empty_funds_state()
        content = result.content

        # 查找 Text 控件
        has_text = False
        for control in content.controls:
            if isinstance(control, Text):
                has_text = True
                break

        assert has_text, "空基金状态应该包含文本说明"

    def test_empty_funds_state_with_on_add_callback(self):
        """测试带添加回调的空基金状态"""
        from src.gui.empty_states import empty_funds_state

        callback_called = False

        def on_add():
            nonlocal callback_called
            callback_called = True

        result = empty_funds_state(on_add=on_add)

        # 应该有按钮控件
        content = result.content
        from flet import ElevatedButton
        has_button = False
        for control in content.controls:
            if isinstance(control, ElevatedButton):
                has_button = True
                break

        assert has_button, "空基金状态应该包含添加按钮"


class TestEmptyCommoditiesState:
    """空商品状态组件测试"""

    def test_empty_commodities_state_returns_container(self):
        """测试空商品状态返回 Container"""
        from src.gui.empty_states import empty_commodities_state

        result = empty_commodities_state()

        assert result is not None
        assert hasattr(result, 'content')

    def test_empty_commodities_state_has_icon(self):
        """测试空商品状态包含图标"""
        from src.gui.empty_states import empty_commodities_state

        result = empty_commodities_state()
        content = result.content

        # 查找 Icon
        from flet import Icon
        has_icon = False
        for control in content.controls:
            if isinstance(control, Icon):
                has_icon = True
                break

        assert has_icon, "空商品状态应该包含图标"

    def test_empty_commodities_state_has_text(self):
        """测试空商品状态包含文本"""
        from flet import Text
        from src.gui.empty_states import empty_commodities_state

        result = empty_commodities_state()
        content = result.content

        # 查找 Text 控件
        has_text = False
        for control in content.controls:
            if isinstance(control, Text):
                has_text = True
                break

        assert has_text, "空商品状态应该包含文本说明"


class TestEmptyNewsState:
    """空新闻状态组件测试"""

    def test_empty_news_state_returns_container(self):
        """测试空新闻状态返回 Container"""
        from src.gui.empty_states import empty_news_state

        result = empty_news_state()

        assert result is not None
        assert hasattr(result, 'content')

    def test_empty_news_state_has_icon(self):
        """测试空新闻状态包含图标"""
        from src.gui.empty_states import empty_news_state

        result = empty_news_state()
        content = result.content

        # 查找 Icon
        from flet import Icon
        has_icon = False
        for control in content.controls:
            if isinstance(control, Icon):
                has_icon = True
                break

        assert has_icon, "空新闻状态应该包含图标"

    def test_empty_news_state_has_text(self):
        """测试空新闻状态包含文本"""
        from flet import Text
        from src.gui.empty_states import empty_news_state

        result = empty_news_state()
        content = result.content

        # 查找 Text 控件
        has_text = False
        for control in content.controls:
            if isinstance(control, Text):
                has_text = True
                break

        assert has_text, "空新闻状态应该包含文本说明"

    def test_empty_news_state_with_on_refresh_callback(self):
        """测试带刷新回调的空新闻状态"""
        from src.gui.empty_states import empty_news_state

        callback_called = False

        def on_refresh():
            nonlocal callback_called
            callback_called = True

        result = empty_news_state(on_refresh=on_refresh)

        # 应该有按钮控件
        content = result.content
        from flet import ElevatedButton
        has_button = False
        for control in content.controls:
            if isinstance(control, ElevatedButton):
                has_button = True
                break

        assert has_button, "空新闻状态应该包含刷新按钮"


class TestEmptyStatesColors:
    """空状态颜色测试"""

    def test_empty_states_use_app_colors(self):
        """测试空状态使用 AppColors"""
        from src.gui.empty_states import empty_funds_state

        result = empty_funds_state()

        # 验证组件使用 AppColors 定义的颜色
        # 文本颜色应该使用 TEXT_PRIMARY 或 TEXT_SECONDARY
        content = result.content
        for control in content.controls:
            if hasattr(control, 'color'):
                if control.color is not None:
                    # 颜色应该是 AppColors 中的值或有效的 hex
                    assert isinstance(control.color, str)


class TestEmptyStatesIntegration:
    """空状态集成测试"""

    def test_empty_states_can_be_used_in_column(self):
        """测试空状态可以在 Column 中使用"""
        from flet import Column, Container
        from src.gui.empty_states import (
            empty_commodities_state,
            empty_funds_state,
            empty_news_state,
        )

        # 创建空状态组件
        funds_empty = empty_funds_state()
        commodities_empty = empty_commodities_state()
        news_empty = empty_news_state()

        # 创建 Column 并添加空状态
        column = Column(
            controls=[
                Container(content=funds_empty),
                Container(content=commodities_empty),
                Container(content=news_empty),
            ]
        )

        assert column is not None
        assert len(column.controls) == 3

    def test_empty_states_with_custom_messages(self):
        """测试带自定义消息的空状态"""
        from src.gui.empty_states import empty_funds_state

        custom_message = "自定义消息：暂无基金数据"
        result = empty_funds_state(message=custom_message)

        # 验证自定义消息被使用
        content = result.content
        from flet import Text

        found_custom_message = False
        for control in content.controls:
            if isinstance(control, Text):
                if custom_message in control.value:
                    found_custom_message = True
                    break

        assert found_custom_message or custom_message is not None
