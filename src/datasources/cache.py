"""
数据缓存模块

提供简单的 TTL 缓存功能，用于缓存 API 响应数据，减少网络请求次数。
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class DataCache:
    """数据缓存管理器

    支持 TTL（Time To Live）过期的简单文件缓存。
    缓存数据以 JSON 格式存储在指定目录。
    """

    DEFAULT_TTL = 300  # 默认 TTL: 5 分钟

    def __init__(self, cache_dir: Path):
        """
        初始化缓存管理器

        Args:
            cache_dir: 缓存目录路径
        """
        self.cache_dir = Path(cache_dir)
        self._ensure_cache_dir()

    def _ensure_cache_dir(self):
        """确保缓存目录存在"""
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_cache_path(self, key: str) -> Path:
        """获取缓存文件路径"""
        # 使用 key 的哈希值作为文件名，避免文件名过长或包含非法字符
        import hashlib
        key_hash = hashlib.md5(key.encode()).hexdigest()
        return self.cache_dir / f"{key_hash}.json"

    def _is_expired(self, cache_path: Path, ttl_seconds: int) -> bool:
        """
        检查缓存是否过期

        Args:
            cache_path: 缓存文件路径
            ttl_seconds: TTL 时间（秒）

        Returns:
            bool: True 表示已过期，False 表示有效
        """
        if not cache_path.exists():
            return True

        # 读取缓存创建时间
        try:
            with open(cache_path, encoding='utf-8') as f:
                cache_data = json.load(f)
                created_at = datetime.fromisoformat(cache_data.get('created_at', ''))
                expires_at = created_at + timedelta(seconds=ttl_seconds)
                return datetime.now() >= expires_at
        except (json.JSONDecodeError, KeyError, ValueError):
            # 如果读取失败，视为过期
            return True

    def get(self, key: str) -> Any | None:
        """
        获取缓存数据

        Args:
            key: 缓存键

        Returns:
            Any: 缓存的数据，如果未命中或已过期返回 None
        """
        cache_path = self._get_cache_path(key)

        if not cache_path.exists():
            return None

        try:
            with open(cache_path, encoding='utf-8') as f:
                cache_data = json.load(f)

                # 检查是否过期
                ttl_seconds = cache_data.get('ttl', self.DEFAULT_TTL)
                created_at = datetime.fromisoformat(cache_data.get('created_at', ''))
                expires_at = created_at + timedelta(seconds=ttl_seconds)

                if datetime.now() >= expires_at:
                    # 已过期，删除缓存文件
                    self._remove_cache(cache_path)
                    return None

                return cache_data.get('value')

        except (json.JSONDecodeError, KeyError, ValueError, OSError):
            # 读取失败，返回 None
            return None

    def set(self, key: str, value: Any, ttl_seconds: int | None = None):
        """
        设置缓存数据

        Args:
            key: 缓存键
            value: 要缓存的数据（必须是 JSON 可序列化的）
            ttl_seconds: TTL 时间（秒），默认 5 分钟
        """
        if ttl_seconds is None:
            ttl_seconds = self.DEFAULT_TTL

        cache_path = self._get_cache_path(key)

        cache_data = {
            'key': key,
            'value': value,
            'ttl': ttl_seconds,
            'created_at': datetime.now().isoformat(),
            'expires_at': (datetime.now() + timedelta(seconds=ttl_seconds)).isoformat()
        }

        try:
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
        except (OSError, TypeError) as e:
            logger.warning(f"缓存写入失败 (key={key}): {e}")

    def clear(self, key: str | None = None):
        """
        清除缓存

        Args:
            key: 要清除的缓存键，如果为 None 则清除所有缓存
        """
        if key is None:
            # 清除所有缓存
            self._clear_all()
        else:
            # 清除单个缓存
            cache_path = self._get_cache_path(key)
            self._remove_cache(cache_path)

    def _remove_cache(self, cache_path: Path):
        """删除缓存文件"""
        try:
            cache_path.unlink(missing_ok=True)
        except OSError as e:
            logger.warning(f"缓存删除失败 (path={cache_path}): {e}")

    def _clear_all(self):
        """清除所有缓存文件"""
        try:
            # 删除缓存目录中的所有 .json 文件
            for cache_file in self.cache_dir.glob('*.json'):
                try:
                    cache_file.unlink()
                except OSError as e:
                    logger.warning(f"批量清除缓存失败 (file={cache_file}): {e}")
        except OSError as e:
            logger.warning(f"批量清除缓存失败 (dir={self.cache_dir}): {e}")

    def get_stats(self) -> dict:
        """
        获取缓存统计信息

        Returns:
            dict: 包含统计信息的字典
        """
        stats = {
            'cache_dir': str(self.cache_dir),
            'total_files': 0,
            'valid_files': 0,
            'expired_files': 0,
            'total_size_bytes': 0
        }

        try:
            for cache_file in self.cache_dir.glob('*.json'):
                stats['total_files'] += 1
                stats['total_size_bytes'] += cache_file.stat().st_size

                # 检查是否过期
                try:
                    with open(cache_file, encoding='utf-8') as f:
                        cache_data = json.load(f)
                        ttl_seconds = cache_data.get('ttl', self.DEFAULT_TTL)
                        created_at = datetime.fromisoformat(cache_data.get('created_at', ''))
                        expires_at = created_at + timedelta(seconds=ttl_seconds)

                        if datetime.now() >= expires_at:
                            stats['expired_files'] += 1
                        else:
                            stats['valid_files'] += 1
                except (json.JSONDecodeError, KeyError, ValueError):
                    stats['expired_files'] += 1

        except OSError:
            pass

        return stats

    def cleanup_expired(self) -> int:
        """
        清理过期的缓存文件

        Returns:
            int: 删除的过期缓存数量
        """
        cleaned = 0

        try:
            for cache_file in self.cache_dir.glob('*.json'):
                try:
                    with open(cache_file, encoding='utf-8') as f:
                        cache_data = json.load(f)
                        ttl_seconds = cache_data.get('ttl', self.DEFAULT_TTL)
                        created_at = datetime.fromisoformat(cache_data.get('created_at', ''))
                        expires_at = created_at + timedelta(seconds=ttl_seconds)

                        if datetime.now() >= expires_at:
                            cache_file.unlink()
                            cleaned += 1
                except (json.JSONDecodeError, KeyError, ValueError, OSError):
                    # 无法读取的文件也删除
                    try:
                        cache_file.unlink()
                        cleaned += 1
                    except OSError as e:
                        logger.warning(f"清理过期缓存失败 (file={cache_file}): {e}")
        except OSError:
            pass

        return cleaned
