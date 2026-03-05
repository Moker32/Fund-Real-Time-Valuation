#!/usr/bin/env python3
"""
基金基本信息同步脚本

从 akshare 获取全部基金基本信息并保存到本地数据库。
用于加速基金搜索，无需每次都调用外部 API。

用法:
    uv run python scripts/sync_fund_info.py
"""

import sys
import time
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, str(__file__).replace("scripts/sync_fund_info.py", ""))

from src.db.database import DatabaseManager, FundBasicInfoDAO


def sync_fund_info(batch_size: int = 500, limit: int | None = None):
    """同步基金基本信息到本地数据库

    Args:
        batch_size: 每次批量插入的数量
        limit: 限制同步数量（用于测试），None 表示全部
    """
    import akshare as ak

    print("=" * 60)
    print("基金基本信息同步")
    print("=" * 60)

    start_time = time.time()

    # 1. 获取基金列表
    print("\n[1/3] 获取基金列表...")
    df = ak.fund_name_em()
    print(f"  获取到 {len(df)} 只基金")

    if limit:
        df = df.head(limit)
        print(f"  限制同步前 {limit} 只")

    total = len(df)

    # 2. 初始化数据库
    print("\n[2/3] 初始化数据库...")
    db_manager = DatabaseManager()
    dao = FundBasicInfoDAO(db_manager)

    # 3. 批量插入
    print(f"\n[3/3] 同步到数据库 (每批 {batch_size})...")

    records = []
    success_count = 0
    error_count = 0

    for idx, row in df.iterrows():
        try:
            code = str(row.get("基金代码", "")).strip()
            name = str(row.get("基金简称", "")).strip()
            fund_type = str(row.get("基金类型", "")).strip()

            if not code:
                continue

            # 构建记录
            record = {
                "code": code,
                "name": name,
                "short_name": name,
                "type": fund_type,
            }
            records.append(record)

            # 批量插入
            if len(records) >= batch_size:
                saved = _batch_save(dao, records)
                success_count += saved
                error_count += len(records) - saved
                print(f"  进度: {idx + 1}/{total} ({(idx + 1) * 100 // total}%)")
                records = []

        except Exception as e:
            error_count += 1
            if error_count <= 3:
                print(f"  警告: {e}")

    # 插入剩余记录
    if records:
        saved = _batch_save(dao, records)
        success_count += saved
        error_count += len(records) - saved

    elapsed = time.time() - start_time

    # 4. 统计结果
    print("\n" + "=" * 60)
    print("同步完成!")
    print("=" * 60)
    print(f"  总数: {total}")
    print(f"  成功: {success_count}")
    print(f"  失败: {error_count}")
    print(f"  耗时: {elapsed:.1f} 秒")
    print(f"  速度: {total / elapsed:.0f} 只/秒")

    # 显示数据库统计
    all_funds = dao.get_all()
    print(f"\n数据库当前共有: {len(all_funds)} 只基金")

    return success_count


def _batch_save(dao: FundBasicInfoDAO, records: list[dict]) -> int:
    """批量保存记录"""
    saved = 0
    for record in records:
        try:
            dao.save(
                code=record["code"],
                name=record.get("name"),
                short_name=record.get("short_name"),
                type=record.get("type"),
            )
            saved += 1
        except Exception:
            pass
    return saved


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="同步基金基本信息")
    parser.add_argument("--batch-size", type=int, default=500, help="批量插入大小")
    parser.add_argument("--limit", type=int, default=None, help="限制同步数量(用于测试)")
    args = parser.parse_args()

    sync_fund_info(batch_size=args.batch_size, limit=args.limit)
