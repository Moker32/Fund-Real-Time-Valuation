import asyncio

from src.datasources.hot_backup import (
    CircuitBreaker,
    CircuitBreakerManager,
    CircuitConfig,
    CircuitState,
)


class TestCircuitBreaker:
    def test_initial_state_closed(self):
        breaker = CircuitBreaker("test", CircuitConfig())
        assert breaker.state == CircuitState.CLOSED
        assert breaker.can_execute() is True

    def test_failure_count_opens_circuit(self):
        breaker = CircuitBreaker(
            "test",
            CircuitConfig(failure_threshold=3, timeout_seconds=60.0),
        )
        assert breaker.state == CircuitState.CLOSED

        asyncio.run(breaker.record_failure())
        assert breaker.state == CircuitState.CLOSED

        asyncio.run(breaker.record_failure())
        assert breaker.state == CircuitState.CLOSED

        asyncio.run(breaker.record_failure())
        assert breaker.state == CircuitState.OPEN
        assert breaker.can_execute() is False

    def test_success_resets_failure_count(self):
        breaker = CircuitBreaker(
            "test",
            CircuitConfig(failure_threshold=3),
        )

        asyncio.run(breaker.record_failure())
        asyncio.run(breaker.record_failure())
        assert breaker._failure_count == 2

        asyncio.run(breaker.record_success())
        assert breaker._failure_count == 0

    def test_half_open_after_timeout(self):
        breaker = CircuitBreaker(
            "test",
            CircuitConfig(failure_threshold=1, timeout_seconds=0.1),
        )

        asyncio.run(breaker.record_failure())
        assert breaker.state == CircuitState.OPEN

        import time

        time.sleep(0.2)

        asyncio.run(breaker.record_half_open())
        assert breaker.state == CircuitState.HALF_OPEN

    def test_half_open_to_closed(self):
        breaker = CircuitBreaker(
            "test",
            CircuitConfig(
                failure_threshold=1,
                success_threshold=2,
                timeout_seconds=0.1,
            ),
        )

        asyncio.run(breaker.record_failure())
        assert breaker.state == CircuitState.OPEN

        import time

        time.sleep(0.2)

        asyncio.run(breaker.record_half_open())
        assert breaker.state == CircuitState.HALF_OPEN

        asyncio.run(breaker.record_success())
        asyncio.run(breaker.record_success())
        assert breaker.state == CircuitState.CLOSED

    def test_get_stats(self):
        breaker = CircuitBreaker("test", CircuitConfig())
        stats = breaker.get_stats()
        assert stats["name"] == "test"
        assert stats["state"] == "CLOSED"
        assert stats["failure_count"] == 0


class TestCircuitBreakerManager:
    def test_get_breaker(self):
        manager = CircuitBreakerManager()
        breaker1 = manager.get_breaker("source1")
        breaker2 = manager.get_breaker("source1")
        assert breaker1 is breaker2

    def test_get_all_stats(self):
        manager = CircuitBreakerManager()
        manager.get_breaker("source1")
        manager.get_breaker("source2")
        stats = manager.get_all_stats()
        assert "source1" in stats
        assert "source2" in stats
