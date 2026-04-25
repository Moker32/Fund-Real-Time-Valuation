"""基金信息数据库操作模块

提供基金基本信息的数据库读写功能。
"""

import logging
from typing import Any

from .fund_cache_helpers import get_basic_info_dao

logger = logging.getLogger(__name__)


def get_basic_info_db(fund_code: str) -> dict[str, Any] | None:
    """
    从数据库读取基金基本信息

    Args:
        fund_code: 基金代码

    Returns:
        基金基本信息字典，如果不存在返回 None
    """
    dao = get_basic_info_dao()
    info = dao.get(fund_code)
    if info:
        return {
            "code": info.code,
            "name": info.name,
            "short_name": info.short_name,
            "type": info.type,
            "fund_key": info.fund_key,
            "net_value": info.net_value,
            "net_value_date": info.net_value_date,
            "establishment_date": info.establishment_date,
            "manager": info.manager,
            "custodian": info.custodian,
            "fund_scale": info.fund_scale,
            "scale_date": info.scale_date,
            "risk_level": info.risk_level,
            "full_name": info.full_name,
        }
    return None


def save_basic_info_to_db(fund_code: str, info: dict[str, Any]) -> bool:
    """
    保存基金基本信息到数据库

    Args:
        fund_code: 基金代码
        info: 基金信息字典

    Returns:
        是否保存成功
    """
    dao = get_basic_info_dao()
    return dao.save_from_dict(fund_code, info)


def get_full_fund_info(fund_code: str) -> dict[str, Any] | None:
    """
    获取完整基金信息（从 akshare 获取更多字段）

    Args:
        fund_code: 基金代码

    Returns:
        包含完整基金信息的字典，失败返回 None
    """
    try:
        import akshare as ak

        info_dict: dict[str, Any] = {}

        # 1. 获取基金简称和全称
        try:
            daily_df = ak.fund_open_fund_daily_em()
            if "基金代码" in daily_df.columns:
                name_rows = daily_df[daily_df["基金代码"] == fund_code]
                if not name_rows.empty:
                    info_dict["short_name"] = str(name_rows.iloc[0].get("基金简称", ""))
                    info_dict["name"] = info_dict["short_name"]
        except Exception as e:
            logger.debug(f"获取基金简称失败: {fund_code}, error: {e}")

        # 2. 获取基金详细信息
        try:
            info_df = ak.fund_individual_basic_info_xq(symbol=fund_code)
            if info_df is not None and not info_df.empty:
                # 遍历所有字段
                for _, row in info_df.iterrows():
                    item = str(row.get("item", ""))
                    value = str(row.get("value", ""))

                    if "基金全称" in item:
                        info_dict["full_name"] = value
                    elif "基金简称" in item:
                        info_dict["short_name"] = value
                    elif "基金类型" in item:
                        # 保留完整的 akshare 格式：主类型-子类型
                        info_dict["type"] = value
                    elif "基金管理人" in item:
                        info_dict["manager"] = value
                    elif "基金托管人" in item:
                        info_dict["custodian"] = value
                    elif "成立日期" in item:
                        info_dict["establishment_date"] = value
                    elif "风险等级" in item:
                        info_dict["risk_level"] = value
        except Exception as e:
            logger.debug(f"获取基金详细信息失败: {fund_code}, error: {e}")

        # 3. 获取基金规模和净值信息
        try:
            fund_info = ak.fund_info_fund_code_em(fund_code=fund_code)
            if fund_info is not None:
                info_dict["fund_scale"] = fund_info.get("基金规模")
                info_dict["scale_date"] = fund_info.get("规模日期", "")
        except Exception as e:
            logger.debug(f"获取基金规模信息失败: {fund_code}, error: {e}")

        # 设置默认值
        info_dict.setdefault("short_name", "")
        info_dict.setdefault("name", "")
        info_dict.setdefault("full_name", "")
        info_dict.setdefault("type", "")
        info_dict.setdefault("manager", "")
        info_dict.setdefault("custodian", "")
        info_dict.setdefault("establishment_date", "")
        info_dict.setdefault("risk_level", "")
        info_dict.setdefault("fund_scale", None)
        info_dict.setdefault("scale_date", "")

        # 保存到数据库
        save_basic_info_to_db(fund_code, info_dict)

        return info_dict

    except Exception as e:
        logger.warning(f"获取完整基金信息失败: {fund_code}, error: {e}")
        return None
