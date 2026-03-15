"""Multi-level cache system for video cut skill."""

import pickle
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional

from video_cut_skill.config import get_config
from video_cut_skill.exceptions import CacheError


class MultiLevelCache:
    """Three-level cache: memory -> disk -> semantic.

    Level 1: In-memory cache (current session)
    Level 2: Disk cache (persisted, TTL-based)
    Level 3: Semantic cache (reusable across sessions)
    """

    def __init__(self, cache_dir: Optional[Path] = None):
        """Initialize cache.

        Args:
            cache_dir: Directory for disk cache. Defaults to config setting.
        """
        config = get_config()

        # L1: Memory cache
        self._memory_cache: Dict[str, Any] = {}

        # L2: Disk cache
        if cache_dir:
            self._cache_dir = cache_dir
        else:
            self._cache_dir = config.session.get_cache_path() / "cache"
        self._cache_dir.mkdir(parents=True, exist_ok=True)

        self._transcribe_ttl = timedelta(hours=config.cost_control.transcribe_ttl_hours)
        self._semantics_ttl = timedelta(hours=config.cost_control.semantics_ttl_hours)
        self._enabled = config.cost_control.cache_enabled

    def _get_cache_key(self, video_hash: str, data_type: str) -> str:
        """Generate cache key."""
        return f"{data_type}_{video_hash}"

    def _get_cache_path(self, key: str) -> Path:
        """Get disk cache file path."""
        return self._cache_dir / f"{key}.pkl"

    def _is_valid(self, cache_path: Path, ttl: timedelta) -> bool:
        """Check if cache entry is still valid."""
        if not cache_path.exists():
            return False

        mtime = datetime.fromtimestamp(cache_path.stat().st_mtime)
        return datetime.now() - mtime < ttl

    # ========== Transcription Cache ==========

    def get_transcription(self, video_hash: str) -> Optional[Any]:
        """Get cached transcription result.

        Args:
            video_hash: Video file hash

        Returns:
            Cached transcription or None
        """
        if not self._enabled:
            return None

        key = self._get_cache_key(video_hash, "transcription")

        # L1: Memory
        if key in self._memory_cache:
            return self._memory_cache[key]

        # L2: Disk
        cache_path = self._get_cache_path(key)
        if self._is_valid(cache_path, self._transcribe_ttl):
            try:
                with open(cache_path, "rb") as f:
                    data = pickle.load(f)
                # Promote to memory
                self._memory_cache[key] = data
                return data
            except Exception:
                # Cache corrupted, ignore
                pass

        return None

    def set_transcription(self, video_hash: str, data: Any) -> None:
        """Cache transcription result.

        Args:
            video_hash: Video file hash
            data: Transcription data to cache
        """
        if not self._enabled:
            return

        key = self._get_cache_key(video_hash, "transcription")

        # L1: Memory
        self._memory_cache[key] = data

        # L2: Disk
        cache_path = self._get_cache_path(key)
        try:
            with open(cache_path, "wb") as f:
                pickle.dump(data, f)
        except Exception as e:
            raise CacheError(f"Failed to cache transcription: {e}") from e

    # ========== Semantics Cache ==========

    def get_semantics(self, video_hash: str) -> Optional[Any]:
        """Get cached semantic analysis.

        Args:
            video_hash: Video file hash

        Returns:
            Cached semantics or None
        """
        if not self._enabled:
            return None

        key = self._get_cache_key(video_hash, "semantics")

        # L1: Memory
        if key in self._memory_cache:
            return self._memory_cache[key]

        # L2: Disk
        cache_path = self._get_cache_path(key)
        if self._is_valid(cache_path, self._semantics_ttl):
            try:
                with open(cache_path, "rb") as f:
                    data = pickle.load(f)
                self._memory_cache[key] = data
                return data
            except Exception:
                pass

        return None

    def set_semantics(self, video_hash: str, data: Any) -> None:
        """Cache semantic analysis.

        Args:
            video_hash: Video file hash
            data: Semantic data to cache
        """
        if not self._enabled:
            return

        key = self._get_cache_key(video_hash, "semantics")

        # L1: Memory
        self._memory_cache[key] = data

        # L2: Disk
        cache_path = self._get_cache_path(key)
        try:
            with open(cache_path, "wb") as f:
                pickle.dump(data, f)
        except Exception as e:
            raise CacheError(f"Failed to cache semantics: {e}") from e

    # ========== Utility Methods ==========

    def clear_memory(self) -> None:
        """Clear memory cache."""
        self._memory_cache.clear()

    def clear_disk(self) -> None:
        """Clear all disk cache."""
        for cache_file in self._cache_dir.glob("*.pkl"):
            cache_file.unlink()

    def clear_all(self) -> None:
        """Clear all caches."""
        self.clear_memory()
        self.clear_disk()

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        disk_size = sum(f.stat().st_size for f in self._cache_dir.glob("*.pkl"))

        return {
            "memory_entries": len(self._memory_cache),
            "disk_entries": len(list(self._cache_dir.glob("*.pkl"))),
            "disk_size_mb": disk_size / (1024 * 1024),
            "cache_dir": str(self._cache_dir),
        }
