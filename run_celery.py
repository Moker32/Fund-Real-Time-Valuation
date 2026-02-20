"""
Celery Worker 启动脚本

用法:
    python run_celery.py
    python run_celery.py --loglevel=info
    python run_celery.py --concurrency=4
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="启动 Celery Worker")
    parser.add_argument(
        "--loglevel",
        default="info",
        choices=["debug", "info", "warning", "error"],
        help="日志级别",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=4,
        help="并发 worker 数量",
    )
    parser.add_argument(
        "--pool",
        default="prefork",
        choices=["prefork", "solo", "threads", "gevent"],
        help="Worker 池类型",
    )
    parser.add_argument(
        "--queues",
        default="celery",
        help="监听的队列（逗号分隔）",
    )

    args = parser.parse_args()

    from src.tasks import celery_app

    argv = [
        "worker",
        f"--loglevel={args.loglevel}",
        f"--concurrency={args.concurrency}",
        f"--pool={args.pool}",
        f"--queues={args.queues}",
    ]

    print(f"启动 Celery Worker: {' '.join(argv)}")
    celery_app.worker_main(argv)
