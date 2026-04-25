"""基金数据源基类模块

提供 FundDataSourceBase 基类，供所有基金数据源继承。
包含共用的基金代码验证、安全类型转换等方法。
"""

import re
from typing import Any

from ..base import DataSource, DataSourceType


class FundDataSourceBase(DataSource):
    """基金数据源基类

    提供基金数据源的共用方法，包括：
    - 基金代码格式验证
    - 安全类型转换
    - 缓存策略骨架
    """

    def __init__(self, name: str, source_type: DataSourceType, timeout: float = 10.0):
        """
        初始化基金数据源基类

        Args:
            name: 数据源名称
            source_type: 数据源类型
            timeout: 请求超时时间(秒)
        """
        super().__init__(name=name, source_type=source_type, timeout=timeout)

    def _validate_fund_code(self, fund_code: str) -> bool:
        """
        验证基金代码格式（6位数字）

        Args:
            fund_code: 基金代码

        Returns:
            bool: 是否有效
        """
        return bool(re.match(r"^\d{6}$", str(fund_code)))

    def _safe_float(self, value: Any) -> float | None:
        """
        安全转换为浮点数

        Args:
            value: 待转换的值

        Returns:
            float | None: 转换后的值，失败返回 None
        """
        if value is None:
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
