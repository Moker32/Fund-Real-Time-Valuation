"""
Celery Beat 启动脚本

用法:
    python run_celery_beat.py
    python run_celery_beat.py --loglevel=info
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="启动 Celery Beat 定时任务调度器")
    parser.add_argument(
        "--loglevel",
        default="info",
        choices=["debug", "info", "warning", "error"],
        help="日志级别",
    )
    parser.add_argument(
        "--schedule",
        default="celerybeat-schedule",
        help="调度文件路径",
    )
    parser.add_argument(
        "--max-interval",
        type=int,
        default=5,
        help="最大调度间隔（秒）",
    )

    args = parser.parse_args()

    from celery.apps.beat import Beat
    from src.tasks import celery_app

    beat = Beat(
        app=celery_app,
        schedule_filename=args.schedule,
        max_interval=args.max_interval,
        loglevel=args.loglevel,
    )

    print(f"启动 Celery Beat: schedule={args.schedule}, max_interval={args.max_interval}s")
    beat.run()
