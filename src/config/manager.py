"""
配置管理器模块
统一管理所有配置文件的加载和保存
"""

from pathlib import Path

from .base import AppConfigLoader, BaseConfigLoader
from .models import AppConfig, Commodity, CommodityList, Fund, FundList, Holding


class FundConfigLoader(BaseConfigLoader[FundList]):
    """基金配置加载器"""

    def __init__(self, config_dir: str | None = None):
        super().__init__('funds.yaml', config_dir)

    def _parse(self, data: dict) -> FundList:
        """解析基金配置数据"""
        watchlist = []
        holdings = []

        # 解析自选基金
        for item in data.get('watchlist', []):
            watchlist.append(Fund(
                code=item.get('code', ''),
                name=item.get('name', '')
            ))

        # 解析持仓基金
        for item in data.get('holdings', []):
            holdings.append(Holding(
                code=item.get('code', ''),
                name=item.get('name', ''),
                shares=item.get('shares', 0.0),
                cost=item.get('cost', 0.0)
            ))

        return FundList(watchlist=watchlist, holdings=holdings)

    def _serialize(self, config: FundList) -> dict:
        """序列化基金配置对象"""
        return {
            'watchlist': [
                {'code': f.code, 'name': f.name}
                for f in config.watchlist
            ],
            'holdings': [
                {'code': h.code, 'name': h.name, 'shares': h.shares, 'cost': h.cost}
                for h in config.holdings
            ]
        }


class CommodityConfigLoader(BaseConfigLoader[CommodityList]):
    """商品配置加载器"""

    def __init__(self, config_dir: str | None = None):
        super().__init__('commodities.yaml', config_dir)

    def _parse(self, data: dict) -> CommodityList:
        """解析商品配置数据"""
        commodities = []

        for item in data.get('commodities', []):
            commodities.append(Commodity(
                symbol=item.get('symbol', ''),
                name=item.get('name', ''),
                source=item.get('source', 'akshare')
            ))

        return CommodityList(commodities=commodities)

    def _serialize(self, config: CommodityList) -> dict:
        """序列化商品配置对象"""
        return {
            'commodities': [
                {'symbol': c.symbol, 'name': c.name, 'source': c.source}
                for c in config.commodities
            ]
        }


class ConfigManager:
    """
    配置管理器
    统一管理所有配置文件的加载和保存
    """

    def __init__(self, config_dir: str | None = None):
        """
        初始化配置管理器

        Args:
            config_dir: 配置目录，默认为 ~/.fund-tui/
        """
        self._config_dir = config_dir or str(Path.home() / '.fund-tui')
        self._ensure_config_dir()

        # 初始化各配置加载器
        self._app_config = AppConfigLoader(self._config_dir)
        self._fund_config = FundConfigLoader(self._config_dir)
        self._commodity_config = CommodityConfigLoader(self._config_dir)

    def _ensure_config_dir(self) -> None:
        """确保配置目录存在"""
        Path(self._config_dir).mkdir(parents=True, exist_ok=True)

    # === 应用主配置 ===

    def load_app_config(self) -> AppConfig:
        """加载应用主配置"""
        return self._app_config.load()

    def save_app_config(self, config: AppConfig) -> None:
        """保存应用主配置"""
        self._app_config.save(config)

    # === 基金配置 ===

    def load_funds(self) -> FundList:
        """加载基金配置"""
        return self._fund_config.load()

    def save_funds(self, config: FundList) -> None:
        """保存基金配置"""
        self._fund_config.save(config)

    def add_watchlist(self, fund: Fund) -> bool:
        """
        添加自选基金

        Args:
            fund: 基金对象

        Returns:
            bool: 是否添加成功（已存在则返回 False）
        """
        funds = self.load_funds()
        if funds.is_watching(fund.code):
            return False
        funds.watchlist.append(fund)
        self.save_funds(funds)
        return True

    def remove_watchlist(self, code: str) -> bool:
        """
        移除自选基金

        Args:
            code: 基金代码

        Returns:
            bool: 是否移除成功
        """
        funds = self.load_funds()
        original_len = len(funds.watchlist)
        funds.watchlist = [f for f in funds.watchlist if f.code != code]
        if len(funds.watchlist) < original_len:
            self.save_funds(funds)
            return True
        return False

    def add_holding(self, holding: Holding) -> bool:
        """
        添加持仓基金

        Args:
            holding: 持仓对象

        Returns:
            bool: 是否添加成功
        """
        funds = self.load_funds()
        if funds.get_holding(holding.code) is not None:
            return False
        funds.holdings.append(holding)
        self.save_funds(funds)
        return True

    def update_holding(self, holding: Holding) -> bool:
        """
        更新持仓基金信息

        Args:
            holding: 持仓对象

        Returns:
            bool: 是否更新成功
        """
        funds = self.load_funds()
        for i, h in enumerate(funds.holdings):
            if h.code == holding.code:
                funds.holdings[i] = holding
                self.save_funds(funds)
                return True
        return False

    def remove_holding(self, code: str) -> bool:
        """
        移除持仓基金

        Args:
            code: 基金代码

        Returns:
            bool: 是否移除成功
        """
        funds = self.load_funds()
        original_len = len(funds.holdings)
        funds.holdings = [h for h in funds.holdings if h.code != code]
        if len(funds.holdings) < original_len:
            self.save_funds(funds)
            return True
        return False

    # === 商品配置 ===

    def load_commodities(self) -> CommodityList:
        """加载商品配置"""
        return self._commodity_config.load()

    def save_commodities(self, config: CommodityList) -> None:
        """保存商品配置"""
        self._commodity_config.save(config)

    def add_commodity(self, commodity: Commodity) -> bool:
        """
        添加商品

        Args:
            commodity: 商品对象

        Returns:
            bool: 是否添加成功
        """
        commodities = self.load_commodities()
        if commodities.get_by_symbol(commodity.symbol) is not None:
            return False
        commodities.commodities.append(commodity)
        self.save_commodities(commodities)
        return True

    def update_commodity(self, commodity: Commodity) -> bool:
        """
        更新商品信息

        Args:
            commodity: 商品对象

        Returns:
            bool: 是否更新成功
        """
        commodities = self.load_commodities()
        for i, c in enumerate(commodities.commodities):
            if c.symbol == commodity.symbol:
                commodities.commodities[i] = commodity
                self.save_commodities(commodities)
                return True
        return False

    def remove_commodity(self, symbol: str) -> bool:
        """
        移除商品

        Args:
            symbol: 商品代码

        Returns:
            bool: 是否移除成功
        """
        commodities = self.load_commodities()
        original_len = len(commodities.commodities)
        commodities.commodities = [
            c for c in commodities.commodities if c.symbol != symbol
        ]
        if len(commodities.commodities) < original_len:
            self.save_commodities(commodities)
            return True
        return False

    # === 备份与恢复 ===

    def backup_all(self) -> dict:
        """
        备份所有配置文件

        Returns:
            dict: 各配置文件的备份路径
        """
        backups = {
            'app': self._app_config.backup(),
            'funds': self._fund_config.backup(),
            'commodities': self._commodity_config.backup(),
        }
        return backups

    def get_config_dir(self) -> str:
        """获取配置目录路径"""
        return self._config_dir
