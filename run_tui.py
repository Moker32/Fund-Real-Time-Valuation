#!/usr/bin/env python3
"""Fund Real-Time Valuation Application

基金实时估值图形化界面，基于 Flet 框架开发。

用法：
    python run_tui.py          # GUI 桌面版（默认）
    python run_tui.py --web    # GUI Web 模式
"""

import sys
from pathlib import Path

# Add src to path (relative to this script)
src_path = Path(__file__).parent / "src"
if src_path.exists():
    sys.path.insert(0, str(src_path))


def main():
    """Main entry point."""
    from src.gui.main import main as gui_main

    gui_main()


if __name__ == "__main__":
    main()
