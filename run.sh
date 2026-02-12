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

# 检查 Python 依赖（使用 uv）
if [ ! -f ".venv" ] || ! uv pip list &>/dev/null; then
    echo -e "${YELLOW}安装 Python 依赖...${NC}"
    uv pip install -r requirements.txt
fi

echo ""
echo -e "${GREEN}启动服务...${NC}"
echo ""

# 启动后端（后台运行）
echo -e "${YELLOW}启动后端服务...${NC}"
BACKEND_PID_FILE="/tmp/fund-api.pid"
API_PORT=8000

# 如果已有后端进程在运行，先停止
if [ -f "$BACKEND_PID_FILE" ]; then
    OLD_PID=$(cat "$BACKEND_PID_FILE")
    if ps -p "$OLD_PID" &>/dev/null; then
        echo "停止旧的后端进程 (PID: $OLD_PID)..."
        kill "$OLD_PID" 2>/dev/null || true
        sleep 1
    fi
    rm -f "$BACKEND_PID_FILE"
fi

# 启动后端
$PYTHON_CMD run_api.py --reload &
BACKEND_PID=$!
echo $BACKEND_PID > "$BACKEND_PID_FILE"
echo -e "${YELLOW}后端进程 PID: $BACKEND_PID${NC}"

# 等待后端就绪
echo -e "${YELLOW}等待后端服务就绪...${NC}"
MAX_RETRIES=30
RETRY_COUNT=0
while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    # 尝试访问健康检查端点
    if curl -s "http://localhost:$API_PORT/api/health/simple" &>/dev/null; then
        echo -e "${GREEN}后端服务已就绪！${NC}"
        break
    fi
    RETRY_COUNT=$((RETRY_COUNT + 1))
    echo -e "${YELLOW}等待后端响应... ($RETRY_COUNT/$MAX_RETRIES)${NC}"
    sleep 1
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo -e "${RED}错误: 后端服务启动超时${NC}"
    rm -f "$BACKEND_PID_FILE"
    exit 1
fi

echo ""
echo -e "${GREEN}启动前端服务...${NC}"
echo ""

# 启动前端（前台运行）
cd web && pnpm run dev
