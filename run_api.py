#!/usr/bin/env -S uv run python
"""Fund Real-Time Valuation Web Application

基金实时估值 Web 应用入口。

用法：
    python run_api.py              # 启动 API 服务
    python run_api.py --frontend   # 启动 API + 前端 (需 pnpm)
    python run_api.py --open       # 启动后自动打开浏览器
    python run_api.py --port 8080  # 指定端口
"""

import argparse
import subprocess
import webbrowser
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(
        description="基金实时估值 Web 应用"
    )
    parser.add_argument(
        "--frontend", "-f",
        action="store_true",
        help="同时启动前端开发服务器 (需要 pnpm)"
    )
    parser.add_argument(
        "--port", "-p",
        type=int,
        default=8000,
        help="API 服务端口 (默认: 8000)"
    )
    parser.add_argument(
        "--open", "-o",
        action="store_true",
        help="启动后自动打开浏览器"
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="绑定地址 (默认: 0.0.0.0)"
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="启用热重载 (开发模式)"
    )

    args = parser.parse_args()

    # 打印启动信息
    print(f"""
========================================
  基金实时估值 Web API 服务
========================================

API 文档: http://localhost:{args.port}/docs
健康检查: http://localhost:{args.port}/api/health

按 Ctrl+C 停止服务
""")

    # 如果需要打开浏览器
    if args.open:
        webbrowser.open(f"http://localhost:{args.port}")

    # 如果需要启动前端
    if args.frontend:
        web_dir = Path(__file__).parent / "web"
        print("启动前端开发服务器...")
        subprocess.Popen(
            ["pnpm", "run", "dev", "--port", "5173"],
            cwd=web_dir
        )
        print("前端开发服务器已启动: http://localhost:5173")
        print("按 Ctrl+C 停止前端服务器")

    # 启动 API 服务
    import uvicorn

    uvicorn.run(
        "api.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="info",
    )


if __name__ == "__main__":
    main()
