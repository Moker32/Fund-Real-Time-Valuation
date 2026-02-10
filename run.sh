#!/bin/bash
# Fund Real-Time Valuation Web 启动脚本

set -e

# 脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  基金实时估值 Web${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# 检测 pnpm
if ! command -v pnpm &> /dev/null; then
    echo -e "${RED}错误: 找不到 pnpm，请先安装 Node.js 和 pnpm${NC}"
    echo "安装方式: npm install -g pnpm"
    exit 1
fi

# 检测 uv
if ! command -v uv &> /dev/null; then
    echo -e "${YELLOW}警告: 找不到 uv，尝试使用 python3${NC}"
    PYTHON_CMD="python3"
else
    PYTHON_CMD="uv run python"
fi

# 检查依赖
echo -e "${YELLOW}检查依赖...${NC}"

# 安装前端依赖
if [ ! -d "node_modules" ]; then
    echo -e "${YELLOW}安装前端依赖...${NC}"
    pnpm install
fi

echo ""
echo -e "${GREEN}启动服务...${NC}"
echo ""

# 启动前后端
exec pnpm run dev "$@"
