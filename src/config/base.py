"""
配置基类模块
定义 YAML 配置文件的加载和保存基类
"""

import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Generic, TypeVar

import yaml

from .models import AppConfig

T = TypeVar('T')


class BaseConfigLoader(ABC, Generic[T]):
    """配置加载器基类"""

    def __init__(self, config_path: str, config_dir: str | None = None):
        """
        初始化配置加载器

        Args:
            config_path: 配置文件名（如 config.yaml）
            config_dir: 配置目录，默认为 ~/.fund-tui/
        """
        self._config_dir = config_dir or self._get_default_config_dir()
        self._config_path = os.path.join(self._config_dir, config_path)
        self._ensure_config_dir()

    def _get_default_config_dir(self) -> str:
        """获取默认配置目录"""
        home = Path.home()
        return str(home / '.fund-tui')

    def _ensure_config_dir(self) -> None:
        """确保配置目录存在"""
        Path(self._config_dir).mkdir(parents=True, exist_ok=True)

    def _load_yaml(self) -> dict:
        """加载 YAML 文件"""
        try:
            with open(self._config_path, encoding='utf-8') as f:
                return yaml.safe_load(f) or {}
        except FileNotFoundError:
            return {}
        except yaml.YAMLError as e:
            raise ValueError(f"YAML 解析错误: {e}")

    def _save_yaml(self, data: Any) -> None:
        """保存 YAML 文件"""
        with open(self._config_path, 'w', encoding='utf-8') as f:
            yaml.safe_dump(data, f, allow_unicode=True, indent=2)

    def load(self) -> T:
        """加载配置"""
        data = self._load_yaml()
        return self._parse(data)

    def save(self, config: T) -> None:
        """保存配置"""
        data = self._serialize(config)
        self._save_yaml(data)

    def exists(self) -> bool:
        """检查配置文件是否存在"""
        return os.path.exists(self._config_path)

    def backup(self) -> str:
        """备份配置文件"""
        if self.exists():
            backup_path = f"{self._config_path}.backup"
            import shutil
            shutil.copy2(self._config_path, backup_path)
            return backup_path
        return ""

    @abstractmethod
    def _parse(self, data: dict) -> T:
        """解析 YAML 数据为配置对象"""
        pass

    @abstractmethod
    def _serialize(self, config: T) -> dict:
        """将配置对象序列化为字典"""
        pass


class AppConfigLoader(BaseConfigLoader[AppConfig]):
    """应用主配置加载器"""

    def __init__(self, config_dir: str | None = None):
        super().__init__('config.yaml', config_dir)

    def _parse(self, data: dict) -> AppConfig:
        """解析主配置数据"""
        return AppConfig(
            refresh_interval=data.get('refresh_interval', 30),
            theme=data.get('theme', 'dark'),
            default_fund_source=data.get('default_fund_source', 'sina'),
            max_history_points=data.get('max_history_points', 100),
            enable_auto_refresh=data.get('enable_auto_refresh', True),
            show_profit_loss=data.get('show_profit_loss', True),
        )

    def _serialize(self, config: AppConfig) -> dict:
        """序列化主配置对象"""
        return {
            'refresh_interval': config.refresh_interval,
            'theme': config.theme,
            'default_fund_source': config.default_fund_source,
            'max_history_points': config.max_history_points,
            'enable_auto_refresh': config.enable_auto_refresh,
            'show_profit_loss': config.show_profit_loss,
        }
