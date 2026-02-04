# -*- coding: UTF-8 -*-
"""Pytest configuration for TUI tests"""

import sys
import os

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
