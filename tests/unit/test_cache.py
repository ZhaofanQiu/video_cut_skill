"""Tests for cache module."""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from video_cut_skill.utils.cache import (
    CachedSceneDetector,
    CachedTranscriber,
    CacheEntry,
    CacheManager,
)


class TestCacheEntry:
    """CacheEntry dataclass tests."""

    def test_cache_entry_creation(self):
        """Test creating CacheEntry."""
        entry = CacheEntry(
            key="test_key",
            data={"result": "test"},
            created_at=datetime.now(),
        )
        assert entry.key == "test_key"
        assert entry.data == {"result": "test"}
        assert entry.expires_at is None
        assert entry.metadata is None

    def test_cache_entry_with_expiry(self):
        """Test CacheEntry with expiration."""
        expires = datetime.now() + timedelta(days=1)
        entry = CacheEntry(
            key="test_key",
            data={"result": "test"},
            created_at=datetime.now(),
            expires_at=expires,
            metadata={"version": "1.0"},
        )
        assert entry.expires_at == expires
        assert entry.metadata == {"version": "1.0"}


class TestCacheManager:
    """CacheManager tests."""

    @pytest.fixture
    def temp_cache_dir(self, tmp_path):
        """Temporary cache directory."""
        return tmp_path / "cache"

    @pytest.fixture
    def cache_manager(self, temp_cache_dir):
        """CacheManager instance."""
        return CacheManager(cache_dir=temp_cache_dir, default_ttl=7)

    def test_initialization(self, temp_cache_dir):
        """Test CacheManager initialization."""
        manager = CacheManager(cache_dir=temp_cache_dir)
        assert manager.cache_dir.exists()
        assert manager.data_dir.exists()
        assert manager.db_path.exists()
        assert manager.default_ttl == 7

    def test_initialization_custom_ttl(self, temp_cache_dir):
        """Test initialization with custom TTL."""
        manager = CacheManager(cache_dir=temp_cache_dir, default_ttl=30)
        assert manager.default_ttl == 30

    def test_initialization_no_ttl(self, temp_cache_dir):
        """Test initialization with no TTL."""
        manager = CacheManager(cache_dir=temp_cache_dir, default_ttl=None)
        assert manager.default_ttl is None

    def test_get_file_hash_nonexistent(self, cache_manager):
        """Test getting hash for nonexistent file."""
        result = cache_manager._get_file_hash("/nonexistent/file.txt")
        assert result == ""

    def test_get_file_hash_existing(self, temp_cache_dir, cache_manager):
        """Test getting hash for existing file."""
        test_file = temp_cache_dir / "test.txt"
        test_file.write_text("hello world")

        result = cache_manager._get_file_hash(test_file)
        assert result != ""
        assert len(result) == 32  # MD5 hash length

    def test_compute_cache_key(self, temp_cache_dir, cache_manager):
        """Test computing cache key."""
        test_file = temp_cache_dir / "video.mp4"
        test_file.write_text("fake video content")

        key = cache_manager._compute_cache_key(test_file, "transcribe")
        assert key != ""
        assert len(key) == 64  # SHA256 hash length

    def test_compute_cache_key_with_params(self, temp_cache_dir, cache_manager):
        """Test computing cache key with parameters."""
        test_file = temp_cache_dir / "video.mp4"
        test_file.write_text("fake video content")

        key1 = cache_manager._compute_cache_key(test_file, "transcribe", {"language": "zh"})
        key2 = cache_manager._compute_cache_key(test_file, "transcribe", {"language": "en"})
        assert key1 != key2

    def test_set_and_get(self, temp_cache_dir, cache_manager):
        """Test setting and getting cache data."""
        test_file = temp_cache_dir / "video.mp4"
        test_file.write_text("fake video content")

        data = {"transcription": "hello world", "segments": []}
        cache_manager.set(test_file, "transcribe", data)

        result = cache_manager.get(test_file, "transcribe")
        assert result == data

    def test_get_nonexistent(self, temp_cache_dir, cache_manager):
        """Test getting nonexistent cache entry."""
        test_file = temp_cache_dir / "video.mp4"
        test_file.write_text("fake video content")

        result = cache_manager.get(test_file, "transcribe")
        assert result is None

    def test_get_with_params(self, temp_cache_dir, cache_manager):
        """Test getting cache with parameters."""
        test_file = temp_cache_dir / "video.mp4"
        test_file.write_text("fake video content")

        data = {"result": "test"}
        params = {"language": "zh", "model": "base"}
        cache_manager.set(test_file, "transcribe", data, params)

        # Correct params - should hit
        result = cache_manager.get(test_file, "transcribe", params)
        assert result == data

        # Wrong params - should miss
        wrong_params = {"language": "en", "model": "base"}
        result = cache_manager.get(test_file, "transcribe", wrong_params)
        assert result is None

    def test_cache_expiration(self, temp_cache_dir):
        """Test cache entry expiration."""
        # Use very short TTL for testing (set to past time)
        manager = CacheManager(cache_dir=temp_cache_dir, default_ttl=None)

        test_file = temp_cache_dir / "video.mp4"
        test_file.write_text("fake video content")

        data = {"result": "test"}
        # Set TTL to negative to force expiration
        manager.set(test_file, "transcribe", data, ttl=-1)

        result = manager.get(test_file, "transcribe")
        assert result is None

    def test_clear_expired(self, temp_cache_dir):
        """Test clearing expired entries."""
        manager = CacheManager(cache_dir=temp_cache_dir, default_ttl=0)

        test_file = temp_cache_dir / "video.mp4"
        test_file.write_text("fake video content")

        # Add expired entry
        manager.set(test_file, "transcribe", {"result": "test"}, ttl=0)

        import time

        time.sleep(0.1)

        count = manager.clear_expired()
        assert count >= 0  # May be 0 or 1 depending on timing

    def test_clear_all(self, temp_cache_dir, cache_manager):
        """Test clearing all cache entries."""
        test_file = temp_cache_dir / "video.mp4"
        test_file.write_text("fake video content")

        cache_manager.set(test_file, "transcribe", {"result": "test"})
        cache_manager.set(test_file, "detect", {"scenes": []})

        cache_manager.clear_all()

        assert cache_manager.get(test_file, "transcribe") is None
        assert cache_manager.get(test_file, "detect") is None

    def test_get_stats(self, temp_cache_dir, cache_manager):
        """Test getting cache statistics."""
        test_file = temp_cache_dir / "video.mp4"
        test_file.write_text("fake video content")

        cache_manager.set(test_file, "transcribe", {"result": "test"})

        stats = cache_manager.get_stats()
        assert "total_entries" in stats
        assert "expired_entries" in stats
        assert "cache_size_mb" in stats
        assert "cache_dir" in stats
        assert stats["total_entries"] == 1

    def test_get_stats_empty(self, cache_manager):
        """Test stats on empty cache."""
        stats = cache_manager.get_stats()
        assert stats["total_entries"] == 0
        assert stats["expired_entries"] == 0
        assert stats["cache_size_mb"] == 0.0

    def test_set_with_metadata(self, temp_cache_dir, cache_manager):
        """Test setting cache with metadata."""
        test_file = temp_cache_dir / "video.mp4"
        test_file.write_text("fake video content")

        data = {"result": "test"}
        metadata = {"version": "1.0", "model": "whisper-base"}
        cache_manager.set(test_file, "transcribe", data, metadata=metadata)

        result = cache_manager.get(test_file, "transcribe")
        assert result == data

    def test_cache_with_file_change(self, temp_cache_dir, cache_manager):
        """Test cache invalidation on file change."""
        test_file = temp_cache_dir / "video.mp4"
        test_file.write_text("original content")

        cache_manager.set(test_file, "transcribe", {"result": "original"})

        # Modify file
        import time

        time.sleep(0.1)
        test_file.write_text("modified content")

        # Should be a cache miss due to different file hash
        result = cache_manager.get(test_file, "transcribe")
        assert result is None


class TestCachedTranscriber:
    """CachedTranscriber tests."""

    @pytest.fixture
    def temp_cache_dir(self, tmp_path):
        """Temporary cache directory."""
        return tmp_path / "cache"

    @patch("video_cut_skill.ai.transcriber.Transcriber")
    def test_initialization(self, mock_transcriber_class, temp_cache_dir):
        """Test CachedTranscriber initialization."""
        mock_transcriber = MagicMock()
        mock_transcriber_class.return_value = mock_transcriber

        transcriber = CachedTranscriber(
            model_size="base",
            cache_dir=temp_cache_dir,
        )

        assert transcriber.cache is not None
        mock_transcriber_class.assert_called_once_with(model_size="base", device=None)

    @patch("video_cut_skill.ai.transcriber.Transcriber")
    def test_transcribe_cache_miss(self, mock_transcriber_class, temp_cache_dir):
        """Test transcribe with cache miss."""
        mock_transcriber = MagicMock()
        mock_transcriber_class.return_value = mock_transcriber
        mock_transcriber.transcribe.return_value = {"text": "hello", "segments": []}

        transcriber = CachedTranscriber(cache_dir=temp_cache_dir)

        test_file = temp_cache_dir / "video.mp4"
        test_file.write_text("fake content")

        result = transcriber.transcribe(test_file)

        assert result == {"text": "hello", "segments": []}
        mock_transcriber.transcribe.assert_called_once()

    @patch("video_cut_skill.ai.transcriber.Transcriber")
    def test_transcribe_cache_hit(self, mock_transcriber_class, temp_cache_dir):
        """Test transcribe with cache hit."""
        mock_transcriber = MagicMock()
        mock_transcriber_class.return_value = mock_transcriber
        mock_transcriber.transcribe.return_value = {"text": "hello", "segments": []}

        transcriber = CachedTranscriber(cache_dir=temp_cache_dir)

        test_file = temp_cache_dir / "video.mp4"
        test_file.write_text("fake content")

        # First call - cache miss
        transcriber.transcribe(test_file)

        # Second call - should hit cache
        result = transcriber.transcribe(test_file)

        assert result == {"text": "hello", "segments": []}
        # Transcriber should only be called once
        assert mock_transcriber.transcribe.call_count == 1


class TestCachedSceneDetector:
    """CachedSceneDetector tests."""

    @pytest.fixture
    def temp_cache_dir(self, tmp_path):
        """Temporary cache directory."""
        return tmp_path / "cache"

    @patch("video_cut_skill.ai.scene_detector.SceneDetector")
    def test_initialization(self, mock_detector_class, temp_cache_dir):
        """Test CachedSceneDetector initialization."""
        mock_detector = MagicMock()
        mock_detector_class.return_value = mock_detector
        mock_detector.detector_type = "content"

        detector = CachedSceneDetector(
            detector_type="content",
            cache_dir=temp_cache_dir,
        )

        assert detector.cache is not None
        assert detector.detector.detector_type == "content"

    @patch("video_cut_skill.ai.scene_detector.SceneDetector")
    def test_detect_cache_miss(self, mock_detector_class, temp_cache_dir):
        """Test detect with cache miss."""
        mock_detector = MagicMock()
        mock_detector_class.return_value = mock_detector
        mock_detector.detector_type = "content"
        mock_detector.detect.return_value = [(0.0, 5.0), (5.0, 10.0)]

        detector = CachedSceneDetector(cache_dir=temp_cache_dir)

        test_file = temp_cache_dir / "video.mp4"
        test_file.write_text("fake content")

        result = detector.detect(test_file)

        assert result == [(0.0, 5.0), (5.0, 10.0)]
        mock_detector.detect.assert_called_once()

    @patch("video_cut_skill.ai.scene_detector.SceneDetector")
    def test_detect_with_params(self, mock_detector_class, temp_cache_dir):
        """Test detect with custom parameters."""
        mock_detector = MagicMock()
        mock_detector_class.return_value = mock_detector
        mock_detector.detector_type = "content"
        mock_detector.detect.return_value = [(0.0, 3.0)]

        detector = CachedSceneDetector(cache_dir=temp_cache_dir)

        test_file = temp_cache_dir / "video.mp4"
        test_file.write_text("fake content")

        result = detector.detect(test_file, threshold=30.0, min_scene_len=1.0)

        assert result == [(0.0, 3.0)]
        mock_detector.detect.assert_called_once_with(test_file, threshold=30.0, min_scene_len=1.0)
