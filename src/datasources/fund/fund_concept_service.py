"""基金概念标签服务

通过基金重仓股所属概念板块，推断基金的概念/主题标签（如 CPO、AI芯片、商业航天等）。

数据流：
1. 异步构建股票→概念板块全量映射缓存（遍历所有概念板块）
2. 基金概念 = 重仓股概念 × 持仓权重加权聚合
3. 结果缓存到 fund_concept_tags 表
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Any

from src.datasources.akshare_config import call_akshare_with_retry
from src.db.database import DatabaseManager
from src.db.fund.stock_concept_dao import FundConceptTagsDAO, StockConceptDAO

logger = logging.getLogger(__name__)

# 股票→概念缓存有效期（秒）：概念板块变更不频繁，24h 刷新一次
STOCK_CONCEPT_CACHE_TTL = 24 * 3600

# 持仓中取前 N 只重仓股用于推断
TOP_HOLDINGS_N = 10

# 返回的概念标签数量
TOP_TAGS_N = 5


def _get_stock_concept_dao() -> StockConceptDAO:
    return StockConceptDAO(DatabaseManager())


def _get_fund_concept_dao() -> FundConceptTagsDAO:
    return FundConceptTagsDAO(DatabaseManager())


async def ensure_stock_concept_cache() -> bool:
    """确保股票→概念缓存存在且有效

    Returns:
        True 表示缓存已就绪，False 表示构建失败
    """
    dao = _get_stock_concept_dao()
    count = dao.count()

    # 第一次构建或缓存为空
    if count == 0:
        logger.info("股票→概念缓存为空，开始后台构建...")
        return await _build_stock_concept_cache()

    return True


async def _build_stock_concept_cache() -> bool:
    """遍历所有概念板块，构建股票→概念映射缓存"""
    import akshare as ak

    dao = _get_stock_concept_dao()
    dao.clear()

    try:
        # 1. 获取所有概念板块列表
        boards = await call_akshare_with_retry(
            ak.stock_board_concept_name_em,
            rate_limit_cps=3,
        )
        if boards is None or boards.empty:
            logger.warning("获取概念板块列表失败")
            return False

        names = boards["板块名称"].tolist()
        logger.info(f"共 {len(names)} 个概念板块，开始构建缓存...")

        # 2. 遍历每个板块，获取成分股
        total_mappings = 0
        for i, name in enumerate(names):
            try:
                cons = await call_akshare_with_retry(
                    ak.stock_board_concept_cons_em,
                    symbol=name,
                    rate_limit_cps=3,
                )
                if cons is not None and not cons.empty:
                    mappings = [(str(code), name) for code in cons["代码"].tolist()]
                    dao.save_batch(mappings)
                    total_mappings += len(mappings)
            except Exception as e:
                logger.debug(f"获取板块[{name}]成分股失败: {e}")
                continue

            if (i + 1) % 50 == 0:
                logger.info(f"概念板块缓存进度: {i + 1}/{len(names)}，已缓存 {total_mappings} 条映射")

        logger.info(f"概念板块缓存完成: 共 {len(names)} 个板块, {dao.count()} 条映射")
        return True

    except Exception as e:
        logger.error(f"构建股票→概念缓存失败: {e}")
        return False


async def _get_fund_holdings(fund_code: str) -> list[dict[str, Any]] | None:
    """获取基金重仓股列表

    Returns:
        [{"stock_code": "300502", "stock_name": "新易盛", "proportion": 8.5}, ...]
        失败返回 None
    """
    import akshare as ak

    current_year = str(datetime.now().year)
    try:
        df = await call_akshare_with_retry(
            ak.fund_portfolio_hold_em,
            symbol=fund_code,
            date=current_year,
            rate_limit_cps=3,
        )
        if df is None or df.empty:
            return None

        # 取最新报告期
        if "季度" in df.columns:
            periods = df["季度"].unique()
            sorted_periods = sorted(periods, reverse=True)
            latest = sorted_periods[0]
            df = df[df["季度"] == latest]

        # 降序排列取前 N
        if "占净值比例" in df.columns:
            df = df.sort_values("占净值比例", ascending=False)

        holdings = []
        for _, row in df.head(TOP_HOLDINGS_N).iterrows():
            holdings.append({
                "stock_code": str(row.get("股票代码", "")),
                "stock_name": str(row.get("股票名称", "")),
                "proportion": float(row.get("占净值比例", 0) or 0),
            })

        return holdings
    except Exception as e:
        logger.debug(f"获取基金 {fund_code} 重仓股失败: {e}")
        return None


async def compute_fund_concept_tags(fund_code: str) -> list[str]:
    """计算基金概念标签

    通过重仓股所属概念板块，按持仓权重加权聚合，返回 Top N 标签。

    Args:
        fund_code: 基金代码

    Returns:
        概念标签列表，如 ["CPO概念", "光通信", "5G"]
    """
    stock_concept_dao = _get_stock_concept_dao()
    fund_concept_dao = _get_fund_concept_dao()

    # 1. 获取重仓股
    holdings = await _get_fund_holdings(fund_code)
    if not holdings:
        return []

    # 2. 查每只重仓股的概念标签，加权聚合
    concept_weight: dict[str, float] = {}

    for h in holdings:
        concepts = stock_concept_dao.get_stock_concepts(h["stock_code"])
        weight = h["proportion"]
        for c in concepts:
            concept_weight[c] = concept_weight.get(c, 0) + weight

    if not concept_weight:
        return []

    # 3. 按总权重降序排列，取 Top N
    sorted_concepts = sorted(concept_weight.items(), key=lambda x: -x[1])
    top_tags = [name for name, _w in sorted_concepts[:TOP_TAGS_N]]

    # 4. 缓存结果
    if top_tags:
        report_period = holdings[0].get("report_period", "")
        fund_concept_dao.save(fund_code, top_tags, report_period)

    return top_tags


def get_cached_fund_concept_tags(fund_code: str) -> list[str] | None:
    """获取缓存的基金概念标签（无网络请求）

    Returns:
        标签列表，无缓存返回 None
    """
    return _get_fund_concept_dao().get(fund_code)


async def refresh_all_fund_concept_tags(fund_codes: list[str]) -> None:
    """批量刷新基金概念标签（后台任务）

    1. 先确保股票→概念缓存存在
    2. 逐只基金计算概念标签

    Args:
        fund_codes: 基金代码列表
    """
    # 1. 确保障缓存就绪
    cache_ready = await ensure_stock_concept_cache()
    if not cache_ready:
        logger.warning("股票→概念缓存不可用，跳过概念标签刷新")
        return

    # 2. 逐只基金计算
    for code in fund_codes:
        try:
            await compute_fund_concept_tags(code)
        except Exception as e:
            logger.debug(f"计算基金 {code} 概念标签失败: {e}")


async def get_fund_concept_tags(fund_code: str) -> list[str]:
    """获取基金概念标签（优先读取缓存）

    缓存命中直接返回；否则异步触发计算并返回空列表。

    Args:
        fund_code: 基金代码

    Returns:
        概念标签列表
    """
    cached = get_cached_fund_concept_tags(fund_code)
    if cached is not None:
        return cached

    # 无缓存，异步触发计算
    import asyncio

    asyncio.ensure_future(compute_fund_concept_tags(fund_code))
    return []
