#!/usr/bin/env python3
"""Fund Real-Time Valuation Application

默认运行 GUI 版本（Flet）。如需运行 TUI 版本，使用 --tui 参数。

用法：
    python run_tui.py          # GUI 版本（默认）
    python run_tui.py --tui    # TUI 版本
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
    if len(sys.argv) > 1 and sys.argv[1] == "--tui":
        # TUI 模式
        from ui.app import FundTUIApp

        app = FundTUIApp()
        app.run()
    else:
        # GUI 模式（默认）
        from src.gui.main import main as gui_main

        gui_main()


if __name__ == "__main__":
    main()
