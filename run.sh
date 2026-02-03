#!/bin/bash
# Fund Real-Time Valuation TUI 启动脚本

set -e

# 脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 检测 Python 路径 (优先使用 venv)
if [ -d "venv" ]; then
    PYTHON_CMD="./venv/bin/python"
else
    PYTHON_CMD="python3"
fi

# 检查 Python 是否可用
if ! command -v "$PYTHON_CMD" &> /dev/null; then
    echo "错误: 找不到 Python 解释器"
    exit 1
fi

# 运行应用
exec "$PYTHON_CMD" run_tui.py "$@"
