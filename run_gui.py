#!/usr/bin/env -S uv run python
"""Fund Real-Time Valuation Application

基金实时估值图形化界面，基于 Flet 框架开发。

用法：
    python run_tui.py          # GUI 桌面版（默认）
    python run_tui.py --web   # GUI Web 模式
    python run_tui.py --check  # 检查依赖
"""

import sys
from pathlib import Path

# Add src to path (relative to this script)
src_path = Path(__file__).parent / "src"
if src_path.exists():
    sys.path.insert(0, str(src_path))


def check_dependencies():
    """检查依赖是否已安装"""
    from src.gui.check_deps import check_environment, verify_imports

    env_ok = check_environment()
    import_ok = verify_imports()

    if not (env_ok and import_ok):
        print("✗ 依赖检查未通过，请先安装缺少的依赖")
        sys.exit(1)

    print("✓ 所有依赖检查通过")
    return True


def main():
    """Main entry point."""
    # 检查命令行参数
    if len(sys.argv) > 1:
        arg = sys.argv[1].lower()
        if arg in ["--check", "-c", "check"]:
            # 只检查依赖
            check_dependencies()
            return
        elif arg in ["--help", "-h", "help"]:
            # 显示帮助
            print("用法:")
            print("  python run_tui.py          # 启动 GUI 桌面版")
            print("  python run_tui.py --web    # 启动 GUI Web 模式")
            print("  python run_tui.py --check  # 检查依赖")
            return

    # 检查依赖
    check_dependencies()

    # 启动 GUI
    from src.gui.main import main as gui_main

    gui_main()


if __name__ == "__main__":
    main()
