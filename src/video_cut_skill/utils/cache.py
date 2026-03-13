"""Caching system for video_cut_skill - 缓存系统.

提供转录结果、场景检测结果等计算密集型操作的缓存功能.
"""

import hashlib
import json
import logging
import pickle
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional, TypeVar, Union

logger = logging.getLogger(__name__)

T = TypeVar("T")


@dataclass
class CacheEntry:
    """缓存条目."""

    key: str
    data: Any
    created_at: datetime
    expires_at: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None


class CacheManager:
    """缓存管理器.

    使用 SQLite 存储缓存元数据，文件系统存储实际数据.
    """

    def __init__(
        self,
        cache_dir: Union[str, Path] = "~/.cache/video_cut_skill",
        default_ttl: Optional[int] = 7,  # 默认7天过期
    ):
        """初始化缓存管理器.

        Args:
            cache_dir: 缓存目录
            default_ttl: 默认过期时间（天），None表示永不过期
        """
        self.cache_dir = Path(cache_dir).expanduser()
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.default_ttl = default_ttl

        # 数据存储目录
        self.data_dir = self.cache_dir / "data"
        self.data_dir.mkdir(exist_ok=True)

        # 初始化 SQLite
        self.db_path = self.cache_dir / "cache.db"
        self._init_db()

        logger.info(f"Cache initialized at {self.cache_dir}")

    def _init_db(self) -> None:
        """初始化数据库."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cache (
                    key TEXT PRIMARY KEY,
                    data_path TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    expires_at TEXT,
                    metadata TEXT,
                    file_hash TEXT
                )
                """)
            conn.commit()

    def _get_file_hash(self, file_path: Union[str, Path]) -> str:
        """计算文件哈希（用于检测文件是否变更）.

        使用文件大小+修改时间的组合作为快速哈希.
        对于大文件，这比完整内容哈希快得多.
        """
        path = Path(file_path)
        if not path.exists():
            return ""

        stat = path.stat()
        # 使用大小+修改时间作为哈希输入
        hash_input = f"{stat.st_size}:{stat.st_mtime}"
        return hashlib.md5(hash_input.encode()).hexdigest()

    def _compute_cache_key(
        self,
        file_path: Union[str, Path],
        operation: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> str:
        """计算缓存键.

        Args:
            file_path: 输入文件路径
            operation: 操作类型 (transcribe/detect_scenes/etc)
            params: 操作参数

        Returns:
            缓存键
        """
        file_hash = self._get_file_hash(file_path)
        key_input = f"{file_hash}:{operation}"

        if params:
            # 将参数排序后序列化，确保相同参数产生相同键
            params_str = json.dumps(params, sort_keys=True)
            key_input += f":{params_str}"

        return hashlib.sha256(key_input.encode()).hexdigest()

    def get(
        self,
        file_path: Union[str, Path],
        operation: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Optional[Any]:
        """获取缓存数据.

        Args:
            file_path: 输入文件路径
            operation: 操作类型
            params: 操作参数

        Returns:
            缓存的数据，如果不存在或已过期则返回 None
        """
        cache_key = self._compute_cache_key(file_path, operation, params)

        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT data_path, expires_at FROM cache WHERE key = ?",
                (cache_key,),
            ).fetchone()

            if not row:
                return None

            data_path, expires_at_str = row

            # 检查是否过期
            if expires_at_str:
                expires_at = datetime.fromisoformat(expires_at_str)
                if datetime.now() > expires_at:
                    logger.debug(f"Cache expired for {operation}")
                    self._remove_entry(cache_key, data_path)
                    return None

            # 加载数据
            try:
                full_path = self.cache_dir / data_path
                with open(full_path, "rb") as f:
                    data = pickle.load(f)
                logger.debug(f"Cache hit for {operation}")
                return data
            except Exception as e:
                logger.warning(f"Failed to load cache: {e}")
                self._remove_entry(cache_key, data_path)
                return None

    def set(
        self,
        file_path: Union[str, Path],
        operation: str,
        data: Any,
        params: Optional[Dict[str, Any]] = None,
        ttl: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """设置缓存数据.

        Args:
            file_path: 输入文件路径
            operation: 操作类型
            data: 要缓存的数据
            params: 操作参数
            ttl: 过期时间（天），None使用默认值
            metadata: 额外元数据
        """
        cache_key = self._compute_cache_key(file_path, operation, params)

        # 保存数据到文件
        data_path = self.data_dir / f"{cache_key}.pkl"
        try:
            with open(data_path, "wb") as f:
                pickle.dump(data, f)
        except Exception as e:
            logger.error(f"Failed to save cache: {e}")
            return

        # 计算过期时间
        ttl = ttl if ttl is not None else self.default_ttl
        expires_at = datetime.now() + timedelta(days=ttl) if ttl else None

        # 保存元数据到数据库
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO cache
                (key, data_path, created_at, expires_at, metadata, file_hash)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    cache_key,
                    str(data_path.relative_to(self.cache_dir)),
                    datetime.now().isoformat(),
                    expires_at.isoformat() if expires_at else None,
                    json.dumps(metadata) if metadata else None,
                    self._get_file_hash(file_path),
                ),
            )
            conn.commit()

        logger.debug(f"Cache set for {operation}")

    def _remove_entry(self, key: str, data_path: str) -> None:
        """移除缓存条目."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM cache WHERE key = ?", (key,))
            conn.commit()

        # 删除数据文件
        (self.cache_dir / data_path).unlink(missing_ok=True)

    def clear_expired(self) -> int:
        """清理过期缓存.

        Returns:
            清理的条目数
        """
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT key, data_path FROM cache WHERE expires_at < ?",
                (datetime.now().isoformat(),),
            ).fetchall()

            count = 0
            for key, data_path in rows:
                self._remove_entry(key, data_path)
                count += 1

        if count > 0:
            logger.info(f"Cleared {count} expired cache entries")
        return count

    def clear_all(self) -> None:
        """清空所有缓存."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM cache")
            conn.commit()

        # 删除所有数据文件
        for f in self.data_dir.glob("*.pkl"):
            f.unlink(missing_ok=True)

        logger.info("Cache cleared")

    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息."""
        with sqlite3.connect(self.db_path) as conn:
            total = conn.execute("SELECT COUNT(*) FROM cache").fetchone()[0]
            expired = conn.execute(
                "SELECT COUNT(*) FROM cache WHERE expires_at < ?",
                (datetime.now().isoformat(),),
            ).fetchone()[0]

        # 计算缓存大小
        total_size = sum(f.stat().st_size for f in self.data_dir.glob("*.pkl"))

        return {
            "total_entries": total,
            "expired_entries": expired,
            "cache_size_mb": round(total_size / (1024 * 1024), 2),
            "cache_dir": str(self.cache_dir),
        }


class CachedTranscriber:
    """带缓存的语音识别器.

    包装 Transcriber，自动缓存转录结果.
    """

    def __init__(
        self,
        model_size: str = "base",
        device: Optional[str] = None,
        cache_dir: Union[str, Path] = "~/.cache/video_cut_skill",
        cache_ttl: int = 7,
    ):
        """初始化.

        Args:
            model_size: Whisper模型大小
            device: 计算设备
            cache_dir: 缓存目录
            cache_ttl: 缓存过期时间（天）
        """
        from video_cut_skill.ai.transcriber import Transcriber

        self.transcriber = Transcriber(model_size=model_size, device=device)
        self.cache = CacheManager(cache_dir, default_ttl=cache_ttl)

    def transcribe(
        self,
        video_path: Union[str, Path],
        language: Optional[str] = None,
        word_timestamps: bool = True,
        **kwargs,
    ) -> Any:
        """转录音视频（带缓存）."""
        params = {
            "language": language,
            "word_timestamps": word_timestamps,
            **kwargs,
        }

        # 尝试从缓存获取
        cached = self.cache.get(video_path, "transcribe", params)
        if cached is not None:
            logger.info(f"Using cached transcription for {video_path}")
            return cached

        # 执行转录
        result = self.transcriber.transcribe(
            video_path,
            language=language,
            word_timestamps=word_timestamps,
            **kwargs,
        )

        # 保存到缓存
        self.cache.set(video_path, "transcribe", result, params)

        return result


class CachedSceneDetector:
    """带缓存的场景检测器.

    包装 SceneDetector，自动缓存检测结果.
    """

    def __init__(
        self,
        detector_type: str = "content",
        cache_dir: Union[str, Path] = "~/.cache/video_cut_skill",
        cache_ttl: int = 7,
    ):
        """初始化.

        Args:
            detector_type: 检测器类型
            cache_dir: 缓存目录
            cache_ttl: 缓存过期时间（天）
        """
        from video_cut_skill.ai.scene_detector import SceneDetector

        self.detector = SceneDetector(detector_type=detector_type)
        self.cache = CacheManager(cache_dir, default_ttl=cache_ttl)

    def detect(
        self,
        video_path: Union[str, Path],
        threshold: float = 27.0,
        min_scene_len: float = 0.5,
        **kwargs,
    ) -> Any:
        """检测场景（带缓存）."""
        params = {
            "threshold": threshold,
            "min_scene_len": min_scene_len,
            "detector_type": self.detector.detector_type,
            **kwargs,
        }

        # 尝试从缓存获取
        cached = self.cache.get(video_path, "detect_scenes", params)
        if cached is not None:
            logger.info(f"Using cached scene detection for {video_path}")
            return cached

        # 执行检测
        result = self.detector.detect(
            video_path,
            threshold=threshold,
            min_scene_len=min_scene_len,
            **kwargs,
        )

        # 保存到缓存
        self.cache.set(video_path, "detect_scenes", result, params)

        return result
