#!/usr/bin/env python
"""
FastAPI 服务启动脚本
"""

import argparse
import uvicorn


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="基金实时估值 API 服务")
    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="绑定地址 (默认: 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="端口号 (默认: 8000)",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="启用热重载 (开发模式)",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="工作进程数 (默认: 1)",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="info",
        choices=["debug", "info", "warning", "error"],
        help="日志级别 (默认: info)",
    )

    args = parser.parse_args()

    uvicorn.run(
        "api.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        workers=args.workers if not args.reload else 1,
        log_level=args.log_level,
    )


if __name__ == "__main__":
    main()
