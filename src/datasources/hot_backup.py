import asyncio
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any

from src.datasources.unified_models import DataResponse


class CircuitState(IntEnum):
    CLOSED = 0
    OPEN = 1
    HALF_OPEN = 2


@dataclass
class CircuitConfig:
    failure_threshold: int = 5
    success_threshold: int = 2
    timeout_seconds: float = 30.0
    half_open_max_calls: int = 3


class CircuitBreaker:
    def __init__(self, name: str, config: CircuitConfig | None = None):
        self.name = name
        self.config = config or CircuitConfig()
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time = 0.0
        self._half_open_calls = 0
        self._lock = asyncio.Lock()

    @property
    def state(self) -> CircuitState:
        return self._state

    def can_execute(self) -> bool:
        if self._state == CircuitState.CLOSED:
            return True
        if self._state == CircuitState.OPEN:
            if time.time() - self._last_failure_time >= self.config.timeout_seconds:
                return True
            return False
        if self._state == CircuitState.HALF_OPEN:
            return self._half_open_calls < self.config.half_open_max_calls
        return False

    async def record_success(self):
        async with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                self._success_count += 1
                if self._success_count >= self.config.success_threshold:
                    self._state = CircuitState.CLOSED
                    self._failure_count = 0
                    self._success_count = 0
                    self._half_open_calls = 0
            elif self._state == CircuitState.CLOSED:
                self._failure_count = 0

    async def record_failure(self):
        async with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.time()

            if self._state == CircuitState.CLOSED:
                if self._failure_count >= self.config.failure_threshold:
                    self._state = CircuitState.OPEN
            elif self._state == CircuitState.HALF_OPEN:
                self._state = CircuitState.OPEN
                self._half_open_calls = 0
                self._success_count = 0

    async def record_half_open(self):
        async with self._lock:
            if self._state == CircuitState.OPEN:
                if time.time() - self._last_failure_time >= self.config.timeout_seconds:
                    self._state = CircuitState.HALF_OPEN
                    self._half_open_calls = 0
                    self._success_count = 0

    async def execute(self, func: Callable[..., Any], *args, **kwargs) -> tuple[bool, Any]:
        await self.record_half_open()

        if not self.can_execute():
            return False, None

        try:
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)

            await self.record_success()
            return True, result
        except Exception:
            await self.record_failure()
            return False, None

    def get_stats(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "state": self._state.name,
            "failure_count": self._failure_count,
            "success_count": self._success_count,
            "half_open_calls": self._half_open_calls,
        }


class CircuitBreakerManager:
    def __init__(self):
        self._breakers: dict[str, CircuitBreaker] = {}
        self._lock = asyncio.Lock()

    def get_breaker(self, name: str, config: CircuitConfig | None = None) -> CircuitBreaker:
        if name not in self._breakers:
            self._breakers[name] = CircuitBreaker(name, config)
        return self._breakers[name]

    def get_all_stats(self) -> dict[str, dict[str, Any]]:
        return {name: breaker.get_stats() for name, breaker in self._breakers.items()}


@dataclass
class HotBackupResult:
    primary_response: DataResponse | None = None
    backup_responses: list[DataResponse] = field(default_factory=list)
    total_calls: int = 0
    successful_calls: int = 0
    fastest_response_ms: float = 0.0

    @property
    def success(self) -> bool:
        if self.primary_response is not None and self.primary_response.success:
            return True
        return any(r.success for r in self.backup_responses)


class HotBackupManager:
    def __init__(self, timeout: float = 10.0):
        self.timeout = timeout

    async def fetch_with_backup(
        self,
        primary_func: Callable[..., Any],
        backup_funcs: list[Callable[..., Any]],
        *args,
        **kwargs,
    ) -> HotBackupResult:
        result = HotBackupResult()

        tasks = []
        task_funcs = [primary_func] + backup_funcs

        async def safe_call(func):
            start = time.perf_counter()
            try:
                if asyncio.iscoroutinefunction(func):
                    resp = await func(*args, **kwargs)
                else:
                    resp = func(*args, **kwargs)
                latency = (time.perf_counter() - start) * 1000
                return True, resp, latency
            except Exception as e:
                latency = (time.perf_counter() - start) * 1000
                return False, str(e), latency

        tasks = [asyncio.create_task(safe_call(f)) for f in task_funcs]

        done, pending = await asyncio.wait(
            tasks, timeout=self.timeout, return_when=asyncio.FIRST_COMPLETED
        )

        for task in pending:
            task.cancel()

        responses = []
        for task in done:
            success, resp, latency = task.result()
            result.total_calls += 1
            if isinstance(resp, DataResponse):
                responses.append((resp, latency))
                if result.fastest_response_ms == 0 or latency < result.fastest_response_ms:
                    result.fastest_response_ms = latency

        if responses:
            successful_responses = [
                (resp, lat)
                for resp, lat in responses
                if isinstance(resp, DataResponse) and resp.success
            ]
            if successful_responses:
                result.primary_response = successful_responses[0][0]
                result.backup_responses = [r[0] for r in successful_responses[1:]]
                result.successful_calls = len(successful_responses)
            else:
                result.primary_response = responses[0][0]
                result.backup_responses = [r[0] for r in responses[1:]]

        return result


__all__ = [
    "CircuitBreaker",
    "CircuitBreakerManager",
    "CircuitConfig",
    "CircuitState",
    "HotBackupManager",
    "HotBackupResult",
]
