"""
大宗商品关注列表配置管理模块

提供关注商品的添加、移除、更新和分类自动识别功能
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import TypedDict

import yaml


class WatchedCommodityDict(TypedDict):
    """关注商品数据结构（YAML 格式）"""
    symbol: str       # 商品代码 (GC=F, ZS=F...)
    name: str         # 显示名称
    category: str     # 分类 (precious_metal/energy/base_metal/agriculture/other)
    added_at: str    # 添加时间 (ISO 8601)


class CommoditiesConfigDict(TypedDict):
    """配置文件根结构"""
    watched_commodities: list[WatchedCommodityDict]


# 分类识别映射表
CATEGORY_MAPPING: dict[str, str] = {
    # 贵金属
    "GC=F": "precious_metal",
    "SI=F": "precious_metal",
    "PT=F": "precious_metal",
    "PA=F": "precious_metal",
    # 能源
    "CL=F": "energy",
    "BZ=F": "energy",
    "NG=F": "energy",
    "HO=F": "energy",
    # 基本金属
    "HG=F": "base_metal",
    "AL=F": "base_metal",
    "ZN=F": "base_metal",
    "NI=F": "base_metal",
    "PB=F": "base_metal",
    "SN=F": "base_metal",
    # 农产品
    "ZS=F": "agriculture",
    "ZC=F": "agriculture",
    "ZW=F": "agriculture",
    "KC=F": "agriculture",
    "SB=F": "agriculture",
    "LE=F": "agriculture",
    "HE=F": "agriculture",
    "ZR=F": "agriculture",
    # 加密货币
    "BTC=F": "crypto",
    "ETH=F": "crypto",
}


class CommoditiesConfig:
    """大宗商品关注列表配置管理类"""

    def __init__(self, config_dir: str | None = None):
        """
        初始化关注商品配置管理器

        Args:
            config_dir: 配置目录，默认为 ~/.fund-tui/
        """
        self._config_dir = config_dir or str(Path.home() / '.fund-tui')
        self._config_path = Path(self._config_dir) / 'commodities.yaml'
        self._ensure_config_dir()

    def _ensure_config_dir(self) -> None:
        """确保配置目录存在"""
        Path(self._config_dir).mkdir(parents=True, exist_ok=True)
        if not self._config_path.exists():
            self._save({"watched_commodities": []})

    def _load(self) -> CommoditiesConfigDict:
        """加载配置文件"""
        try:
            with open(self._config_path, encoding='utf-8') as f:
                data = yaml.safe_load(f)
                if data is None:
                    return {"watched_commodities": []}
                return data
        except FileNotFoundError:
            return {"watched_commodities": []}
        except Exception as e:
            raise ValueError(f"加载配置文件失败: {e}")

    def _save(self, data: CommoditiesConfigDict) -> None:
        """保存配置文件"""
        with open(self._config_path, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, allow_unicode=True, sort_keys=False)

    @staticmethod
    def identify_category(symbol: str) -> str:
        """
        自动识别商品分类

        Args:
            symbol: 商品代码

        Returns:
            str: 分类名称 (precious_metal/energy/base_metal/agriculture/crypto/other)
        """
        # 清理 symbol
        clean_symbol = symbol.upper().strip()
        if not clean_symbol.endswith('=F'):
            clean_symbol = clean_symbol.upper()

        return CATEGORY_MAPPING.get(clean_symbol, "other")

    def get_watched_commodities(self) -> list[WatchedCommodityDict]:
        """
        获取关注列表

        Returns:
            list[WatchedCommodityDict]: 关注商品列表
        """
        data = self._load()
        return data.get("watched_commodities", [])

    def is_watching(self, symbol: str) -> bool:
        """
        检查商品是否已在关注列表中

        Args:
            symbol: 商品代码

        Returns:
            bool: 是否已关注
        """
        watched = self.get_watched_commodities()
        clean_symbol = symbol.upper().strip()
        if not clean_symbol.endswith('=F'):
            clean_symbol = f"{clean_symbol}=F"
        return any(w["symbol"].upper() == clean_symbol for w in watched)

    def add_watched_commodity(
        self,
        symbol: str,
        name: str,
        category: str | None = None
    ) -> tuple[bool, str]:
        """
        添加关注商品

        Args:
            symbol: 商品代码
            name: 显示名称
            category: 分类（可选，自动识别）

        Returns:
            tuple[bool, str]: (是否成功, 消息)
        """
        # 清理 symbol
        clean_symbol = symbol.upper().strip()
        if not clean_symbol.endswith('=F'):
            clean_symbol = f"{clean_symbol}=F"

        # 检查是否已存在
        if self.is_watching(clean_symbol):
            return False, f"商品 {clean_symbol} 已在关注列表中"

        # 自动识别分类
        if category is None:
            category = self.identify_category(clean_symbol)

        # 加载现有配置
        data = self._load()

        # 确保有列表
        if "watched_commodities" not in data:
            data["watched_commodities"] = []

        # 添加新商品
        now = datetime.now(timezone.utc).isoformat()
        new_commodity: WatchedCommodityDict = {
            "symbol": clean_symbol,
            "name": name,
            "category": category,
            "added_at": now,
        }
        data["watched_commodities"].append(new_commodity)

        # 保存
        self._save(data)
        return True, f"已添加 {name} ({clean_symbol}) 到关注列表"

    def remove_watched_commodity(self, symbol: str) -> tuple[bool, str]:
        """
        移除关注商品

        Args:
            symbol: 商品代码

        Returns:
            tuple[bool, str]: (是否成功, 消息)
        """
        # 清理 symbol
        clean_symbol = symbol.upper().strip()
        if not clean_symbol.endswith('=F'):
            clean_symbol = f"{clean_symbol}=F"

        # 加载配置
        data = self._load()
        watched = data.get("watched_commodities", [])

        # 查找并移除
        original_len = len(watched)
        data["watched_commodities"] = [
            w for w in watched if w["symbol"].upper() != clean_symbol
        ]

        if len(data["watched_commodities"]) < original_len:
            self._save(data)
            return True, f"已从关注列表移除 {clean_symbol}"
        return False, f"商品 {clean_symbol} 不在关注列表中"

    def update_watched_commodity_name(self, symbol: str, name: str) -> tuple[bool, str]:
        """
        更新关注商品名称

        Args:
            symbol: 商品代码
            name: 新名称

        Returns:
            tuple[bool, str]: (是否成功, 消息)
        """
        # 清理 symbol
        clean_symbol = symbol.upper().strip()
        if not clean_symbol.endswith('=F'):
            clean_symbol = f"{clean_symbol}=F"

        # 加载配置
        data = self._load()
        watched = data.get("watched_commodities", [])

        # 查找并更新
        for item in watched:
            if item["symbol"].upper() == clean_symbol:
                old_name = item["name"]
                item["name"] = name
                self._save(data)
                return True, f"已将 {old_name} 更新为 {name}"
        return False, f"商品 {clean_symbol} 不在关注列表中"

    def update_watched_commodity_category(
        self, symbol: str, category: str
    ) -> tuple[bool, str]:
        """
        更新关注商品分类

        Args:
            symbol: 商品代码
            category: 新分类

        Returns:
            tuple[bool, str]: (是否成功, 消息)
        """
        # 清理 symbol
        clean_symbol = symbol.upper().strip()
        if not clean_symbol.endswith('=F'):
            clean_symbol = f"{clean_symbol}=F"

        # 加载配置
        data = self._load()
        watched = data.get("watched_commodities", [])

        # 查找并更新
        for item in watched:
            if item["symbol"].upper() == clean_symbol:
                old_category = item.get("category", "other")
                item["category"] = category
                self._save(data)
                return True, f"已将 {clean_symbol} 分类从 {old_category} 更新为 {category}"
        return False, f"商品 {clean_symbol} 不在关注列表中"

    def clear_watched_commodities(self) -> tuple[bool, str]:
        """
        清空关注列表

        Returns:
            tuple[bool, str]: (是否成功, 消息)
        """
        data = self._load()
        count = len(data.get("watched_commodities", []))
        if count > 0:
            data["watched_commodities"] = []
            self._save(data)
            return True, f"已清空关注列表 ({count} 个商品)"
        return False, "关注列表已经是空的"

    def get_watched_by_category(self, category: str) -> list[WatchedCommodityDict]:
        """
        按分类获取关注商品

        Args:
            category: 分类名称

        Returns:
            list[WatchedCommodityDict]: 分类下的关注商品列表
        """
        watched = self.get_watched_commodities()
        return [w for w in watched if w.get("category") == category]

    def get_watched_count(self) -> int:
        """
        获取关注商品数量

        Returns:
            int: 关注商品数量
        """
        return len(self.get_watched_commodities())


# 全局配置管理器实例
_config_instance: CommoditiesConfig | None = None


def get_commodities_config(config_dir: str | None = None) -> CommoditiesConfig:
    """
    获取全局关注商品配置管理器实例

    Args:
        config_dir: 配置目录

    Returns:
        CommoditiesConfig: 配置管理器实例
    """
    global _config_instance
    if _config_instance is None:
        _config_instance = CommoditiesConfig(config_dir)
    return _config_instance
