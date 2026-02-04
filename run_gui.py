#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""Fund Real-Time Valuation GUI Application Entry Point

GUI 入口文件，运行 Flet 图形化界面。
使用方式：
    python run_gui.py
    ./run_gui.py
"""

import sys
from pathlib import Path

# 添加 src 到路径
src_path = Path(__file__).parent / "src"
if src_path.exists():
    sys.path.insert(0, str(src_path))


def main():
    """主入口函数"""
    from src.gui.main import main as gui_main

    gui_main()


if __name__ == "__main__":
    main()
