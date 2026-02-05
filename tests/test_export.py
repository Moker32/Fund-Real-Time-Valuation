# -*- coding: UTF-8 -*-
"""数据导出功能测试"""

import csv
import os
import pytest
import tempfile

from src.config.models import Fund, Holding


class TestExportFundsToCsv:
    """基金导出 CSV 测试"""

    def test_export_funds_to_csv(self, tmp_path):
        """测试基金导出到 CSV 文件"""
        from src.utils.export import export_funds_to_csv

        funds = [
            Fund(code="000001", name="华夏成长混合"),
            Fund(code="000002", name="华夏回报混合"),
            Fund(code="110011", name="华夏大盘精选"),
        ]

        filepath = tmp_path / "funds.csv"
        export_funds_to_csv(funds, str(filepath))

        # 验证文件创建
        assert os.path.exists(filepath)

        # 验证文件内容
        with open(filepath, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        assert len(rows) == 3
        assert rows[0]["code"] == "000001"
        assert rows[0]["name"] == "华夏成长混合"
        assert rows[1]["code"] == "000002"
        assert rows[1]["name"] == "华夏回报混合"
        assert rows[2]["code"] == "110011"
        assert rows[2]["name"] == "华夏大盘精选"

    def test_export_empty_funds(self, tmp_path):
        """测试导出空基金列表"""
        from src.utils.export import export_funds_to_csv

        filepath = tmp_path / "empty_funds.csv"
        export_funds_to_csv([], str(filepath))

        assert os.path.exists(filepath)

        with open(filepath, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        assert len(rows) == 0

    def test_export_funds_csv_headers(self, tmp_path):
        """测试导出 CSV 包含正确的表头"""
        from src.utils.export import export_funds_to_csv

        funds = [Fund(code="000001", name="测试基金")]

        filepath = tmp_path / "headers_test.csv"
        export_funds_to_csv(funds, str(filepath))

        with open(filepath, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames

        assert "code" in headers
        assert "name" in headers


class TestExportPortfolioReport:
    """持仓报告导出测试"""

    def test_export_portfolio_report(self, tmp_path):
        """测试持仓报告导出"""
        from src.utils.export import export_portfolio_report

        holdings = [
            Holding(code="000001", name="华夏成长混合", shares=1000.0, cost=1.5),
            Holding(code="000002", name="华夏回报混合", shares=500.0, cost=2.0),
        ]

        filepath = tmp_path / "portfolio.csv"
        export_portfolio_report(holdings, str(filepath))

        # 验证文件创建
        assert os.path.exists(filepath)

        # 验证文件内容
        with open(filepath, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        assert len(rows) == 2

        # 检查第一条记录
        assert rows[0]["code"] == "000001"
        assert rows[0]["name"] == "华夏成长混合"
        assert rows[0]["shares"] == "1000.0"
        assert rows[0]["cost"] == "1.5"
        assert rows[0]["total_cost"] == "1500.0"  # 1000 * 1.5 = 1500

        # 检查第二条记录
        assert rows[1]["code"] == "000002"
        assert rows[1]["name"] == "华夏回报混合"
        assert rows[1]["shares"] == "500.0"
        assert rows[1]["cost"] == "2.0"
        assert rows[1]["total_cost"] == "1000.0"  # 500 * 2.0 = 1000

    def test_export_empty_portfolio(self, tmp_path):
        """测试导出空持仓报告"""
        from src.utils.export import export_portfolio_report

        filepath = tmp_path / "empty_portfolio.csv"
        export_portfolio_report([], str(filepath))

        assert os.path.exists(filepath)

        with open(filepath, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        assert len(rows) == 0

    def test_export_portfolio_csv_headers(self, tmp_path):
        """测试持仓报告 CSV 包含正确的表头"""
        from src.utils.export import export_portfolio_report

        holdings = [Holding(code="000001", name="测试", shares=100.0, cost=1.0)]

        filepath = tmp_path / "portfolio_headers.csv"
        export_portfolio_report(holdings, str(filepath))

        with open(filepath, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames

        assert "code" in headers
        assert "name" in headers
        assert "shares" in headers
        assert "cost" in headers
        assert "total_cost" in headers


class TestExportFileCreated:
    """文件创建验证测试"""

    def test_export_file_created(self, tmp_path):
        """验证导出文件被正确创建"""
        from src.utils.export import export_funds_to_csv

        funds = [Fund(code="000001", name="测试基金")]
        filepath = tmp_path / "test_file.csv"

        result = export_funds_to_csv(funds, str(filepath))

        assert os.path.isfile(filepath)
        assert result is True

    def test_export_file_overwrite(self, tmp_path):
        """测试导出文件可以被覆盖"""
        from src.utils.export import export_funds_to_csv

        funds1 = [Fund(code="000001", name="基金1")]
        funds2 = [Fund(code="000002", name="基金2")]

        filepath = tmp_path / "overwrite_test.csv"

        # 第一次导出
        export_funds_to_csv(funds1, str(filepath))
        with open(filepath, "r", encoding="utf-8-sig") as f:
            content1 = f.read()

        # 第二次导出（覆盖）
        export_funds_to_csv(funds2, str(filepath))
        with open(filepath, "r", encoding="utf-8-sig") as f:
            content2 = f.read()

        # 验证文件内容已更新
        assert "基金1" not in content2
        assert "基金2" in content2
