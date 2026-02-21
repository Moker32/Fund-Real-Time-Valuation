# -*- coding: UTF-8 -*-
"""数据导出模块

提供基金和持仓数据导出到 CSV 文件的功能。
使用标准库 csv 模块，无需额外依赖。
支持 dataclass 对象或字典格式输入。
"""

import csv
from pathlib import Path


def _get_value(obj: dict | object, key: str, default: str = "") -> str:
    """获取对象或字典的值

    Args:
        obj: 对象或字典
        key: 属性名或键名
        default: 默认值

    Returns:
        str: 属性的字符串值
    """
    if isinstance(obj, dict):
        return str(obj.get(key, default))
    else:
        return str(getattr(obj, key, default))


def _get_float(obj: dict | object, key: str, default: float = 0.0) -> float:
    """获取对象或字典的浮点数值

    Args:
        obj: 对象或字典
        key: 属性名或键名
        default: 默认值

    Returns:
        float: 属性的浮点数值
    """
    if isinstance(obj, dict):
        return float(obj.get(key, default))
    else:
        return float(getattr(obj, key, default))


def export_funds_to_csv(funds: list[dict | object], filepath: str | Path) -> bool:
    """导出基金列表到 CSV 文件

    Args:
        funds: 基金对象或字典列表，每个元素应包含 'code' 和 'name' 属性/键
        filepath: 输出文件路径

    Returns:
        bool: 导出成功返回 True，失败返回 False
    """
    try:
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)

        with open(filepath, "w", encoding="utf-8-sig", newline="") as f:
            fieldnames = ["code", "name"]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for fund in funds:
                writer.writerow(
                    {
                        "code": _get_value(fund, "code"),
                        "name": _get_value(fund, "name"),
                    }
                )

        return True
    except Exception:
        return False
