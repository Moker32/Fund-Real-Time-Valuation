from celery import Celery

broker_url = "redis://localhost:6379/0"
result_backend = "redis://localhost:6379/1"
task_serializer = "json"
result_serializer = "json"
accept_content = ["json"]
timezone = "Asia/Shanghai"
enable_utc = True

task_routes = {
    "src.tasks.cache_tasks.*": {"queue": "cache"},
    "src.tasks.health_tasks.*": {"queue": "health"},
    "src.tasks.fund_tasks.*": {"queue": "funds"},
    "src.tasks.push_tasks.*": {"queue": "pubsub"},
}

beat_schedule = {
    "periodic-cache-warmup-every-5-minutes": {
        "task": "src.tasks.cache_tasks.periodic_warmup",
        "schedule": 300.0,
    },
    "periodic-cache-cleanup-every-hour": {
        "task": "src.tasks.cache_tasks.periodic_cleanup",
        "schedule": 3600.0,
    },
    "periodic-health-check-every-minute": {
        "task": "src.tasks.health_tasks.periodic_check",
        "schedule": 60.0,
    },
    # WebSocket Push Tasks (every 30 seconds)
    "periodic-push-fund-update": {
        "task": "src.tasks.push_tasks.push_fund_update",
        "schedule": 30.0,
    },
    "periodic-push-commodity-update": {
        "task": "src.tasks.push_tasks.push_commodity_update",
        "schedule": 30.0,
    },
    "periodic-push-index-update": {
        "task": "src.tasks.push_tasks.push_index_update",
        "schedule": 30.0,
    },
}

task_base = Celery
