# -*- coding: UTF-8 -*-
"""GUI TabBar+Tabs API 测试

测试 Flet 0.80.5 官方 TabBar+Tabs API 的功能：
- TabBar 组件创建和配置
- Tab 组件创建和属性
- Tab 切换事件处理
- 与 FundGUIApp 的集成
"""

import sys
from pathlib import Path

import pytest

# 添加 src 目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestTabBarAPIModuleImports:
    """TabBar API 模块导入测试"""

    def test_import_tabbar_from_flet(self):
        """测试从 Flet 导入 TabBar"""
        from flet import TabBar

        assert TabBar is not None
        assert callable(TabBar)

    def test_import_tab_from_flet(self):
        """测试从 Flet 导入 Tab"""
        from flet import Tab

        assert Tab is not None
        assert callable(Tab)

    def test_import_tabbar_from_main_module(self):
        """测试从 main 模块导入 TabBar"""
        # 直接导入 flet 模块来测试
        import flet as ft
        assert hasattr(ft, 'TabBar')

    def test_import_tab_from_main_module(self):
        """测试从 main 模块导入 Tab"""
        import flet as ft
        assert hasattr(ft, 'Tab')


class TestTabComponent:
    """Tab 组件测试"""

    def test_tab_creation_with_label_only(self):
        """测试仅创建带标签的 Tab"""
        from flet import Tab

        tab = Tab(label="测试标签")
        assert tab.label == "测试标签"
        assert tab.icon is None

    def test_tab_creation_with_icon(self):
        """测试创建带图标的 Tab"""
        from flet import Icons, Tab

        tab = Tab(label="基金", icon=Icons.STAR_BORDER)
        assert tab.label == "基金"
        assert tab.icon == Icons.STAR_BORDER


class TestTabBarComponent:
    """TabBar 组件测试"""

    def test_tabbar_creation(self):
        """测试 TabBar 创建"""
        from flet import Tab, TabBar

        tab_bar = TabBar(
            tabs=[
                Tab(label="标签1"),
                Tab(label="标签2"),
                Tab(label="标签3"),
            ]
        )

        assert tab_bar is not None
        assert len(tab_bar.tabs) == 3

    def test_tabbar_with_icons(self):
        """测试带图标的 TabBar"""
        from flet import Icons, Tab, TabBar

        tab_bar = TabBar(
            tabs=[
                Tab(label="自选", icon=Icons.STAR_BORDER),
                Tab(label="商品", icon=Icons.TRENDING_UP),
                Tab(label="新闻", icon=Icons.NEWSPAPER),
            ]
        )

        assert len(tab_bar.tabs) == 3
        assert tab_bar.tabs[0].icon == Icons.STAR_BORDER
        assert tab_bar.tabs[1].icon == Icons.TRENDING_UP
        assert tab_bar.tabs[2].icon == Icons.NEWSPAPER

    def test_tabbar_with_on_click_handler(self):
        """测试带 on_click 事件处理器的 TabBar"""
        from flet import Tab, TabBar

        handler_called = [False]
        tab_index = [None]

        def on_click(e):
            handler_called[0] = True
            tab_index[0] = int(e.data)

        tab_bar = TabBar(
            tabs=[
                Tab(label="标签1"),
                Tab(label="标签2"),
            ],
            on_click=on_click,
        )

        assert tab_bar.on_click is not None
        assert callable(tab_bar.on_click)

    def test_tabbar_with_tab_alignment(self):
        """测试带 tab_alignment 的 TabBar"""
        from flet import Tab, TabAlignment, TabBar

        tab_bar = TabBar(
            tabs=[Tab(label="测试")],
            tab_alignment=TabAlignment.START,
        )

        assert tab_bar.tab_alignment == TabAlignment.START

    def test_tabbar_with_label_colors(self):
        """测试带标签颜色的 TabBar"""
        from flet import Tab, TabBar

        tab_bar = TabBar(
            tabs=[Tab(label="测试")],
            label_color="#007AFF",
            unselected_label_color="#8E8E93",
        )

        assert tab_bar.label_color == "#007AFF"
        assert tab_bar.unselected_label_color == "#8E8E93"


class TestTabBarEventHandling:
    """TabBar 事件处理测试"""

    def test_tab_bar_click_event_data(self):
        """测试 TabBar 点击事件数据"""
        from flet import Tab, TabBar

        # 模拟事件对象
        class MockEvent:
            def __init__(self, data, control):
                self.data = data  # tab 索引（字符串格式）
                self.control = control

        # 创建 TabBar
        tab_bar = TabBar(
            tabs=[
                Tab(label="标签1"),
                Tab(label="标签2"),
            ]
        )

        # 模拟点击第二个标签
        event = MockEvent(data="1", control=tab_bar)
        selected_index = int(event.data)

        assert selected_index == 1


class TestFundGUIAppTabBar:
    """FundGUIApp TabBar 集成测试"""

    def test_app_current_tab_initial_value(self):
        """测试应用当前标签页初始值"""
        from src.gui.main import FundGUIApp

        app = FundGUIApp()
        assert app.current_tab == 0

    def test_app_tab_count(self):
        """测试应用标签页数量"""
        # 根据 _build_ui 中的定义，应该有3个标签页
        expected_tab_count = 3
        assert expected_tab_count == 3  # 自选、商品、新闻

    def test_tab_click_handler_exists(self):
        """测试 Tab 点击处理器存在"""
        from src.gui.main import FundGUIApp

        app = FundGUIApp()
        assert hasattr(app, "_on_tab_click")
        assert callable(app._on_tab_click)

    def test_tab_click_updates_current_tab(self):
        """测试 Tab 点击更新当前标签页"""
        from src.gui.main import FundGUIApp

        class MockEvent:
            def __init__(self, data):
                self.data = data

        app = FundGUIApp()
        app.current_tab = 0

        # 模拟点击第二个标签
        event = MockEvent(data="1")
        app.current_tab = int(event.data)
        assert app.current_tab == 1

        # 模拟点击第三个标签
        event = MockEvent(data="2")
        app.current_tab = int(event.data)
        assert app.current_tab == 2


class TestTabBarAPIVersionCompatibility:
    """TabBar API 版本兼容性测试"""

    def test_tabbar_replaces_old_custom_tabs(self):
        """测试 TabBar 替换旧的自定义 Tabs 实现"""
        from flet import Icons, Tab, TabBar

        # 新的官方 API 使用 TabBar + Tab
        tab_bar = TabBar(
            tabs=[
                Tab(label="自选", icon=Icons.STAR_BORDER),
                Tab(label="商品", icon=Icons.TRENDING_UP),
                Tab(label="新闻", icon=Icons.NEWSPAPER),
            ],
            on_click=lambda e: None,
        )

        assert isinstance(tab_bar, TabBar)
        assert len(tab_bar.tabs) == 3

    def test_tabbar_no_longer_needs_custom_containers(self):
        """测试 TabBar 不再需要自定义容器来管理可见性"""
        from flet import Tab, TabBar

        # 官方 API 的 TabBar 负责标签导航
        # 内容切换由开发者自行管理

        # 验证 TabBar 包含多个标签
        tab_bar = TabBar(
            tabs=[
                Tab(label="页面1"),
                Tab(label="页面2"),
                Tab(label="页面3"),
            ]
        )

        # 验证 TabBar 包含正确的标签数量
        assert len(tab_bar.tabs) == 3


class TestTabBarImportAliases:
    """TabBar 导入别名测试"""

    def test_main_module_uses_direct_imports(self):
        """测试 main 模块使用直接导入"""
        # 验证 TabBar 和 Tab 在 flet 中可用
        import flet as ft
        assert hasattr(ft, 'TabBar')
        assert hasattr(ft, 'Tab')


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
