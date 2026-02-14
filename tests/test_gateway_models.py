import pytest

from src.datasources.base import DataSourceType
from src.datasources.unified_models import (
    BatchDataRequest,
    BatchDataResponse,
    DataRequest,
    DataResponse,
    RequestPriority,
    ResponseStatus,
)


class TestDataRequest:
    def test_create_request(self):
        req = DataRequest(symbol="161039", source_type=DataSourceType.FUND)
        assert req.symbol == "161039"
        assert req.source_type == DataSourceType.FUND
        assert req.priority == RequestPriority.NORMAL
        assert req.allow_fallback is True
        assert req.request_id is not None

    def test_create_request_with_priority(self):
        req = DataRequest(
            symbol="161039",
            source_type=DataSourceType.FUND,
            priority=RequestPriority.HIGH,
        )
        assert req.priority == RequestPriority.HIGH

    def test_to_dict(self):
        req = DataRequest(symbol="161039", source_type=DataSourceType.FUND)
        d = req.to_dict()
        assert d["symbol"] == "161039"
        assert d["source_type"] == "fund"


class TestDataResponse:
    def test_create_success_response(self):
        resp = DataResponse(request_id="test-001", success=True, data={"price": 1.23})
        assert resp.success is True
        assert resp.data == {"price": 1.23}
        assert resp.error is None
        assert resp.status == ResponseStatus.SUCCESS

    def test_create_error_response(self):
        resp = DataResponse(
            request_id="test-001",
            success=False,
            error="Network error",
        )
        assert resp.success is False
        assert resp.error == "Network error"
        assert resp.status == ResponseStatus.FAILED

    def test_to_dict(self):
        resp = DataResponse(request_id="test-001", success=True, data={"price": 1.23})
        d = resp.to_dict()
        assert d["success"] is True
        assert d["data"] == {"price": 1.23}

    def test_from_result(self):
        from src.datasources.base import DataSourceResult

        request = DataRequest(symbol="161039", source_type=DataSourceType.FUND)
        result = DataSourceResult(
            success=True,
            data={"price": 1.23},
            source="fund123",
            timestamp=1234567890.0,
        )
        resp = DataResponse.from_result(request, result, latency_ms=100.0)
        assert resp.success is True
        assert resp.source == "fund123"
        assert resp.latency_ms == 100.0


class TestBatchDataRequest:
    def test_create_batch_request(self):
        requests = [
            DataRequest(symbol="161039", source_type=DataSourceType.FUND),
            DataRequest(symbol="000001", source_type=DataSourceType.STOCK),
        ]
        batch = BatchDataRequest(requests=requests, parallel=True)
        assert len(batch) == 2
        assert batch.parallel is True


class TestBatchDataResponse:
    def test_success_rate(self):
        responses = [
            DataResponse(request_id="1", success=True),
            DataResponse(request_id="2", success=True),
            DataResponse(request_id="3", success=False),
        ]
        batch_resp = BatchDataResponse(
            request_id="batch-001",
            responses=responses,
            total_count=3,
            success_count=2,
            failed_count=1,
            total_latency_ms=100.0,
        )
        assert batch_resp.success_rate == pytest.approx(2 / 3)


class TestRequestPriority:
    def test_priority_order(self):
        assert RequestPriority.LOW < RequestPriority.NORMAL
        assert RequestPriority.NORMAL < RequestPriority.HIGH
        assert RequestPriority.HIGH < RequestPriority.CRITICAL
