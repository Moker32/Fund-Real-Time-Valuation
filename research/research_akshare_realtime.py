#!/usr/bin/env python3
"""
Akshare 实时数据接口研究脚本

功能：
1. 列出akshare所有可用函数
2. 搜索包含 "spot", "realtime", "live" 的实时数据接口
3. 搜索港股、美股、全球指数、期货、外汇等相关接口
4. 测试验证发现的接口是否可用
5. 输出详细的发现报告

使用方法：
    uv run python scripts/research_akshare_realtime.py
"""

import inspect
import json
import re
import time
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import akshare as ak


@dataclass
class ApiTestResult:
    """API测试结果"""
    name: str
    category: str
    description: str = ""
    test_status: str = "pending"  # pending, success, failed, skipped
    error_message: str = ""
    response_time_ms: float = 0.0
    sample_data: Any = field(default=None, repr=False)
    data_fields: list = field(default_factory=list)
    data_shape: tuple = field(default_factory=tuple)
    notes: str = ""


@dataclass
class ResearchReport:
    """研究报告"""
    total_functions: int = 0
    realtime_apis: list = field(default_factory=list)
    hk_apis: list = field(default_factory=list)
    us_apis: list = field(default_factory=list)
    global_index_apis: list = field(default_factory=list)
    futures_apis: list = field(default_factory=list)
    forex_apis: list = field(default_factory=list)
    test_results: list = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class AkshareResearcher:
    """Akshare 接口研究员"""

    # 实时数据相关关键词
    REALTIME_KEYWORDS = [
        "spot", "realtime", "live", "current", "now", "tick",
        "实时", "即时", "当前", "行情", "报价", "分时"
    ]

    # 港股相关关键词
    HK_KEYWORDS = [
        "hk", "hongkong", "hong_kong", "港股", "香港"
    ]

    # 美股相关关键词
    US_KEYWORDS = [
        "us", "usa", "america", "nasdaq", "nyse", "美股", "美国"
    ]

    # 全球指数相关关键词
    GLOBAL_INDEX_KEYWORDS = [
        "global", "world", "index", "indices", "指数", "全球", "世界"
    ]

    # 期货相关关键词
    FUTURES_KEYWORDS = [
        "futures", "future", "期货", "commodity", "商品"
    ]

    # 外汇相关关键词
    FOREX_KEYWORDS = [
        "forex", "fx", "currency", "exchange_rate", "外汇", "汇率", "货币"
    ]

    def __init__(self):
        self.all_functions: list[str] = []
        self.report = ResearchReport()
        self.output_dir = Path("scripts/output")
        self.output_dir.mkdir(exist_ok=True)

    def list_all_functions(self) -> list[str]:
        """列出akshare所有可用函数"""
        print("🔍 正在列出所有akshare函数...")

        # 获取所有属性
        all_attrs = dir(ak)

        # 过滤出可调用的函数
        functions = []
        for attr in all_attrs:
            if attr.startswith("_"):
                continue
            try:
                obj = getattr(ak, attr)
                if callable(obj) and not isinstance(obj, type):
                    functions.append(attr)
            except Exception:
                pass

        self.all_functions = sorted(functions)
        self.report.total_functions = len(self.all_functions)

        print(f"✅ 发现 {len(self.all_functions)} 个函数")
        return self.all_functions

    def search_by_keywords(self, keywords: list[str]) -> list[str]:
        """根据关键词搜索函数"""
        results = set()
        pattern = re.compile("|".join(keywords), re.IGNORECASE)

        for func_name in self.all_functions:
            if pattern.search(func_name):
                results.add(func_name)

        return sorted(list(results))

    def categorize_apis(self):
        """对接口进行分类"""
        print("\n📊 正在分类接口...")

        # 实时数据接口
        self.report.realtime_apis = self.search_by_keywords(self.REALTIME_KEYWORDS)
        print(f"  实时数据接口: {len(self.report.realtime_apis)} 个")

        # 港股接口
        self.report.hk_apis = self.search_by_keywords(self.HK_KEYWORDS)
        print(f"  港股接口: {len(self.report.hk_apis)} 个")

        # 美股接口
        self.report.us_apis = self.search_by_keywords(self.US_KEYWORDS)
        print(f"  美股接口: {len(self.report.us_apis)} 个")

        # 全球指数接口
        self.report.global_index_apis = self.search_by_keywords(self.GLOBAL_INDEX_KEYWORDS)
        print(f"  全球指数接口: {len(self.report.global_index_apis)} 个")

        # 期货接口
        self.report.futures_apis = self.search_by_keywords(self.FUTURES_KEYWORDS)
        print(f"  期货接口: {len(self.report.futures_apis)} 个")

        # 外汇接口
        self.report.forex_apis = self.search_by_keywords(self.FOREX_KEYWORDS)
        print(f"  外汇接口: {len(self.report.forex_apis)} 个")

    def get_function_info(self, func_name: str) -> dict:
        """获取函数信息"""
        try:
            func = getattr(ak, func_name)
            doc = inspect.getdoc(func) or ""
            sig = str(inspect.signature(func)) if hasattr(func, "__signature__") else "(...)"

            return {
                "name": func_name,
                "signature": sig,
                "doc": doc[:200] + "..." if len(doc) > 200 else doc,
            }
        except Exception as e:
            return {
                "name": func_name,
                "signature": "(...)",
                "doc": f"Error: {e}",
            }

    def test_api(self, func_name: str, category: str, test_params: dict = None) -> ApiTestResult:
        """测试单个API"""
        result = ApiTestResult(
            name=func_name,
            category=category,
        )

        try:
            func = getattr(ak, func_name)
            result.description = inspect.getdoc(func) or ""

            # 获取函数签名
            sig = inspect.signature(func)
            params = list(sig.parameters.keys())

            # 准备测试参数
            args = []
            kwargs = test_params or {}

            # 记录开始时间
            start_time = time.time()

            # 调用函数
            if kwargs:
                data = func(**kwargs)
            else:
                # 对于无参函数直接调用
                if len(params) == 0:
                    data = func()
                else:
                    # 尝试使用默认参数调用
                    data = func()

            # 计算响应时间
            result.response_time_ms = (time.time() - start_time) * 1000

            # 分析返回数据
            if hasattr(data, 'to_dict'):
                # pandas DataFrame
                result.data_shape = data.shape
                result.data_fields = list(data.columns)
                result.sample_data = data.head(3).to_dict(orient='records')
            elif isinstance(data, (list, dict)):
                result.data_fields = list(data[0].keys()) if isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict) else []
                result.sample_data = data[:3] if isinstance(data, list) else data
            else:
                result.sample_data = str(data)[:500]

            result.test_status = "success"

        except TypeError as e:
            # 需要参数但未被提供
            result.test_status = "skipped"
            result.error_message = f"需要参数: {e}"
            result.notes = "需要特定参数才能调用"

        except Exception as e:
            result.test_status = "failed"
            result.error_message = str(e)

        return result

    def test_apis(self, max_tests_per_category: int = 10):
        """测试各类API"""
        print("\n🧪 开始测试API...")

        # 定义要测试的API及其参数
        test_cases = [
            # 实时数据
            ("stock_zh_a_spot_em", "realtime", {}),
            ("stock_hk_ggt_components_em", "hk", {}),
            ("stock_us_spot_em", "us", {}),
            ("index_global_em", "global_index", {}),
            ("futures_zh_spot", "futures", {"subscribe_list": ["RB0", "CU0"]}),
            ("currency_boc_safe", "forex", {}),
            ("currency_latest", "forex", {}),
            ("stock_zh_index_spot_em", "realtime", {}),
            ("bond_zh_hs_spot", "realtime", {}),
            ("fund_etf_spot_em", "realtime", {}),

            # 港股
            ("stock_hk_spot_em", "hk", {}),
            ("stock_hk_daily", "hk", {"symbol": "00700"}),
            ("stock_hk_hist", "hk", {"symbol": "00700", "period": "daily", "start_date": "20240101", "end_date": "20241231"}),

            # 美股
            ("stock_us_spot_em", "us", {}),
            ("stock_us_daily", "us", {"symbol": "AAPL"}),
            ("stock_us_hist", "us", {"symbol": "105.AAPL", "period": "daily", "start_date": "20240101", "end_date": "20241231"}),

            # 全球指数
            ("index_global_em", "global_index", {}),
            ("index_global_hist_em", "global_index", {"symbol": "DJIA", "period": "daily"}),

            # 期货
            ("futures_zh_spot", "futures", {"subscribe_list": ["RB0", "CU0", "AU0"]}),
            ("futures_zh_daily", "futures", {"symbol": "RB0", "start_date": "20240101", "end_date": "20241231"}),
            ("futures_foreign_commodity_realtime", "futures", {}),

            # 外汇
            ("currency_boc_safe", "forex", {}),
            ("currency_latest", "forex", {}),
            ("currency_hist", "forex", {"symbol": "USD/CNY", "start_date": "20240101", "end_date": "20241231"}),
        ]

        tested = set()
        for func_name, category, params in test_cases:
            if func_name in tested:
                continue
            if not hasattr(ak, func_name):
                continue

            tested.add(func_name)
            print(f"  测试 {func_name}...", end=" ")

            result = self.test_api(func_name, category, params)
            self.report.test_results.append(result)

            status_icon = "✅" if result.test_status == "success" else "⚠️" if result.test_status == "skipped" else "❌"
            print(f"{status_icon} ({result.response_time_ms:.1f}ms)")

        print(f"\n✅ 测试完成，共测试 {len(self.report.test_results)} 个API")

    def generate_markdown_report(self) -> str:
        """生成Markdown格式的报告"""
        lines = []

        # 标题
        lines.append("# Akshare 实时数据接口研究报告")
        lines.append(f"\n生成时间: {self.report.timestamp}")
        lines.append("\n---\n")

        # 概览
        lines.append("## 📊 概览")
        lines.append(f"\n- **总函数数量**: {self.report.total_functions}")
        lines.append(f"- **实时数据接口**: {len(self.report.realtime_apis)}")
        lines.append(f"- **港股接口**: {len(self.report.hk_apis)}")
        lines.append(f"- **美股接口**: {len(self.report.us_apis)}")
        lines.append(f"- **全球指数接口**: {len(self.report.global_index_apis)}")
        lines.append(f"- **期货接口**: {len(self.report.futures_apis)}")
        lines.append(f"- **外汇接口**: {len(self.report.forex_apis)}")
        lines.append(f"- **已测试API**: {len(self.report.test_results)}")

        # 实时数据接口
        lines.append("\n---\n")
        lines.append("## 🔴 实时数据接口")
        lines.append(f"\n发现 {len(self.report.realtime_apis)} 个相关接口:\n")
        for api in self.report.realtime_apis[:30]:  # 限制显示数量
            info = self.get_function_info(api)
            lines.append(f"- `{api}` - {info['doc'][:80]}")
        if len(self.report.realtime_apis) > 30:
            lines.append(f"- ... 还有 {len(self.report.realtime_apis) - 30} 个接口")

        # 港股接口
        lines.append("\n---\n")
        lines.append("## 🇭🇰 港股接口")
        lines.append(f"\n发现 {len(self.report.hk_apis)} 个相关接口:\n")
        for api in self.report.hk_apis:
            info = self.get_function_info(api)
            lines.append(f"- `{api}` - {info['doc'][:80]}")

        # 美股接口
        lines.append("\n---\n")
        lines.append("## 🇺🇸 美股接口")
        lines.append(f"\n发现 {len(self.report.us_apis)} 个相关接口:\n")
        for api in self.report.us_apis:
            info = self.get_function_info(api)
            lines.append(f"- `{api}` - {info['doc'][:80]}")

        # 全球指数接口
        lines.append("\n---\n")
        lines.append("## 🌍 全球指数接口")
        lines.append(f"\n发现 {len(self.report.global_index_apis)} 个相关接口:\n")
        for api in self.report.global_index_apis:
            info = self.get_function_info(api)
            lines.append(f"- `{api}` - {info['doc'][:80]}")

        # 期货接口
        lines.append("\n---\n")
        lines.append("## 📈 期货接口")
        lines.append(f"\n发现 {len(self.report.futures_apis)} 个相关接口:\n")
        for api in self.report.futures_apis:
            info = self.get_function_info(api)
            lines.append(f"- `{api}` - {info['doc'][:80]}")

        # 外汇接口
        lines.append("\n---\n")
        lines.append("## 💱 外汇接口")
        lines.append(f"\n发现 {len(self.report.forex_apis)} 个相关接口:\n")
        for api in self.report.forex_apis:
            info = self.get_function_info(api)
            lines.append(f"- `{api}` - {info['doc'][:80]}")

        # 测试结果
        lines.append("\n---\n")
        lines.append("## 🧪 API 测试结果")

        # 按类别分组
        by_category = defaultdict(list)
        for result in self.report.test_results:
            by_category[result.category].append(result)

        for category, results in sorted(by_category.items()):
            lines.append(f"\n### {category.upper()}")

            for r in results:
                status_icon = "✅" if r.test_status == "success" else "⚠️" if r.test_status == "skipped" else "❌"
                lines.append(f"\n#### {status_icon} `{r.name}`")
                lines.append(f"- **状态**: {r.test_status}")
                lines.append(f"- **响应时间**: {r.response_time_ms:.2f} ms")

                if r.data_shape:
                    lines.append(f"- **数据形状**: {r.data_shape}")
                if r.data_fields:
                    lines.append(f"- **数据字段**: {', '.join(r.data_fields[:10])}")
                    if len(r.data_fields) > 10:
                        lines.append(f"  - ... 还有 {len(r.data_fields) - 10} 个字段")

                if r.sample_data and r.test_status == "success":
                    lines.append("- **样例数据**:")
                    lines.append("```json")
                    lines.append(json.dumps(r.sample_data, ensure_ascii=False, indent=2, default=str)[:800])
                    lines.append("```")

                if r.error_message:
                    lines.append(f"- **错误**: {r.error_message}")
                if r.notes:
                    lines.append(f"- **备注**: {r.notes}")

        # 推荐接口
        lines.append("\n---\n")
        lines.append("## ⭐ 推荐接口")

        successful = [r for r in self.report.test_results if r.test_status == "success"]
        lines.append(f"\n以下 {len(successful)} 个接口测试成功，推荐用于实时数据获取:\n")

        for r in sorted(successful, key=lambda x: x.response_time_ms)[:20]:
            lines.append(f"- `{r.name}` ({r.category}) - {r.response_time_ms:.1f}ms")

        # 附录：所有函数列表
        lines.append("\n---\n")
        lines.append("## 📋 附录：所有函数列表")
        lines.append("\n<details>")
        lines.append(f"<summary>点击展开 ({len(self.all_functions)} 个函数)</summary>")
        lines.append("")
        lines.append("```")
        for func in self.all_functions:
            lines.append(func)
        lines.append("```")
        lines.append("</details>")

        return "\n".join(lines)

    def save_report(self, content: str):
        """保存报告到文件"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Markdown报告
        md_path = self.output_dir / f"akshare_research_report_{timestamp}.md"
        md_path.write_text(content, encoding="utf-8")
        print(f"\n📝 Markdown报告已保存: {md_path}")

        # JSON数据
        json_data = {
            "timestamp": self.report.timestamp,
            "total_functions": self.report.total_functions,
            "realtime_apis": self.report.realtime_apis,
            "hk_apis": self.report.hk_apis,
            "us_apis": self.report.us_apis,
            "global_index_apis": self.report.global_index_apis,
            "futures_apis": self.report.futures_apis,
            "forex_apis": self.report.forex_apis,
            "test_results": [asdict(r) for r in self.report.test_results],
        }

        json_path = self.output_dir / f"akshare_research_data_{timestamp}.json"
        json_path.write_text(json.dumps(json_data, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        print(f"📝 JSON数据已保存: {json_path}")

        return md_path, json_path

    def run(self):
        """运行完整的研究流程"""
        print("=" * 60)
        print("🔬 Akshare 实时数据接口研究")
        print("=" * 60)

        # 1. 列出所有函数
        self.list_all_functions()

        # 2. 分类接口
        self.categorize_apis()

        # 3. 测试API
        self.test_apis(max_tests_per_category=10)

        # 4. 生成报告
        print("\n📄 正在生成报告...")
        report_content = self.generate_markdown_report()

        # 5. 保存报告
        md_path, json_path = self.save_report(report_content)

        # 6. 输出到控制台
        print("\n" + "=" * 60)
        print("📊 报告摘要")
        print("=" * 60)
        print(f"总函数数量: {self.report.total_functions}")
        print(f"实时数据接口: {len(self.report.realtime_apis)}")
        print(f"港股接口: {len(self.report.hk_apis)}")
        print(f"美股接口: {len(self.report.us_apis)}")
        print(f"全球指数接口: {len(self.report.global_index_apis)}")
        print(f"期货接口: {len(self.report.futures_apis)}")
        print(f"外汇接口: {len(self.report.forex_apis)}")
        print(f"已测试API: {len(self.report.test_results)}")

        success_count = sum(1 for r in self.report.test_results if r.test_status == "success")
        print(f"测试成功: {success_count}")
        print(f"测试失败: {len(self.report.test_results) - success_count}")

        print("\n" + "=" * 60)
        print("✅ 研究完成!")
        print(f"📁 报告文件: {md_path}")
        print(f"📁 数据文件: {json_path}")
        print("=" * 60)

        return self.report


def main():
    """主函数"""
    researcher = AkshareResearcher()
    researcher.run()


if __name__ == "__main__":
    main()
