"""基金信息工具模块

包含基金信息获取、类型推断、缓存管理等工具函数。

此模块现在主要作为重导出层，实际功能已拆分到：
- fund_info_db: 数据库读写
- fund_type_inference: 类型推断
- fund_trading_helpers: 交易日辅助
"""

import logging
import time
from typing import Any

from .fund_cache_helpers import (
    _fund_info_cache,
    _fund_info_cache_ttl,
    _fund_info_hit_count,
    _fund_info_miss_count,
    get_fund_cache,
)

# 从各子模块导入，保持向后兼容
from .fund_info_db import (
    get_basic_info_db,
    get_full_fund_info,
    save_basic_info_to_db,
)
from .fund_trading_helpers import (
    _get_china_market_date,
    _get_latest_trading_day,
    _get_net_value_date_from_akshare,
    _get_trading_calendar,
    _is_after_market_close,
    _is_net_value_cache_valid,
    _update_net_value_cache,
)
from .fund_type_inference import (
    _get_fund_type_from_fund_name_em,
    _has_real_time_estimate,
    _infer_fund_type_from_name,
)

logger = logging.getLogger(__name__)


def get_fund_basic_info(fund_code: str) -> tuple[str, str] | None:
    """
    获取基金基本信息（名称和类型），使用全局缓存和数据库

    优先从数据库读取，如果不存在或类型为空则从 akshare 获取并保存到数据库

    Args:
        fund_code: 基金代码

    Returns:
        (name, type) 或 None（如果获取失败）
    """
    global _fund_info_cache, _fund_info_hit_count, _fund_info_miss_count
    now = time.time()

    # 1. 检查内存缓存
    if fund_code in _fund_info_cache:
        info, timestamp = _fund_info_cache[fund_code]
        if now - timestamp < _fund_info_cache_ttl:
            _fund_info_hit_count += 1
            return info

    # 2. 尝试从数据库读取
    db_info = get_basic_info_db(fund_code)
    if db_info:
        name = db_info.get("short_name", "") or ""
        fund_type = db_info.get("type", "") or ""
        # 只有当类型不为空时才使用缓存，否则需要重新获取
        if fund_type:
            result = (name, fund_type)
            _fund_info_cache[fund_code] = (result, now)
            _fund_info_hit_count += 1
            return result
        # 类型为空，需要从 akshare 重新获取
        _fund_info_miss_count += 1
    else:
        _fund_info_miss_count += 1

    # 3. 从 akshare 获取
    try:
        import akshare as ak

        # 获取基金简称
        fund_name = ""
        try:
            daily_df = ak.fund_open_fund_daily_em()
            if "基金代码" in daily_df.columns:
                name_rows = daily_df[daily_df["基金代码"] == fund_code]
                if not name_rows.empty:
                    fund_name = str(name_rows.iloc[0].get("基金简称", ""))
        except Exception as e:
            logger.debug(f"获取基金简称失败: {fund_code}, error: {e}")

        # 获取基金类型（保留完整的 akshare 格式：主类型-子类型）
        # 优先级：fund_individual_basic_info_xq > fund_name_em > 名称推断
        fund_type = ""

        # 方案1: fund_individual_basic_info_xq (最精确)
        try:
            info_df = ak.fund_individual_basic_info_xq(symbol=fund_code)
            if info_df is not None and not info_df.empty:
                type_row = info_df[info_df["item"] == "基金类型"]
                if not type_row.empty:
                    fund_type = str(type_row.iloc[0]["value"]).strip()
                    # 保留完整格式，如 "QDII-商品"、"股票型-增强指数"、"指数型-股票"
        except Exception as e:
            logger.debug(f"获取基金类型失败: {fund_code}, error: {e}")

        # 方案2: fund_name_em (备用，保留子类型)
        if not fund_type:
            fund_type = _get_fund_type_from_fund_name_em(fund_code) or ""

        # 方案3: 从基金名称中识别类型（最后回退）
        if not fund_type and fund_name:
            fund_type = _infer_fund_type_from_name(fund_name)

        result = (fund_name, fund_type)
        _fund_info_cache[fund_code] = (result, now)

        # 保存到数据库
        if fund_name or fund_type:
            save_basic_info_to_db(
                fund_code,
                {
                    "short_name": fund_name,
                    "name": fund_name,
                    "type": fund_type,
                },
            )

        return result

    except Exception as e:
        logger.warning(f"获取基金基本信息失败: {fund_code}, error: {e}")
        return None


def get_fund_cache_stats() -> dict[str, Any]:
    """
    获取基金缓存统计信息

    Returns:
        dict: 包含 fund_cache 和 fund_info_cache 的统计信息
    """
    global _fund_info_hit_count, _fund_info_miss_count

    # 获取基金信息缓存统计
    info_total = _fund_info_hit_count + _fund_info_miss_count
    info_hit_rate = _fund_info_hit_count / info_total if info_total > 0 else 0.0

    # 获取基金数据缓存统计
    fund_cache = get_fund_cache()
    fund_cache_stats = fund_cache.get_stats() if fund_cache else {}

    return {
        "fund_cache": fund_cache_stats,
        "fund_info_cache": {
            "hit_count": _fund_info_hit_count,
            "miss_count": _fund_info_miss_count,
            "hit_rate": round(info_hit_rate, 4),
            "total_requests": info_total,
            "cached_items": len(_fund_info_cache),
            "ttl_seconds": _fund_info_cache_ttl,
        },
    }
