"""基金类型推断模块

提供基金类型推断和判断功能。
"""

import logging

logger = logging.getLogger(__name__)


def _get_fund_type_from_fund_name_em(fund_code: str) -> str | None:
    """
    从 akshare fund_name_em API 获取基金类型

    该 API 返回完整的基金类型字符串，包含子类型信息。
    例如："指数型-股票"、"股票型"、"混合型-偏股" 等。

    Args:
        fund_code: 基金代码

    Returns:
        基金类型字符串（含子类型后缀），获取失败返回 None
    """
    try:
        import akshare as ak

        df = ak.fund_name_em()
        if df is None or df.empty:
            return None

        # 查找对应基金代码的记录
        if "基金代码" not in df.columns or "基金类型" not in df.columns:
            logger.debug(f"fund_name_em 返回数据格式不正确: {df.columns.tolist()}")
            return None

        fund_rows = df[df["基金代码"] == fund_code]
        if fund_rows.empty:
            return None

        fund_type = str(fund_rows.iloc[0].get("基金类型", "")).strip()
        if fund_type and fund_type != "nan":
            logger.debug(f"从 fund_name_em 获取基金类型: {fund_code} -> {fund_type}")
            return fund_type

        return None
    except Exception as e:
        logger.debug(f"fund_name_em 获取基金类型失败: {fund_code}, error: {e}")
        return None


def _infer_fund_type_from_name(fund_name: str) -> str:
    """
    从基金名称推断基金类型

    Args:
        fund_name: 基金名称

    Returns:
        基金类型字符串
    """
    if not fund_name:
        return ""

    name = fund_name.upper()

    # 根据名称中的关键词推断类型
    if "QDII" in name:
        return "QDII"
    if "FOF" in name:
        return "FOF"
    if "ETF" in name and "联接" in name:
        return "ETF-联接"
    if "ETF" in name:
        return "ETF"
    if "LOF" in name:
        return "LOF"
    if "货币" in name:
        return "货币型"
    if "债券" in name:
        return "债券型"
    if "混合" in name:
        return "混合型"
    # 指数型基金单独处理，保持与 akshare 返回格式一致
    if "指数" in name:
        return "指数型"
    if "股票" in name:
        return "股票型"

    return ""


def _has_real_time_estimate(fund_type: str, fund_name: str) -> bool:
    """
    判断基金是否有实时估值

    规则：
    - QDII 基金：无实时估值（投资海外市场，净值更新延迟）
    - FOF 基金投资海外基金（QDII-FOF）：无实时估值
    - 其他 FOF、ETF-联接基金：有实时估值（底层资产是国内基金）
    - 普通基金：有实时估值
    - 类型未知时：从名称推断，仍无法判断时保守返回 True

    Args:
        fund_type: 基金类型
        fund_name: 基金名称

    Returns:
        bool: 是否有实时估值
    """
    # 类型为空时，尝试从名称推断
    effective_type = fund_type
    if not effective_type and fund_name:
        effective_type = _infer_fund_type_from_name(fund_name)

    # 仍无法判断类型时，保守返回 True（大多数基金有实时估值）
    if not effective_type:
        return True

    # QDII 基金无实时估值（包括 QDII-商品、QDII-股票等子类型）
    if effective_type.startswith("QDII"):
        return False

    # FOF 基金需要进一步判断是否投资海外
    if effective_type == "FOF":
        name_upper = (fund_name or "").upper()
        # QDII-FOF 或投资海外的 FOF 无实时估值
        if "QDII" in name_upper or "海外" in name_upper or "全球" in name_upper:
            return False
        return True

    # 其他类型有实时估值
    return True
