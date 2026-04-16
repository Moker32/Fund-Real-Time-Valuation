"""
交易时间配置模块

定义全球各大宗商品交易所的交易时间，支持时区转换。
"""

from dataclasses import dataclass
from datetime import time
from enum import Enum
from typing import NamedTuple


class MarketType(str, Enum):
    """市场类型"""

    SGE = "sge"  # 上海黄金交易所
    COMEX = "comex"  # 纽约商品交易所
    NYMEX = "nymex"  # 纽约商业交易所
    LME = "lme"  # 伦敦金属交易所
    LBMA = "lbma"  # 伦敦金银市场协会
    CME = "cme"  # 芝加哥商品交易所
    CBOT = "cbot"  # 芝加哥期货交易所
    ICE = "ice"  # 洲际交易所
    NYBOT = "nybot"  # 纽约期货交易所
    BMD = "bmd"  # 马来西亚衍生品交易所
    TOCOM = "tocom"  # 东京商品交易所
    CRYPTO = "crypto"  # 加密货币（24/7）
    CHINA = "china"  # 中国A股
    HK = "hk"  # 香港交易所
    USA = "usa"  # 美国股市


class TradingSession(NamedTuple):
    """交易时段"""

    start: time
    end: time
    name: str
    overnight: bool = False  # 是否跨夜


@dataclass
class TradingHoursConfig:
    """交易时间配置"""

    market: MarketType
    name: str
    timezone: str  # IANA 时区名称
    sessions: list[TradingSession]
    trading_days: list[int]  # 0=周一, 6=周日
    holidays: list[str] | None = None  # 节假日列表 (YYYY-MM-DD 格式)

    def to_shanghai_time(self, session: TradingSession) -> TradingSession:
        """
        将交易时段转换为上海时间

        Args:
            session: 原始交易时段

        Returns:
            转换后的交易时段
        """
        from zoneinfo import ZoneInfo

        # 获取市场时区和上海时区
        market_tz = ZoneInfo(self.timezone)
        shanghai_tz = ZoneInfo("Asia/Shanghai")

        # 构建今天的日期时间
        from datetime import datetime

        today = datetime.now().date()

        # 转换开始时间
        start_dt = datetime.combine(today, session.start).replace(tzinfo=market_tz)
        start_shanghai = start_dt.astimezone(shanghai_tz)

        # 转换结束时间
        end_dt = datetime.combine(today, session.end).replace(tzinfo=market_tz)
        end_shanghai = end_dt.astimezone(shanghai_tz)

        # 处理跨夜情况
        overnight = session.overnight or (end_shanghai.date() > start_shanghai.date())

        return TradingSession(
            start=start_shanghai.time(),
            end=end_shanghai.time(),
            name=session.name,
            overnight=overnight,
        )


# ==================== 交易所交易时间配置 ====================

# 上海黄金交易所 (SGE)
# 日盘: 9:00-15:30 (北京时间)
# 夜盘: 19:50-次日02:30 (北京时间)
SGE_TRADING_HOURS = TradingHoursConfig(
    market=MarketType.SGE,
    name="上海黄金交易所",
    timezone="Asia/Shanghai",
    sessions=[
        TradingSession(start=time(9, 0), end=time(15, 30), name="日盘"),
        TradingSession(start=time(19, 50), end=time(2, 30), name="夜盘", overnight=True),
    ],
    trading_days=[0, 1, 2, 3, 4],  # 周一至周五
)

# COMEX (纽约商品交易所)
# 电子盘: 周日18:00-周五17:00 (纽约时间)
# 主要交易时段: 8:20-13:30 (纽约时间) = 21:20-次日02:30 (北京时间)
COMEX_TRADING_HOURS = TradingHoursConfig(
    market=MarketType.COMEX,
    name="COMEX",
    timezone="America/New_York",
    sessions=[
        TradingSession(start=time(18, 0), end=time(17, 0), name="电子盘", overnight=True),
        TradingSession(start=time(8, 20), end=time(13, 30), name="公开喊价", overnight=True),
    ],
    trading_days=[0, 1, 2, 3, 4],  # 周一至周五
)

# NYMEX (纽约商业交易所)
# 电子盘: 周日18:00-周五17:00 (纽约时间)
# 主要交易时段: 9:00-14:30 (纽约时间) = 22:00-次日03:30 (北京时间)
NYMEX_TRADING_HOURS = TradingHoursConfig(
    market=MarketType.NYMEX,
    name="NYMEX",
    timezone="America/New_York",
    sessions=[
        TradingSession(start=time(18, 0), end=time(17, 0), name="电子盘", overnight=True),
        TradingSession(start=time(9, 0), end=time(14, 30), name="公开喊价", overnight=True),
    ],
    trading_days=[0, 1, 2, 3, 4],  # 周一至周五
)

# LME (伦敦金属交易所)
# 电子盘 (LMEselect): 1:00-19:00 (伦敦时间) = 9:00-次日03:00 (北京时间)
# 公开喊价: 11:40-17:00 (伦敦时间) = 19:40-次日01:00 (北京时间)
LME_TRADING_HOURS = TradingHoursConfig(
    market=MarketType.LME,
    name="伦敦金属交易所",
    timezone="Europe/London",
    sessions=[
        TradingSession(start=time(1, 0), end=time(19, 0), name="电子盘", overnight=True),
        TradingSession(start=time(11, 40), end=time(17, 0), name="公开喊价", overnight=True),
    ],
    trading_days=[0, 1, 2, 3, 4],  # 周一至周五
)

# LBMA (伦敦金银市场协会)
# 24小时交易，周末休市
LBMA_TRADING_HOURS = TradingHoursConfig(
    market=MarketType.LBMA,
    name="伦敦金银市场",
    timezone="Europe/London",
    sessions=[
        TradingSession(start=time(0, 0), end=time(23, 59, 59), name="全天"),
    ],
    trading_days=[0, 1, 2, 3, 4],  # 周一至周五
)

# CME (芝加哥商品交易所)
# 电子盘: 周日18:00-周五17:00 (芝加哥时间)
# 主要交易时段: 8:30-13:20 (芝加哥时间) = 22:30-次日03:20 (北京时间)
CME_TRADING_HOURS = TradingHoursConfig(
    market=MarketType.CME,
    name="芝加哥商品交易所",
    timezone="America/Chicago",
    sessions=[
        TradingSession(start=time(18, 0), end=time(17, 0), name="电子盘", overnight=True),
        TradingSession(start=time(8, 30), end=time(13, 20), name="公开喊价", overnight=True),
    ],
    trading_days=[0, 1, 2, 3, 4],  # 周一至周五
)

# CBOT (芝加哥期货交易所)
# 电子盘: 周日19:00-周五(次日)07:45 (芝加哥时间)
# 日盘: 9:30-14:20 (芝加哥时间) = 23:30-次日04:20 (北京时间)
CBOT_TRADING_HOURS = TradingHoursConfig(
    market=MarketType.CBOT,
    name="芝加哥期货交易所",
    timezone="America/Chicago",
    sessions=[
        TradingSession(start=time(19, 0), end=time(7, 45), name="电子盘", overnight=True),
        TradingSession(start=time(9, 30), end=time(14, 20), name="日盘", overnight=True),
    ],
    trading_days=[0, 1, 2, 3, 4],  # 周一至周五
)

# ICE (洲际交易所)
# 布伦特原油: 20:00-18:00 (伦敦时间) = 次日04:00-次日02:00 (北京时间)
ICE_TRADING_HOURS = TradingHoursConfig(
    market=MarketType.ICE,
    name="洲际交易所",
    timezone="Europe/London",
    sessions=[
        TradingSession(start=time(20, 0), end=time(18, 0), name="电子盘", overnight=True),
    ],
    trading_days=[0, 1, 2, 3, 4],  # 周一至周五
)

# NYBOT (纽约期货交易所)
# 棉花: 9:00-14:30 (纽约时间) = 22:00-次日03:30 (北京时间)
NYBOT_TRADING_HOURS = TradingHoursConfig(
    market=MarketType.NYBOT,
    name="纽约期货交易所",
    timezone="America/New_York",
    sessions=[
        TradingSession(start=time(9, 0), end=time(14, 30), name="日盘", overnight=True),
    ],
    trading_days=[0, 1, 2, 3, 4],  # 周一至周五
)

# 加密货币 (24/7 交易)
CRYPTO_TRADING_HOURS = TradingHoursConfig(
    market=MarketType.CRYPTO,
    name="加密货币",
    timezone="UTC",
    sessions=[
        TradingSession(start=time(0, 0), end=time(23, 59, 59), name="全天"),
    ],
    trading_days=[0, 1, 2, 3, 4, 5, 6],  # 全周
)

# 中国A股
# 上午: 9:30-11:30 (北京时间)
# 下午: 13:00-15:00 (北京时间)
CHINA_TRADING_HOURS = TradingHoursConfig(
    market=MarketType.CHINA,
    name="中国A股",
    timezone="Asia/Shanghai",
    sessions=[
        TradingSession(start=time(9, 30), end=time(11, 30), name="上午"),
        TradingSession(start=time(13, 0), end=time(15, 0), name="下午"),
    ],
    trading_days=[0, 1, 2, 3, 4],  # 周一至周五
)

# 香港交易所
# 上午: 9:30-12:00 (香港时间)
# 下午: 13:00-16:00 (香港时间)
HK_TRADING_HOURS = TradingHoursConfig(
    market=MarketType.HK,
    name="香港交易所",
    timezone="Asia/Hong_Kong",
    sessions=[
        TradingSession(start=time(9, 30), end=time(12, 0), name="上午"),
        TradingSession(start=time(13, 0), end=time(16, 0), name="下午"),
    ],
    trading_days=[0, 1, 2, 3, 4],  # 周一至周五
)

# 美国股市
# 常规交易: 9:30-16:00 (纽约时间) = 22:30-次日05:00 (北京时间夏令时) / 23:30-次日06:00 (冬令时)
# 盘前: 4:00-9:30 (纽约时间)
# 盘后: 16:00-20:00 (纽约时间)
USA_TRADING_HOURS = TradingHoursConfig(
    market=MarketType.USA,
    name="美国股市",
    timezone="America/New_York",
    sessions=[
        TradingSession(start=time(4, 0), end=time(9, 30), name="盘前"),
        TradingSession(start=time(9, 30), end=time(16, 0), name="常规"),
        TradingSession(start=time(16, 0), end=time(20, 0), name="盘后"),
    ],
    trading_days=[0, 1, 2, 3, 4],  # 周一至周五
)


# 市场配置映射
MARKET_CONFIGS: dict[MarketType, TradingHoursConfig] = {
    MarketType.SGE: SGE_TRADING_HOURS,
    MarketType.COMEX: COMEX_TRADING_HOURS,
    MarketType.NYMEX: NYMEX_TRADING_HOURS,
    MarketType.LME: LME_TRADING_HOURS,
    MarketType.LBMA: LBMA_TRADING_HOURS,
    MarketType.CME: CME_TRADING_HOURS,
    MarketType.CBOT: CBOT_TRADING_HOURS,
    MarketType.ICE: ICE_TRADING_HOURS,
    MarketType.NYBOT: NYBOT_TRADING_HOURS,
    MarketType.CRYPTO: CRYPTO_TRADING_HOURS,
    MarketType.CHINA: CHINA_TRADING_HOURS,
    MarketType.HK: HK_TRADING_HOURS,
    MarketType.USA: USA_TRADING_HOURS,
}


# 商品代码到市场的映射
COMMODITY_MARKET_MAP: dict[str, MarketType] = {
    # 上海黄金
    "Au99.99": MarketType.SGE,
    "SG=F": MarketType.SGE,
    "gold_cny": MarketType.SGE,
    # COMEX 贵金属
    "GC=F": MarketType.COMEX,
    "gold": MarketType.COMEX,
    "SI=F": MarketType.COMEX,
    "silver": MarketType.COMEX,
    "HG=F": MarketType.COMEX,
    "copper": MarketType.COMEX,
    # NYMEX 能源
    "CL=F": MarketType.NYMEX,
    "wti": MarketType.NYMEX,
    "NG=F": MarketType.NYMEX,
    "natural_gas": MarketType.NYMEX,
    "BZ=F": MarketType.ICE,
    "brent": MarketType.ICE,
    # LME 基本金属
    "AL=F": MarketType.LME,
    "aluminum": MarketType.LME,
    "ZN=F": MarketType.LME,
    "zinc": MarketType.LME,
    "NI=F": MarketType.LME,
    "nickel": MarketType.LME,
    # 加密货币
    "BTC-USD": MarketType.CRYPTO,
    "btc": MarketType.CRYPTO,
    "ETH-USD": MarketType.CRYPTO,
    "eth": MarketType.CRYPTO,
    "BTC=F": MarketType.CME,
    "btc_futures": MarketType.CME,
    "ETH=F": MarketType.CME,
    "eth_futures": MarketType.CME,
    # CBOT 农产品
    "ZS=F": MarketType.CBOT,
    "soybean": MarketType.CBOT,
    "ZC=F": MarketType.CBOT,
    "corn": MarketType.CBOT,
    "ZW=F": MarketType.CBOT,
    "wheat": MarketType.CBOT,
    # NYBOT
    "CT=F": MarketType.NYBOT,
    "cotton": MarketType.NYBOT,
}


def get_market_config(market: MarketType | str) -> TradingHoursConfig | None:
    """
    获取市场配置

    Args:
        market: 市场类型或市场代码

    Returns:
        交易时间配置，如果不存在则返回 None
    """
    if isinstance(market, str):
        try:
            market = MarketType(market.lower())
        except ValueError:
            return None
    return MARKET_CONFIGS.get(market)


def get_commodity_market(symbol: str) -> MarketType:
    """
    根据商品代码获取对应的市场

    Args:
        symbol: 商品代码

    Returns:
        市场类型
    """
    # 直接匹配
    if symbol in COMMODITY_MARKET_MAP:
        return COMMODITY_MARKET_MAP[symbol]

    # 尝试小写匹配
    symbol_lower = symbol.lower()
    if symbol_lower in COMMODITY_MARKET_MAP:
        return COMMODITY_MARKET_MAP[symbol_lower]

    # 根据代码前缀判断
    if symbol.startswith("GC=F") or symbol.startswith("SI=F") or symbol.startswith("HG=F"):
        return MarketType.COMEX
    if symbol.startswith("CL=F") or symbol.startswith("NG=F"):
        return MarketType.NYMEX
    if symbol.startswith("BZ=F"):
        return MarketType.ICE
    if symbol.startswith("AL=F") or symbol.startswith("ZN=F") or symbol.startswith("NI=F"):
        return MarketType.LME
    if symbol.startswith("ZS=F") or symbol.startswith("ZC=F") or symbol.startswith("ZW=F"):
        return MarketType.CBOT
    if symbol.startswith("BTC") or symbol.startswith("ETH"):
        return MarketType.CRYPTO
    if symbol.startswith("Au") or symbol.startswith("SG=F"):
        return MarketType.SGE

    # 默认返回 COMEX
    return MarketType.COMEX


def is_trading_hours(
    market: MarketType | str, check_time: time | None = None, check_weekday: int | None = None
) -> bool:
    """
    检查指定市场是否处于交易时间

    Args:
        market: 市场类型或代码
        check_time: 要检查的时间，默认为当前时间
        check_weekday: 要检查的星期，0=周一，默认为今天

    Returns:
        是否处于交易时间
    """
    from datetime import datetime

    config = get_market_config(market)
    if not config:
        return False

    # 获取当前上海时间
    now = datetime.now()
    shanghai_time = now.astimezone()
    current_time = check_time or shanghai_time.time()
    current_weekday = check_weekday if check_weekday is not None else shanghai_time.weekday()

    # 检查是否是交易日
    if current_weekday not in config.trading_days:
        return False

    # 加密货币24/7交易
    if config.market == MarketType.CRYPTO:
        return True

    # 检查是否在交易时段内
    for session in config.sessions:
        # 转换为上海时间
        shanghai_session = config.to_shanghai_time(session)

        if shanghai_session.overnight:
            # 跨夜时段
            if shanghai_session.start <= current_time or current_time <= shanghai_session.end:
                return True
        else:
            # 非跨夜时段
            if shanghai_session.start <= current_time <= shanghai_session.end:
                return True

    return False


def get_trading_status(market: MarketType | str) -> dict:
    """
    获取市场交易状态详情

    Args:
        market: 市场类型或代码

    Returns:
        包含交易状态信息的字典
    """
    from datetime import datetime

    config = get_market_config(market)
    if not config:
        return {"error": "未知市场"}

    now = datetime.now()
    shanghai_time = now.astimezone()
    current_time = shanghai_time.time()
    current_weekday = shanghai_time.weekday()

    is_trading = is_trading_hours(market, current_time, current_weekday)

    # 获取当前时段
    current_session = None
    for session in config.sessions:
        shanghai_session = config.to_shanghai_time(session)
        if shanghai_session.overnight:
            if shanghai_session.start <= current_time or current_time <= shanghai_session.end:
                current_session = shanghai_session.name
                break
        else:
            if shanghai_session.start <= current_time <= shanghai_session.end:
                current_session = shanghai_session.name
                break

    return {
        "market": config.market.value,
        "name": config.name,
        "is_trading": is_trading,
        "current_session": current_session,
        "current_time_shanghai": current_time.strftime("%H:%M"),
        "trading_days": ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][current_weekday],
        "timezone": config.timezone,
    }


# 导出所有配置
__all__ = [
    "MarketType",
    "TradingSession",
    "TradingHoursConfig",
    "SGE_TRADING_HOURS",
    "COMEX_TRADING_HOURS",
    "NYMEX_TRADING_HOURS",
    "LME_TRADING_HOURS",
    "LBMA_TRADING_HOURS",
    "CME_TRADING_HOURS",
    "CBOT_TRADING_HOURS",
    "ICE_TRADING_HOURS",
    "NYBOT_TRADING_HOURS",
    "CRYPTO_TRADING_HOURS",
    "CHINA_TRADING_HOURS",
    "HK_TRADING_HOURS",
    "USA_TRADING_HOURS",
    "MARKET_CONFIGS",
    "COMMODITY_MARKET_MAP",
    "get_market_config",
    "get_commodity_market",
    "is_trading_hours",
    "get_trading_status",
]
