"""腾讯财经指数数据源 (A股、港股、美股 - 实时)"""

import logging
import re
import time
from datetime import datetime
from typing import Any

import httpx

from ..base import DataSourceResult
from .base import INDEX_NAMES, INDEX_REGIONS, TENCENT_CODES, IndexDataSource

logger = logging.getLogger(__name__)


class TencentIndexSource(IndexDataSource):
    """腾讯财经指数数据源 (A股、港股、美股 - 实时)"""

    def __init__(self, timeout: float = 10.0):
        super().__init__(name="tencent_index", timeout=timeout)
        self.base_url = "https://qt.gtimg.cn/q"

    async def fetch(self, index_type: str) -> DataSourceResult:
        """
        获取单个指数数据

        Args:
            index_type: 指数类型 (如 shanghai, hang_seng, dow_jones 等)

        Returns:
            DataSourceResult: 指数数据结果
        """
        try:
            tencent_code = TENCENT_CODES.get(index_type)
            if not tencent_code:
                return DataSourceResult(
                    success=False,
                    error=f"腾讯财经不支持的指数类型: {index_type}",
                    timestamp=time.time(),
                    source=self.name,
                    metadata={"index_type": index_type},
                )

            url = f"{self.base_url}={tencent_code}"

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url)
                response.raise_for_status()
                text = response.text.strip()

            if "none_match" in text or not text:
                return DataSourceResult(
                    success=False,
                    error=f"未找到指数数据: {index_type}",
                    timestamp=time.time(),
                    source=self.name,
                    metadata={"index_type": index_type},
                )

            # 解析数据
            # 格式: v_usDJI="200~道琼斯~.DJI~49451.98~50121.40~...";
            match = re.search(r'="([^"]+)"', text)
            if not match:
                return DataSourceResult(
                    success=False,
                    error="解析腾讯财经数据失败",
                    timestamp=time.time(),
                    source=self.name,
                    metadata={"index_type": index_type},
                )

            parts = match.group(1).split("~")

            # 判断市场类型
            is_us = tencent_code.startswith("us")
            is_hk = tencent_code.startswith("hk")

            if is_us:
                # 美股格式
                price = float(parts[3]) if parts[3] else 0.0
                open_price = float(parts[5]) if len(parts) > 5 and parts[5] else 0.0
                prev_close = float(parts[4]) if parts[4] else 0.0
                high = float(parts[33]) if len(parts) > 33 and parts[33] else 0.0
                low = float(parts[34]) if len(parts) > 34 and parts[34] else 0.0
                change = float(parts[31]) if len(parts) > 31 and parts[31] else 0.0
                # 涨跌幅计算
                if price > 0 and prev_close > 0:
                    change_percent = (change / prev_close) * 100
                else:
                    change_percent = 0.0
                currency = "USD"
                exchange = "US"
            elif is_hk:
                # 港股格式: 3=当前价, 4=昨日收盘, 5=开盘, 33=最高, 34=最低
                price = float(parts[3]) if parts[3] else 0.0
                open_price = float(parts[5]) if len(parts) > 5 and parts[5] else 0.0
                prev_close = float(parts[4]) if parts[4] else 0.0
                high = float(parts[33]) if len(parts) > 33 and parts[33] else 0.0
                low = float(parts[34]) if len(parts) > 34 and parts[34] else 0.0
                change = float(parts[31]) if len(parts) > 31 and parts[31] else 0.0
                if price > 0 and prev_close > 0:
                    change_percent = (change / prev_close) * 100
                else:
                    change_percent = 0.0
                currency = "HKD"
                exchange = "HKEX"
            else:
                # A股格式: 3=当前价, 4=昨日收盘, 5=开盘, 33=最高, 34=最低, 31=涨跌, 32=涨跌幅
                price = float(parts[3]) if parts[3] else 0.0
                open_price = float(parts[5]) if parts[5] else 0.0
                prev_close = float(parts[4]) if parts[4] else 0.0
                high = float(parts[33]) if parts[33] else 0.0
                low = float(parts[34]) if parts[34] else 0.0
                change = float(parts[31]) if parts[31] else 0.0
                change_percent = float(parts[32]) if parts[32] else 0.0
                currency = "CNY"
                # Fix: A股代码格式是 sh000001 或 sz399001，不是 s_sh
                exchange = "SSE" if tencent_code.startswith("sh") else "SZSE"

            # 从腾讯数据中提取时间戳（格式：YYYYMMDDHHmmss）
            # 例如：20210105154040 表示 2021-01-05 15:40:40
            data_timestamp: datetime | None = None
            for i in range(len(parts) - 1, -1, -1):
                if parts[i] and len(parts[i]) == 14 and parts[i].isdigit():
                    try:
                        data_timestamp = datetime.strptime(parts[i], "%Y%m%d%H%M%S")
                        break
                    except ValueError:
                        continue

            # 如果找到时间戳则使用，否则使用当前时间
            if data_timestamp:
                time_str = data_timestamp.strftime("%Y-%m-%d %H:%M:%S")
            else:
                time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            data = {
                "index": index_type,
                "symbol": tencent_code,
                "name": INDEX_NAMES.get(index_type, index_type),
                "price": price,
                "change": change,
                "change_percent": change_percent,
                "currency": currency,
                "exchange": exchange,
                "time": time_str,
                "data_timestamp": data_timestamp.isoformat() if data_timestamp else None,
                "high": high,
                "low": low,
                "open": open_price,
                "prev_close": prev_close,
                "region": INDEX_REGIONS.get(index_type, "unknown"),
            }

            self._record_success()
            return DataSourceResult(
                success=True,
                data=data,
                timestamp=time.time(),
                source=self.name,
                metadata={"index_type": index_type},
            )

        except httpx.HTTPError as e:
            return self._handle_error(e, self.name)
        except Exception as e:
            return self._handle_error(e, self.name)

    def get_status(self) -> dict[str, Any]:
        """获取数据源状态"""
        status = super().get_status()
        status["supported_indices"] = list(TENCENT_CODES.keys())
        return status
