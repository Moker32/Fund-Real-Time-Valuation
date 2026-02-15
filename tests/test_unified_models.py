# -*- coding: UTF-8 -*-
"""Unified Models Tests

测试统一数据模型
"""


from src.datasources.base import DataSourceType
from src.datasources.unified_models import (
    BatchDataRequest,
    BatchDataResponse,
    DataRequest,
    DataResponse,
    RequestPriority,
    ResponseStatus,
)


class TestRequestPriority:
    """请求优先级测试"""

    def test_priority_values(self):
        """测试优先级值"""
        assert RequestPriority.LOW == 0
        assert RequestPriority.NORMAL == 1
        assert RequestPriority.HIGH == 2
        assert RequestPriority.CRITICAL == 3

    def test_priority_comparison(self):
        """测试优先级比较"""
        assert RequestPriority.LOW < RequestPriority.NORMAL
        assert RequestPriority.NORMAL < RequestPriority.HIGH
        assert RequestPriority.HIGH < RequestPriority.CRITICAL


class TestResponseStatus:
    """响应状态测试"""

    def test_status_values(self):
        """测试状态值"""
        assert ResponseStatus.SUCCESS == 0
        assert ResponseStatus.PARTIAL == 1
        assert ResponseStatus.FAILED == 2
        assert ResponseStatus.TIMEOUT == 3
        assert ResponseStatus.FALLBACK == 4


class TestDataRequest:
    """数据请求测试"""

    def test_data_request_creation(self):
        """测试创建数据请求"""
        request = DataRequest(
            symbol="000001",
            source_type=DataSourceType.FUND
        )

        assert request.symbol == "000001"
        assert request.source_type == DataSourceType.FUND
        assert request.request_id is not None
        assert request.priority == RequestPriority.NORMAL
        assert request.allow_fallback is True

    def test_data_request_with_priority(self):
        """测试指定优先级"""
        request = DataRequest(
            symbol="000001",
            source_type=DataSourceType.FUND,
            priority=RequestPriority.HIGH
        )

        assert request.priority == RequestPriority.HIGH


class TestDataResponse:
    """数据响应测试"""

    def test_data_response_success(self):
        """测试成功响应"""
        response = DataResponse(
            request_id="test-123",
            success=True,
            data={"key": "value"},
            source="test_source"
        )

        assert response.success is True
        assert response.data == {"key": "value"}
        assert response.source == "test_source"

    def test_data_response_failure(self):
        """测试失败响应"""
        response = DataResponse(
            request_id="test-123",
            success=False,
            error="Error message"
        )

        assert response.success is False
        assert response.error == "Error message"

    def test_data_response_status_auto_update(self):
        """测试状态自动更新"""
        # 失败时状态应自动更新为 FAILED
        response = DataResponse(
            request_id="test-123",
            success=False
        )
        
        assert response.status == ResponseStatus.FAILED


class TestBatchDataRequest:
    """批量请求测试"""

    def test_batch_request_creation(self):
        """测试创建批量请求"""
        requests = [
            DataRequest(symbol="000001", source_type=DataSourceType.FUND),
            DataRequest(symbol="000002", source_type=DataSourceType.FUND),
        ]
        
        batch = BatchDataRequest(requests=requests)
        
        assert len(batch.requests) == 2


class TestBatchDataResponse:
    """批量响应测试"""

    def test_batch_response_init(self):
        """测试批量响应创建"""
        # 简单测试批量响应可以初始化
        response = BatchDataResponse(
            request_id="batch-1",
            total_count=2,
            success_count=2,
            failed_count=0,
            total_latency_ms=100.0,
            responses=[]
        )
        
        assert response.total_count == 2
        assert response.success_count == 2
