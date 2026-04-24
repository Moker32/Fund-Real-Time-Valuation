"""基金概念标签服务

通过基金重仓股所属概念板块，推断基金的概念/主题标签（如 CPO、AI芯片、商业航天等）。

数据流：
1. 异步构建股票→概念板块全量映射缓存（遍历所有概念板块）
2. 基金概念 = 重仓股概念 × 持仓权重加权聚合
3. 结果缓存到 fund_concept_tags 表
"""

import logging
from datetime import datetime
from typing import Any

from src.datasources.akshare_config import call_akshare_with_retry
from src.db.database import DatabaseManager
from src.db.fund.stock_concept_dao import FundConceptTagsDAO, StockConceptDAO

logger = logging.getLogger(__name__)

# 不展示的通用概念词（财务/交易类，非主题性标签）
_NON_THEMATIC_CONCEPTS: set[str] = {
    "基金重仓", "社保重仓", "QFII重仓", "保险重仓",
    "券商重仓", "信托重仓",
    "融资融券", "股权激励", "本月解禁", "即将解禁",
    "整体上市", "业绩预升", "业绩预降",
    "近期复牌", "昨日振荡", "密集调研", "最近异动",
    "高管增持", "定增股", "配股预案",
    "含H股", "含B股", "IPO受益",
    "参股金融", "金融参股", "参股新股", "参股券商",
    "参股银行", "参股保险",
    "黄河三角", "皖江区域", "成渝特区", "长株潭",
    "珠三角", "长三角", "海峡西岸", "前海概念", "环渤海",
    "奢侈品", "超大盘", "分拆上市",
}

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
    """遍历概念板块，构建股票→概念映射缓存

    优先使用 Sina 数据源（stock_sector_spot），
    Sina 不可用时回退到 EastMoney（stock_board_concept_name_em）。
    """
    import akshare as ak

    dao = _get_stock_concept_dao()
    dao.clear()

    # Step 1: 获取概念板块列表（Sina，175个板块）
    try:
        spot = await call_akshare_with_retry(
            ak.stock_sector_spot, indicator="概念", rate_limit_cps=3
        )
        if spot is None or spot.empty:
            raise ValueError("Sina 概念板块为空")
        board_names = spot["板块"].tolist()
        board_labels = spot["label"].tolist()
        source_name = "sina"
        logger.info(
            f"[Sina] 获取 {len(board_names)} 个概念板块，开始构建缓存..."
        )
    except Exception as e:
        logger.warning(f"Sina 概念板块获取失败({e})，尝试 EastMoney 回退...")
        try:
            boards = await call_akshare_with_retry(
                ak.stock_board_concept_name_em, rate_limit_cps=3
            )
            if boards is None or boards.empty:
                logger.error("EastMoney 概念板块也为空")
                return False
            board_names = boards["板块名称"].tolist()
            board_labels = board_names  # EM 直接用名称查询
            source_name = "eastmoney"
            logger.info(
                f"[EastMoney] 获取 {len(board_names)} 个概念板块，开始构建缓存..."
            )
        except Exception as e2:
            logger.error(f"所有数据源均失败: {e2}")
            return False

    # Step 2: 遍历每个板块，获取成分股
    total_mappings = 0
    for i, name in enumerate(board_names):
        label = board_labels[i]
        try:
            if source_name == "sina":
                cons = await call_akshare_with_retry(
                    ak.stock_sector_detail, sector=label, rate_limit_cps=3
                )
                if cons is not None and not cons.empty:
                    mappings = [
                        (str(code).strip(), name)
                        for code in cons["code"].tolist()
                    ]
                    dao.save_batch(mappings)
                    total_mappings += len(mappings)
            else:
                cons = await call_akshare_with_retry(
                    ak.stock_board_concept_cons_em, symbol=name, rate_limit_cps=3
                )
                if cons is not None and not cons.empty:
                    mappings = [(str(code), name) for code in cons["代码"].tolist()]
                    dao.save_batch(mappings)
                    total_mappings += len(mappings)
        except Exception as e:
            logger.debug(f"获取板块[{name}]成分股失败: {e}")
            continue

        if (i + 1) % 50 == 0:
            logger.info(
                f"概念板块缓存进度: {i + 1}/{len(board_names)}，"
                f"已缓存 {total_mappings} 条映射"
            )

    logger.info(
        f"概念板块缓存完成: 来源={source_name}, "
        f"{len(board_names)} 个板块, {dao.count()} 条映射"
    )
    return True


def _find_underlying_etf(fund_code: str) -> str | None:
    """查找 ETF联接基金 对应的场内ETF代码

    策略：从 fund_basic_info 匹配去掉"联接"后缀的基金简称，
    找场内ETF（代码以 51/56/58/15/16 开头）。
    """
    try:
        with DatabaseManager().get_connection() as conn:
            row = conn.execute(
                "SELECT short_name FROM fund_basic_info WHERE code = ?",
                (fund_code,),
            ).fetchone()
            if not row:
                return None
            fund_name: str = row[0] or ""

        if "ETF联接" not in fund_name and "联接" not in fund_name:
            return None

        # 去掉"联接"、后缀A/C等，取核心名称
        base = fund_name.replace("联接", "").replace("ETF", "ETF")
        for suffix in ("A", "C", "E", "I"):
            if base.endswith(suffix):
                base = base[:-1]
                break

        if not base:
            return None

        core = base[:8]
        etf_prefixes = ("15", "16", "51", "56", "58")
        with DatabaseManager().get_connection() as conn:
            rows = conn.execute(
                "SELECT code FROM fund_basic_info WHERE name LIKE ?",
                (f"%{core}%",),
            ).fetchall()
            for r in rows:
                code = str(r[0])
                if code.startswith(etf_prefixes) and len(code) == 6:
                    return code
        return None
    except Exception as e:
        logger.debug(f"查找场内ETF失败: {fund_code} - {e}")
        return None


async def _get_fund_holdings(fund_code: str) -> list[dict[str, Any]] | None:
    """获取基金重仓股列表

    对于 ETF联接基金，自动查找对应场内ETF代码再获取持仓。

    Returns:
        [{"stock_code": "300502", "stock_name": "新易盛", "proportion": 8.5}, ...]
        失败返回 None
    """
    import akshare as ak

    async def _fetch_holdings(code: str) -> list[dict[str, Any]] | None:
        current_year = str(datetime.now().year)
        for year in (current_year, "2024", "2023"):
            try:
                df = await call_akshare_with_retry(
                    ak.fund_portfolio_hold_em,
                    symbol=code,
                    date=year,
                    rate_limit_cps=3,
                )
                if df is not None and len(df) > 0:
                    # 取最新报告期
                    if "季度" in df.columns:
                        periods = df["季度"].unique()
                        latest = sorted(periods, reverse=True)[0]
                        df = df[df["季度"] == latest]

                    # 降序排列取前 N
                    if "占净值比例" in df.columns:
                        df = df.sort_values("占净值比例", ascending=False)

                    holdings = []
                    for _, row in df.head(TOP_HOLDINGS_N).iterrows():
                        prop = float(row.get("占净值比例", 0) or 0)
                        if prop > 0:
                            holdings.append({
                                "stock_code": str(row.get("股票代码", "")),
                                "stock_name": str(row.get("股票名称", "")),
                                "proportion": prop,
                            })
                    if holdings:
                        return holdings
            except Exception:
                continue
        return None

    # 1. 直接用基金代码查
    holdings = await _fetch_holdings(fund_code)
    if holdings:
        return holdings

    # 2. 查找对应场内ETF代码
    etf_code = _find_underlying_etf(fund_code)
    if etf_code:
        logger.debug(f"基金 {fund_code} 无持仓，尝试场内ETF {etf_code}")
        return await _fetch_holdings(etf_code)

    return None


def _get_fund_sector_fallback(fund_code: str) -> str | None:
    """兜底1：从 fund_sector 表读取已有主题标签"""
    try:
        with DatabaseManager().get_connection() as conn:
            row = conn.execute(
                "SELECT sector FROM fund_sector WHERE fund_code = ?",
                (fund_code,),
            ).fetchone()
            return row[0] if row else None
    except Exception:
        return None


def _get_fund_name_fallback(fund_code: str) -> list[str]:
    """兜底2：从基金名称/跟踪标的提取概念关键词"""
    try:
        with DatabaseManager().get_connection() as conn:
            row = conn.execute(
                "SELECT short_name, name FROM fund_basic_info WHERE code = ?",
                (fund_code,),
            ).fetchone()
            if not row:
                return []
            name = row[1] or row[0] or ""

        # 常见概念关键词映射
        keywords = {
            "人工智能": "人工智能", "AI": "AI",
            "芯片": "芯片", "半导体": "半导体",
            "机器人": "机器人",
            "新能源": "新能源", "光伏": "光伏",
            "白酒": "白酒", "消费": "消费",
            "医药": "医药", "医疗": "医疗",
            "煤炭": "煤炭", "能源": "能源",
            "农业": "农业", "养殖": "养殖",
            "科技": "科技", "数字经济": "数字经济",
            "通信": "通信", "5G": "5G",
            "军工": "军工", "航天": "航天",
            "红利": "红利", "银行": "银行",
            "证券": "证券", "保险": "保险",
            "地产": "地产", "基建": "基建",
            "有色": "有色金属", "钢铁": "钢铁",
            "化工": "化工",
            "纳斯达克": "纳斯达克", "恒生": "恒生",
            "北证": "北证", "科创": "科创板",
            "创业板": "创业板",
            "央企": "央企", "国企": "国企改革",
            "黄金": "黄金",
            "绿电": "绿色电力", "电力": "电力",
            "电池": "电池",
            "畜牧": "畜牧养殖", "粮食": "粮食",
            "云计算": "云计算", "大数据": "大数据",
            "智能": "智能", "高端制造": "高端制造",
            "沪深300": "沪深300", "中证500": "中证500",
        }
        found = []
        for word, tag in keywords.items():
            if word in name:
                found.append(tag)
        return found[:TOP_TAGS_N]
    except Exception:
        return []


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
    if holdings:
        # 2. 查每只重仓股的概念标签，加权聚合
        concept_weight: dict[str, float] = {}

        for h in holdings:
            concepts = stock_concept_dao.get_stock_concepts(h["stock_code"])
            weight = h["proportion"]
            for c in concepts:
                if c not in _NON_THEMATIC_CONCEPTS:
                    concept_weight[c] = concept_weight.get(c, 0) + weight

        if concept_weight:
            # 3. 按总权重降序排列，取 Top N
            sorted_concepts = sorted(concept_weight.items(), key=lambda x: -x[1])
            top_tags = [name for name, _w in sorted_concepts[:TOP_TAGS_N]]

            # 4. 缓存结果
            if top_tags:
                report_period = holdings[0].get("report_period", "")
                fund_concept_dao.save(fund_code, top_tags, report_period)

            return top_tags

    # 5. 兜底：sector → 基金名称
    sector = _get_fund_sector_fallback(fund_code)
    if sector:
        fund_concept_dao.save(fund_code, [sector])
        return [sector]
    name_tags = _get_fund_name_fallback(fund_code)
    if name_tags:
        fund_concept_dao.save(fund_code, name_tags)
    return name_tags


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
