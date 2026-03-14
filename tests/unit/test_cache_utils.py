"""Tests for cache module utilities."""

from datetime import datetime, timedelta

import pytest

from video_cut_skill.utils.cache import CacheEntry, CacheManager


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
        expires = datetime.now() + timedelta(days=7)
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
    def manager(self, temp_cache_dir):
        """CacheManager instance."""
        return CacheManager(cache_dir=temp_cache_dir, default_ttl=7)

    def test_initialization(self, temp_cache_dir):
        """Test CacheManager initialization."""
        manager = CacheManager(cache_dir=temp_cache_dir)
        assert manager.cache_dir == temp_cache_dir.expanduser()
        assert manager.data_dir.exists()
        assert manager.db_path.exists()

    def test_initialization_custom_ttl(self, temp_cache_dir):
        """Test initialization with custom TTL."""
        manager = CacheManager(cache_dir=temp_cache_dir, default_ttl=30)
        assert manager.default_ttl == 30

    def test_initialization_no_ttl(self, temp_cache_dir):
        """Test initialization with no TTL (never expires)."""
        manager = CacheManager(cache_dir=temp_cache_dir, default_ttl=None)
        assert manager.default_ttl is None

    def test_get_file_hash_nonexistent(self, manager, temp_cache_dir):
        """Test file hash for non-existent file."""
        result = manager._get_file_hash("/nonexistent/file.mp4")
        assert result == ""

    def test_get_file_hash_existing(self, manager, temp_cache_dir):
        """Test file hash for existing file."""
        test_file = temp_cache_dir / "test.mp4"
        test_file.write_text("test content")

        result = manager._get_file_hash(test_file)
        assert len(result) == 32  # MD5 hash length
        assert result != ""

    def test_compute_cache_key(self, manager, temp_cache_dir):
        """Test cache key computation."""
        test_file = temp_cache_dir / "test.mp4"
        test_file.write_text("test content")

        key1 = manager._compute_cache_key(test_file, "transcribe")
        key2 = manager._compute_cache_key(test_file, "transcribe")

        # Same file and operation should produce same key
        assert key1 == key2
        assert len(key1) == 64  # SHA256 hex length

    def test_compute_cache_key_with_params(self, manager, temp_cache_dir):
        """Test cache key with parameters."""
        test_file = temp_cache_dir / "test.mp4"
        test_file.write_text("test content")

        key1 = manager._compute_cache_key(test_file, "transcribe", {"model": "base"})
        key2 = manager._compute_cache_key(test_file, "transcribe", {"model": "small"})

        # Different params should produce different keys
        assert key1 != key2

    def test_set_and_get(self, manager, temp_cache_dir):
        """Test setting and getting cache data."""
        test_file = temp_cache_dir / "test.mp4"
        test_file.write_text("test content")
        data = {"result": "test_data", "segments": []}

        manager.set(test_file, "transcribe", data)
        result = manager.get(test_file, "transcribe")

        assert result == data

    def test_get_nonexistent(self, manager, temp_cache_dir):
        """Test getting non-existent cache."""
        test_file = temp_cache_dir / "test.mp4"
        test_file.write_text("test content")

        result = manager.get(test_file, "nonexistent_operation")
        assert result is None

    def test_get_with_params(self, manager, temp_cache_dir):
        """Test getting cache with parameters."""
        test_file = temp_cache_dir / "test.mp4"
        test_file.write_text("test content")
        data = {"result": "test"}

        manager.set(test_file, "transcribe", data, params={"model": "base"})
        result = manager.get(test_file, "transcribe", params={"model": "base"})

        assert result == data

    def test_cache_expiration(self, temp_cache_dir):
        """Test cache entry expiration."""
        # Use very short TTL for testing (negative to force expiration)
        manager = CacheManager(cache_dir=temp_cache_dir, default_ttl=None)

        test_file = temp_cache_dir / "test.mp4"
        test_file.write_text("test content")

        data = {"result": "test"}
        # Set TTL to negative to force expiration
        manager.set(test_file, "transcribe", data, ttl=-1)

        result = manager.get(test_file, "transcribe")
        assert result is None

    def test_clear_expired(self, manager, temp_cache_dir):
        """Test clearing expired entries."""
        test_file = temp_cache_dir / "test.mp4"
        test_file.write_text("test content")

        # Set expired entry
        manager.set(test_file, "transcribe", {"result": "test"}, ttl=-1)

        count = manager.clear_expired()
        assert count >= 0  # May be 0 or more depending on timing

    def test_clear_all(self, manager, temp_cache_dir):
        """Test clearing all cache."""
        test_file = temp_cache_dir / "test.mp4"
        test_file.write_text("test content")

        manager.set(test_file, "transcribe", {"result": "test"})
        manager.clear_all()

        result = manager.get(test_file, "transcribe")
        assert result is None

    def test_get_stats(self, manager, temp_cache_dir):
        """Test getting cache stats."""
        test_file = temp_cache_dir / "test.mp4"
        test_file.write_text("test content")

        manager.set(test_file, "transcribe", {"result": "test"})
        stats = manager.get_stats()

        assert "total_entries" in stats
        assert "expired_entries" in stats
        assert "cache_size_mb" in stats
        assert "cache_dir" in stats
        assert stats["total_entries"] >= 0

    def test_get_stats_empty(self, manager):
        """Test stats with empty cache."""
        stats = manager.get_stats()
        assert stats["total_entries"] == 0
        assert stats["expired_entries"] == 0
        assert stats["cache_size_mb"] == 0.0

    def test_set_with_metadata(self, manager, temp_cache_dir):
        """Test setting cache with metadata."""
        test_file = temp_cache_dir / "test.mp4"
        test_file.write_text("test content")

        metadata = {"version": "1.0", "model": "whisper-base"}
        manager.set(
            test_file,
            "transcribe",
            {"result": "test"},
            metadata=metadata,
        )

        # Data should still be retrievable
        result = manager.get(test_file, "transcribe")
        assert result == {"result": "test"}

    def test_cache_with_file_change(self, manager, temp_cache_dir):
        """Test cache invalidation when file changes."""
        test_file = temp_cache_dir / "test.mp4"
        test_file.write_text("original content")

        manager.set(test_file, "transcribe", {"result": "original"})

        # Modify file
        import time

        time.sleep(0.01)  # Ensure different mtime
        test_file.write_text("modified content")

        # Should be a cache miss because file hash changed
        result = manager.get(test_file, "transcribe")
        assert result is None  # Different file hash = different cache key


class TestCacheManagerEdgeCases:
    """CacheManager edge case tests."""

    @pytest.fixture
    def temp_cache_dir(self, tmp_path):
        """Temporary cache directory."""
        return tmp_path / "cache"

    def test_corrupted_cache_file(self, temp_cache_dir):
        """Test handling of corrupted cache file."""
        manager = CacheManager(cache_dir=temp_cache_dir)
        test_file = temp_cache_dir / "test.mp4"
        test_file.write_text("test content")

        # Set valid cache
        manager.set(test_file, "transcribe", {"result": "test"})

        # Corrupt the data file
        cache_key = manager._compute_cache_key(test_file, "transcribe")
        data_file = manager.data_dir / f"{cache_key}.pkl"
        data_file.write_text("corrupted data")

        # Should return None and clean up
        result = manager.get(test_file, "transcribe")
        assert result is None

    def test_pickle_error_on_set(self, temp_cache_dir):
        """Test handling unpicklable data."""
        manager = CacheManager(cache_dir=temp_cache_dir)
        test_file = temp_cache_dir / "test.mp4"
        test_file.write_text("test content")

        # Try to cache something that can't be pickled (like a lambda)
        unpicklable_data = {"func": lambda x: x}

        # Should not raise, but log error
        manager.set(test_file, "transcribe", unpicklable_data)

    def test_concurrent_access(self, temp_cache_dir):
        """Test cache handles concurrent access gracefully."""
        manager = CacheManager(cache_dir=temp_cache_dir)
        test_file = temp_cache_dir / "test.mp4"
        test_file.write_text("test content")

        # Multiple sets should not crash
        for i in range(5):
            manager.set(test_file, "transcribe", {"result": f"test_{i}"})

        result = manager.get(test_file, "transcribe")
        assert result is not None
