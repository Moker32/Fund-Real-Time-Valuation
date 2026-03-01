#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
手动更新基金基础信息脚本

从 akshare 获取基金的基础信息（名称、类型、基金经理、风险等级等）并保存到数据库。

用法:
    # 更新所有自选基金
    uv run python scripts/update_fund_info.py

    # 更新指定基金
    uv run python scripts/update_fund_info.py --codes 025833,017175

    # 强制更新（即使已有信息）
    uv run python scripts/update_fund_info.py --force
"""

import argparse
import logging
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.db.database import ConfigDAO, DatabaseManager
from src.datasources.fund_source import get_basic_info_db, get_full_fund_info, save_basic_info_to_db

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def get_fund_codes_from_db(force: bool = False) -> list[str]:
    """
    从数据库获取需要更新的基金代码列表

    Args:
        force: 是否强制更新（如果为 False，只更新缺少类型信息的基金）

    Returns:
        基金代码列表
    """
    db_manager = DatabaseManager()
    config_dao = ConfigDAO(db_manager)

    # 获取所有配置的基金
    all_funds = config_dao.get_all_funds()

    if not all_funds:
        logger.warning("数据库中没有配置任何基金")
        return []

    fund_codes = []
    for fund in all_funds:
        if force:
            # 强制模式：更新所有基金
            fund_codes.append(fund.code)
        else:
            # 非强制模式：只更新缺少类型信息的基金
            basic_info = get_basic_info_db(fund.code)
            if not basic_info or not basic_info.get("type"):
                fund_codes.append(fund.code)
            else:
                logger.debug(f"跳过已有类型信息的基金: {fund.code}")

    return fund_codes


def update_fund_info(fund_codes: list[str]) -> tuple[int, int]:
    """
    更新基金基础信息

    Args:
        fund_codes: 基金代码列表

    Returns:
        (成功数量, 失败数量)
    """
    success_count = 0
    fail_count = 0
    total = len(fund_codes)

    if total == 0:
        logger.info("没有需要更新的基金")
        return 0, 0

    logger.info(f"正在更新基金基础信息...")

    for i, code in enumerate(fund_codes, 1):
        try:
            # 获取完整基金信息（从 akshare 获取）
            info = get_full_fund_info(code)

            if info:
                # 获取名称和类型用于显示
                name = info.get("short_name", "") or info.get("name", "") or f"基金 {code}"
                fund_type = info.get("type", "未知类型")

                # 显示更新结果
                logger.info(f"[{i}/{total}] {code}: {name} -> {fund_type} ✓")
                success_count += 1
            else:
                logger.warning(f"[{i}/{total}] {code}: 获取信息失败 ✗")
                fail_count += 1

        except Exception as e:
            logger.error(f"[{i}/{total}] {code}: 更新失败 - {e}")
            fail_count += 1

    return success_count, fail_count


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="更新基金基础信息",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    # 更新所有缺少类型信息的基金
    uv run python scripts/update_fund_info.py

    # 更新指定基金
    uv run python scripts/update_fund_info.py --codes 025833,017175

    # 强制更新所有基金（即使已有信息）
    uv run python scripts/update_fund_info.py --force
        """,
    )

    parser.add_argument(
        "--codes",
        type=str,
        help="指定要更新的基金代码，多个代码用逗号分隔（如: 025833,017175）",
    )

    parser.add_argument(
        "--force",
        action="store_true",
        help="强制更新所有基金，即使已有类型信息",
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="显示详细日志",
    )

    args = parser.parse_args()

    # 设置日志级别
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # 获取基金代码列表
    if args.codes:
        # 从命令行参数获取
        fund_codes = [code.strip() for code in args.codes.split(",") if code.strip()]
        logger.info(f"从命令行获取 {len(fund_codes)} 个基金代码")
    else:
        # 从数据库获取
        fund_codes = get_fund_codes_from_db(force=args.force)

    if not fund_codes:
        logger.info("没有需要更新的基金")
        return

    logger.info(f"共需更新 {len(fund_codes)} 个基金")

    # 执行更新
    success, fail = update_fund_info(fund_codes)

    # 输出统计
    logger.info(f"更新完成: 成功 {success}, 失败 {fail}")


if __name__ == "__main__":
    main()