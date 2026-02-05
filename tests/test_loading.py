# -*- coding: UTF-8 -*-
"""Tests for loading state functionality"""

import sys
import os
import pytest
from unittest.mock import Mock, MagicMock, patch
from dataclasses import dataclass, field
from typing import List, Optional

# Add project paths
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_ROOT = os.path.join(PROJECT_ROOT, 'src')
if SRC_ROOT not in sys.path:
    sys.path.insert(0, SRC_ROOT)

# Import GUI components
from src.gui.components import FundCard, AppColors, get_change_color


class TestFundCardLoadingState:
    """Tests for FundCard loading state functionality"""

    def test_fundcard_has_loading_attribute(self):
        """Test that FundCard has loading state attribute"""
        card = FundCard(
            code="000001",
            name="测试基金",
            net_value=1.2345,
            est_value=1.2456,
            change_pct=0.9,
            profit=100.0,
        )
        assert hasattr(card, 'loading'), "FundCard should have loading attribute"

    def test_fundcard_loading_default_false(self):
        """Test that loading state defaults to False"""
        card = FundCard(
            code="000001",
            name="测试基金",
            net_value=1.2345,
            est_value=1.2456,
            change_pct=0.9,
            profit=100.0,
        )
        assert card.loading == False, "Loading state should default to False"

    def test_fundcard_set_loading_true(self):
        """Test setting loading state to True"""
        card = FundCard(
            code="000001",
            name="测试基金",
            net_value=1.2345,
            est_value=1.2456,
            change_pct=0.9,
            profit=100.0,
        )
        card.set_loading(True)
        assert card.loading == True, "Loading state should be True after set_loading(True)"

    def test_fundcard_set_loading_false(self):
        """Test setting loading state to False"""
        card = FundCard(
            code="000001",
            name="测试基金",
            net_value=1.2345,
            est_value=1.2456,
            change_pct=0.9,
            profit=100.0,
        )
        card.set_loading(True)
        card.set_loading(False)
        assert card.loading == False, "Loading state should be False after set_loading(False)"

    def test_fundcard_has_progress_ring(self):
        """Test that FundCard has ProgressRing component when loading"""
        card = FundCard(
            code="000001",
            name="测试基金",
            net_value=1.2345,
            est_value=1.2456,
            change_pct=0.9,
            profit=100.0,
        )
        assert hasattr(card, 'progress_ring'), "FundCard should have progress_ring attribute"

    def test_fundcard_progress_ring_visible_when_loading(self):
        """Test that ProgressRing is visible when loading"""
        card = FundCard(
            code="000001",
            name="测试基金",
            net_value=1.2345,
            est_value=1.2456,
            change_pct=0.9,
            profit=100.0,
        )
        card.set_loading(True)
        # ProgressRing should be visible when loading
        assert card.progress_ring.visible == True, "ProgressRing should be visible when loading"

    def test_fundcard_progress_ring_hidden_when_not_loading(self):
        """Test that ProgressRing is hidden when not loading"""
        card = FundCard(
            code="000001",
            name="测试基金",
            net_value=1.2345,
            est_value=1.2456,
            change_pct=0.9,
            profit=100.0,
        )
        card.set_loading(False)
        # ProgressRing should be hidden when not loading
        assert card.progress_ring.visible == False, "ProgressRing should be hidden when not loading"

    def test_fundcard_content_opacity_when_loading(self):
        """Test that card loading overlay is visible when loading"""
        card = FundCard(
            code="000001",
            name="测试基金",
            net_value=1.2345,
            est_value=1.2456,
            change_pct=0.9,
            profit=100.0,
        )
        card.set_loading(True)
        # Loading overlay should be visible when loading
        assert card._loading_overlay.visible == True, "Loading overlay should be visible when loading"
        assert card.progress_ring.visible == True, "ProgressRing should be visible when loading"


class TestRefreshButtonState:
    """Tests for refresh button disabled state functionality"""

    def test_fundguipp_has_refresh_disabled_state(self):
        """Test that FundGUIApp has refresh button disabled state management"""
        # This test verifies the main app has loading state tracking
        with patch('src.gui.main.ConfigManager'), \
             patch('src.gui.main.DatabaseManager'), \
             patch('src.gui.main.ConfigDAO'), \
             patch('src.gui.main.NotificationManager'):
            from src.gui.main import FundGUIApp
            app = FundGUIApp()
            assert hasattr(app, '_is_loading'), "FundGUIApp should have _is_loading attribute"
            assert hasattr(app, '_refresh_button'), "FundGUIApp should have _refresh_button reference"


class TestLoadingIndicatorIntegration:
    """Integration tests for loading state across components"""

    def test_loading_state_propagation(self):
        """Test that loading state propagates correctly"""
        card = FundCard(
            code="000001",
            name="测试基金",
            net_value=1.2345,
            est_value=1.2456,
            change_pct=0.9,
            profit=100.0,
        )

        # Initially not loading
        assert card.loading == False
        assert card.progress_ring.visible == False

        # Set loading
        card.set_loading(True)
        assert card.loading == True
        assert card.progress_ring.visible == True

        # Set not loading
        card.set_loading(False)
        assert card.loading == False
        assert card.progress_ring.visible == False

    def test_multiple_cards_loading_independently(self):
        """Test that multiple cards can have independent loading states"""
        card1 = FundCard(
            code="000001",
            name="基金1",
            net_value=1.2345,
            est_value=1.2456,
            change_pct=0.9,
            profit=100.0,
        )
        card2 = FundCard(
            code="000002",
            name="基金2",
            net_value=2.3456,
            est_value=2.3567,
            change_pct=-0.5,
            profit=-50.0,
        )

        # Set different loading states
        card1.set_loading(True)
        card2.set_loading(False)

        assert card1.loading == True
        assert card1.progress_ring.visible == True
        assert card2.loading == False
        assert card2.progress_ring.visible == False


class TestLoadingStateMethods:
    """Tests for loading state control methods"""

    def test_set_loading_method_exists(self):
        """Test that set_loading method exists"""
        card = FundCard(
            code="000001",
            name="测试基金",
            net_value=1.2345,
            est_value=1.2456,
            change_pct=0.9,
            profit=100.0,
        )
        assert hasattr(card, 'set_loading'), "FundCard should have set_loading method"
        assert callable(getattr(card, 'set_loading')), "set_loading should be callable"

    def test_toggle_loading_method_exists(self):
        """Test that toggle_loading method exists"""
        card = FundCard(
            code="000001",
            name="测试基金",
            net_value=1.2345,
            est_value=1.2456,
            change_pct=0.9,
            profit=100.0,
        )
        assert hasattr(card, 'toggle_loading'), "FundCard should have toggle_loading method"
        assert callable(getattr(card, 'toggle_loading')), "toggle_loading should be callable"

    def test_toggle_loading_functionality(self):
        """Test toggle_loading flips loading state"""
        card = FundCard(
            code="000001",
            name="测试基金",
            net_value=1.2345,
            est_value=1.2456,
            change_pct=0.9,
            profit=100.0,
        )

        assert card.loading == False

        card.toggle_loading()
        assert card.loading == True

        card.toggle_loading()
        assert card.loading == False


class TestAppLoadingState:
    """Tests for application-level loading state management"""

    def test_app_has_loading_state(self):
        """Test that app has loading state tracking"""
        with patch('src.gui.main.ConfigManager'), \
             patch('src.gui.main.DatabaseManager'), \
             patch('src.gui.main.ConfigDAO'), \
             patch('src.gui.main.NotificationManager'):
            from src.gui.main import FundGUIApp
            app = FundGUIApp()
            # App should track overall loading state
            assert hasattr(app, 'is_loading'), "FundGUIApp should have is_loading property"

    def test_app_set_loading_state(self):
        """Test that app can set loading state"""
        with patch('src.gui.main.ConfigManager'), \
             patch('src.gui.main.DatabaseManager'), \
             patch('src.gui.main.ConfigDAO'), \
             patch('src.gui.main.NotificationManager'):
            from src.gui.main import FundGUIApp
            app = FundGUIApp()

            # Initially not loading
            assert app.is_loading == False

            # Set loading
            app.set_loading(True)
            assert app.is_loading == True

            # Set not loading
            app.set_loading(False)
            assert app.is_loading == False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
