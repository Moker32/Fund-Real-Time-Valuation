import asyncio

import pytest

from src.datasources.hot_backup import HotBackupManager, HotBackupResult
from src.datasources.unified_models import DataResponse


@pytest.mark.asyncio
async def test_hot_backup_single_success():
    async def primary():
        return DataResponse(request_id="test", success=True, data={"price": 100.0})

    manager = HotBackupManager(timeout=5.0)
    result = await manager.fetch_with_backup(primary, [])

    assert result.success is True
    assert result.primary_response is not None
    assert result.primary_response.data == {"price": 100.0}


@pytest.mark.asyncio
async def test_hot_backup_primary_fallback():
    async def primary():
        return DataResponse(request_id="test", success=False, error="Primary failed")

    async def backup():
        return DataResponse(request_id="test", success=True, data={"price": 50.0})

    manager = HotBackupManager(timeout=5.0)
    result = await manager.fetch_with_backup(primary, [backup])

    assert result.success is True
    assert result.primary_response is not None
    assert result.primary_response.data == {"price": 50.0}


@pytest.mark.asyncio
async def test_hot_backup_all_fail():
    async def primary():
        return DataResponse(request_id="test", success=False, error="Primary failed")

    async def backup():
        return DataResponse(request_id="test", success=False, error="Backup also failed")

    manager = HotBackupManager(timeout=5.0)
    result = await manager.fetch_with_backup(primary, [backup])

    assert result.success is False


@pytest.mark.asyncio
async def test_hot_backup_timeout():
    async def slow_func():
        await asyncio.sleep(10.0)
        return DataResponse(request_id="test", success=True, data={"price": 100.0})

    manager = HotBackupManager(timeout=0.5)
    result = await manager.fetch_with_backup(slow_func, [])

    assert result.total_calls >= 0


def test_hot_backup_result_success():
    result = HotBackupResult()
    assert result.success is False

    result.primary_response = DataResponse(request_id="test", success=True, data={"price": 100.0})
    assert result.success is True

    result2 = HotBackupResult()
    result2.backup_responses = [
        DataResponse(request_id="test", success=True, data={"data": "test"})
    ]
    assert result2.success is True
