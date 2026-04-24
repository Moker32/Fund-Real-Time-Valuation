"""基金行业配置服务

从 akshare 获取基金行业配置数据并缓存到数据库。
行业配置数据按季度更新，缓存周期可较长。
"""

import logging
from datetime import datetime, timedelta
from typing import Any

from src.db.database import DatabaseManager
from src.db.fund.fund_industry_dao import FundIndustryDAO

logger = logging.getLogger(__name__)

# 缓存有效期（秒）：行业配置按季度更新，7天刷新一次足够
CACHE_TTL_SECONDS = 7 * 24 * 3600


def _get_industry_dao() -> FundIndustryDAO:
    """获取行业配置 DAO 单例"""
    return FundIndustryDAO(DatabaseManager())


def save_fund_sector(fund_code: str, sector: str, source: str = "") -> None:
    """保存基金板块标签到数据库"""
    from datetime import datetime
    with DatabaseManager().get_connection() as conn:
        conn.execute(
            """INSERT OR REPLACE INTO fund_sector (fund_code, sector, source, updated_at)
               VALUES (?, ?, ?, ?)""",
            (fund_code, sector, source, datetime.now().isoformat()),
        )


def get_fund_sector(fund_code: str) -> str | None:
    """从数据库读取基金板块标签"""
    with DatabaseManager().get_connection() as conn:
        row = conn.execute(
            "SELECT sector FROM fund_sector WHERE fund_code = ?", (fund_code,)
        ).fetchone()
        return row[0] if row else None


async def fetch_fund_industries(fund_code: str) -> list[dict[str, Any]] | None:
    """从 akshare 获取基金行业配置数据

    Args:
        fund_code: 基金代码

    Returns:
        行业配置列表，如 [{"industry_name": "制造业", "proportion": 57.32}, ...]
        失败返回 None
    """
    from src.datasources.akshare_config import call_akshare_with_retry

    try:
        import akshare as ak

        # 用当前年份获取最新的行业配置数据
        current_year = str(datetime.now().year)
        df = await call_akshare_with_retry(
            ak.fund_portfolio_industry_allocation_em,
            symbol=fund_code,
            date=current_year,
        )

        if df is None or df.empty:
            logger.debug(f"基金 {fund_code} 无行业配置数据")
            return None

        # 获取最新的报告期（数据可能包含多个季度）
        # 降序排序，取最新报告期
        report_dates = df["截止时间"].unique()
        sorted_dates = sorted(report_dates, reverse=True)
        latest_date = sorted_dates[0] if sorted_dates else None

        if not latest_date:
            return None

        # 筛选最新报告期的数据
        latest_data = df[df["截止时间"] == latest_date]
        # 只保留占净值比例 > 0 的行业
        latest_data = latest_data[latest_data["占净值比例"] > 0]

        industries = []
        for _, row in latest_data.iterrows():
            industries.append({
                "industry_name": row["行业类别"],
                "proportion": float(row["占净值比例"]),
            })

        # 保存到数据库
        dao = _get_industry_dao()
        dao.save_batch(fund_code, industries, latest_date)

        return industries

    except Exception as e:
        logger.warning(f"获取基金行业配置失败: {fund_code} - {e}")
        return None


async def get_fund_industries(fund_code: str) -> list[dict[str, Any]] | None:
    """获取基金行业配置数据（带缓存）

    优先从数据库读取，缓存过期时从 akshare 获取并更新。

    Args:
        fund_code: 基金代码

    Returns:
        行业配置列表，无数据返回 None
    """
    dao = _get_industry_dao()

    # 检查缓存是否有效
    latest_date = dao.get_latest_report_date(fund_code)
    if latest_date:
        records = dao.get_latest(fund_code, limit=5)
        if records:
            # 检查缓存是否过期
            fetched_at = records[0].fetched_at
            if fetched_at:
                try:
                    fetched_time = datetime.fromisoformat(fetched_at)
                    if datetime.now() - fetched_time < timedelta(seconds=CACHE_TTL_SECONDS):
                        return [
                            {
                                "industry_name": r.industry_name,
                                "proportion": r.proportion,
                            }
                            for r in records
                        ]
                except ValueError:
                    pass

    # 缓存过期或不存在，从 akshare 重新获取
    return await fetch_fund_industries(fund_code)


async def get_fund_theme(fund_code: str) -> str | None:
    """获取基金投资主题

    优先级：
    1. 指数基金从跟踪标的名称提取（如 "中证白酒指数" -> "白酒"）
    2. 从行业配置 top 1 推断

    Args:
        fund_code: 基金代码

    Returns:
        投资主题字符串，无法确定返回 None
    """
    from src.datasources.akshare_config import call_akshare_with_retry

    # 1. 从跟踪标的提取（指数基金）
    try:
        import akshare as ak

        overview = await call_akshare_with_retry(
            ak.fund_overview_em, symbol=fund_code
        )
        if overview is not None and not overview.empty:
            track_target = str(overview.iloc[0].get("跟踪标的", "")).strip()
            if track_target and track_target != "该基金无跟踪标的":
                # 取跟踪标的简化名，如 "中证白酒指数" -> "白酒"
                # 去掉常见前缀和后缀
                for prefix in ["中证", "上证", "国证", "深证", "沪深"]:
                    if track_target.startswith(prefix):
                        track_target = track_target[len(prefix):]
                        break
                for suffix in ["指数", "ETF", "LOF"]:
                    if suffix in track_target:
                        track_target = track_target.split(suffix)[0].strip()
                if track_target:
                    return track_target
    except Exception as e:
        logger.debug(f"获取跟踪标的失败: {fund_code} - {e}")

    # 2. 从行业配置推断（取占比最高且非制造业的行业）
    industries = await get_fund_industries(fund_code)
    if industries:
        for ind in industries:
            name = ind["industry_name"]
            if name not in ("制造业",):
                short_map: dict[str, str] = {
                    "信息传输、软件和信息技术服务业": "信息技术",
                }
                return short_map.get(name, name)

    return None
