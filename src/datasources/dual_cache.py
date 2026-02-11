"""
双层缓存模块

L1: 内存缓存 (快速，TTL 短)
L2: 文件缓存 (持久化，TTL 长)
"""

import asyncio
import hashlib
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class MemoryCache:
    """L1 内存缓存 (LRU)"""

    def __init__(self, max_size: int = 1000, ttl_seconds: int = 60):
        """
        Args:
            max_size: 最大缓存条目数
            ttl_seconds: TTL 时间（秒）
        """
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._cache: dict[str, dict] = {}
        self._access_order: list[str] = []
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Any | None:
        """获取缓存"""
        async with self._lock:
            if key not in self._cache:
                return None

            entry = self._cache[key]
            # 检查 TTL
            if datetime.now() >= entry["expires_at"]:
                self._remove(key)
                return None

            # 更新访问顺序
            self._access_order.remove(key)
            self._access_order.append(key)

            return entry["value"]

    async def set(self, key: str, value: Any, ttl_seconds: int | None = None):
        """设置缓存"""
        ttl = ttl_seconds or self.ttl_seconds

        async with self._lock:
            # LRU 淘汰
            while len(self._cache) >= self.max_size and self._access_order:
                oldest = self._access_order.pop(0)
                self._cache.pop(oldest, None)

            # 移除旧值
            self._cache.pop(key, None)

            # 添加新值
            self._cache[key] = {
                "value": value,
                "expires_at": datetime.now() + timedelta(seconds=ttl)
            }

            # 更新访问顺序
            if key in self._access_order:
                self._access_order.remove(key)
            self._access_order.append(key)

    def _remove(self, key: str):
        """移除缓存"""
        self._cache.pop(key, None)
        if key in self._access_order:
            self._access_order.remove(key)

    def clear(self):
        """清空缓存"""
        self._cache.clear()
        self._access_order.clear()


class DualLayerCache:
    """双层缓存 (L1 内存 + L2 文件)"""

    def __init__(
        self,
        cache_dir: Path,
        memory_ttl: int = 60,
        file_ttl: int = 300,
        max_memory_items: int = 1000
    ):
        """
        Args:
            cache_dir: 文件缓存目录
            memory_ttl: 内存缓存 TTL（秒）
            file_ttl: 文件缓存 TTL（秒）
            max_memory_items: 最大内存缓存条目数
        """
        self.cache_dir = Path(cache_dir)
        self.file_ttl = file_ttl
        self.memory_cache = MemoryCache(max_size=max_memory_items, ttl_seconds=memory_ttl)
        self._ensure_cache_dir()
        self._lock = asyncio.Lock()

    def _ensure_cache_dir(self):
        """确保缓存目录存在"""
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_file_key(self, key: str) -> str:
        """生成文件名"""
        return hashlib.md5(key.encode()).hexdigest()

    async def get(self, key: str) -> tuple[Any | None, str]:
        """
        获取缓存

        Returns:
            (value, cache_type): 值和缓存类型 ('memory', 'file', None)
        """
        # L1: 内存缓存
        value = await self.memory_cache.get(key)
        if value is not None:
            return value, "memory"

        # L2: 文件缓存
        file_key = self._get_file_key(key)
        file_path = self.cache_dir / f"{file_key}.json"

        if not file_path.exists():
            return None, None

        try:
            with open(file_path, encoding='utf-8') as f:
                cache_data = json.load(f)
                created_at = datetime.fromisoformat(cache_data.get('created_at', ''))
                expires_at = created_at + timedelta(seconds=self.file_ttl)

                if datetime.now() >= expires_at:
                    # 过期，删除文件
                    file_path.unlink(missing_ok=True)
                    return None, None

                value = cache_data.get('value')
                # 回填 L1 缓存
                await self.memory_cache.set(key, value, self.file_ttl)
                return value, "file"

        except (json.JSONDecodeError, KeyError, ValueError, OSError):
            return None, None

    async def set(self, key: str, value: Any, ttl_seconds: int | None = None):
        """设置缓存"""
        ttl = ttl_seconds or self.file_ttl

        # L1: 内存缓存
        await self.memory_cache.set(key, value, ttl)

        # L2: 文件缓存
        file_key = self._get_file_key(key)
        file_path = self.cache_dir / f"{file_key}.json"

        cache_data = {
            'key': key,
            'value': value,
            'ttl': ttl,
            'created_at': datetime.now().isoformat(),
            'expires_at': (datetime.now() + timedelta(seconds=ttl)).isoformat()
        }

        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
        except (OSError, TypeError) as e:
            logger.warning(f"缓存写入失败 (key={key}): {e}")

    async def delete(self, key: str):
        """删除缓存"""
        # L1
        self.memory_cache.clear()  # 简化：清空 L1（因为 key 可能被 LRU 淘汰）

        # L2
        file_key = self._get_file_key(key)
        file_path = self.cache_dir / f"{file_key}.json"
        file_path.unlink(missing_ok=True)

    async def clear(self):
        """清空所有缓存"""
        self.memory_cache.clear()

        for cache_file in self.cache_dir.glob('*.json'):
            try:
                cache_file.unlink()
            except OSError:
                pass

    def get_stats(self) -> dict:
        """获取缓存统计"""
        total_files = 0
        valid_files = 0
        total_size = 0

        for cache_file in self.cache_dir.glob('*.json'):
            total_files += 1
            total_size += cache_file.stat().st_size

            try:
                with open(cache_file, encoding='utf-8') as f:
                    cache_data = json.load(f)
                    ttl = cache_data.get('ttl', self.file_ttl)
                    created_at = datetime.fromisoformat(cache_data.get('created_at', ''))
                    expires_at = created_at + timedelta(seconds=ttl)

                    if datetime.now() < expires_at:
                        valid_files += 1
            except (json.JSONDecodeError, KeyError, ValueError, OSError):
                pass

        return {
            "memory_cache_size": len(self.memory_cache._cache),
            "file_cache_total": total_files,
            "file_cache_valid": valid_files,
            "file_cache_size_bytes": total_size
        }
