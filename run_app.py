#!/usr/bin/env -S uv run python
"""Fund Real-Time Valuation Web Application

基金实时估值 Web 应用入口。

用法：
    python run_app.py              # 启动完整应用 (API + 前端，如前端未构建则自动构建)
    python run_app.py --open       # 启动后自动打开浏览器
    python run_app.py --port 8080  # 指定端口
    python run_app.py --no-frontend # 仅启动 API 服务
    python run_app.py --force-build # 强制重新构建前端
"""

import argparse
import subprocess
import webbrowser
from pathlib import Path


def ensure_frontend_built(force_build: bool = False):
    """确保前端已构建，如果 dist 目录不存在或 force_build 为 True 则自动构建。"""
    web_dir = Path(__file__).parent
    dist_dir = web_dir / "web" / "dist"

    need_build = force_build or not dist_dir.exists()

    if need_build:
        if force_build:
            print("强制重新构建前端...")
        else:
            print("前端未构建，正在构建...")
        subprocess.run(
            ["pnpm", "run", "build:web"],
            cwd=web_dir,
            check=True,
        )
        print("前端构建完成")
    else:
        print("前端已构建，跳过构建步骤")


def main():
    parser = argparse.ArgumentParser(description="基金实时估值 Web 应用")
    parser.add_argument("--no-frontend", action="store_true", help="跳过前端构建和服务")
    parser.add_argument("--force-build", action="store_true", help="强制重新构建前端")
    parser.add_argument("--fast", action="store_true", help="快速启动（跳过缓存预热）")
    parser.add_argument("--port", "-p", type=int, default=8000, help="API 服务端口 (默认: 8000)")
    parser.add_argument("--open", "-o", action="store_true", help="启动后自动打开浏览器")
    parser.add_argument("--host", default="0.0.0.0", help="绑定地址 (默认: 0.0.0.0)")
    parser.add_argument("--reload", action="store_true", help="启用热重载 (开发模式)")

    args = parser.parse_args()

    # 确保前端已构建
    if not args.no_frontend:
        ensure_frontend_built(force_build=args.force_build)

    # 打印启动信息
    print(f"""
========================================
  基金实时估值 Web 应用
========================================

前端页面: http://localhost:{args.port}
API 文档: http://localhost:{args.port}/docs
健康检查: http://localhost:{args.port}/api/health
{"快速启动模式" if args.fast else ""}

按 Ctrl+C 停止服务
""")

    # 如果需要打开浏览器
    if args.open:
        webbrowser.open(f"http://localhost:{args.port}")

    # 设置环境变量控制预热行为
    if args.fast:
        import os

        os.environ["SKIP_CACHE_WARMUP"] = "1"

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
