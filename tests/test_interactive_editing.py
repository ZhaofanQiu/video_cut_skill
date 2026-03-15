#!/usr/bin/env python3
"""Unit tests for interactive video editing features."""

import os
import sys
import tempfile
import unittest
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../src"))

# Set test API key
os.environ["DASHSCOPE_API_KEY"] = os.getenv("DASHSCOPE_API_KEY", "test-key")

from video_cut_skill.models import (
    ContentSegment,
    EditSession,
    EditStrategy,
    AgentResponse,
    SegmentType,
)
from video_cut_skill.models.semantic import VideoSemantics, TranscriptionResult, Sentence
from video_cut_skill.core.session_manager import SessionManager
from video_cut_skill.core.cache import MultiLevelCache
from video_cut_skill.core.cost_guardian import CostGuardian


class TestSemanticModels(unittest.TestCase):
    """Test semantic data models."""

    def test_content_segment_creation(self):
        """Test ContentSegment creation."""
        segment = ContentSegment(
            segment_id="seg_0",
            start_time=0.0,
            end_time=10.0,
            duration=10.0,
            text="Hello world",
            summary="A greeting",
            keywords=["hello", "world"],
        )
        self.assertEqual(segment.segment_id, "seg_0")
        self.assertEqual(segment.duration, 10.0)

    def test_video_semantics_search(self):
        """Test VideoSemantics keyword search."""
        segments = [
            ContentSegment(
                segment_id="seg_0",
                start_time=0.0,
                end_time=10.0,
                duration=10.0,
                text="This is about AI technology",
                keywords=["AI", "technology"],
            ),
            ContentSegment(
                segment_id="seg_1",
                start_time=10.0,
                end_time=20.0,
                duration=10.0,
                text="This is about business",
                keywords=["business"],
            ),
        ]
        semantics = VideoSemantics(
            video_path="test.mp4",
            video_hash="abc123",
            duration=20.0,
            segments=segments,
        )
        
        results = semantics.search_by_keyword("AI")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].segment_id, "seg_0")


class TestSessionManager(unittest.TestCase):
    """Test SessionManager functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.manager = SessionManager(cache_dir=Path(self.temp_dir))

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_create_and_get_session(self):
        """Test session creation and retrieval."""
        # Create a dummy video file
        video_path = os.path.join(self.temp_dir, "test.mp4")
        with open(video_path, "w") as f:
            f.write("dummy")

        session_id = self.manager.create_session(video_path)
        self.assertIsNotNone(session_id)

        session = self.manager.get_session(session_id)
        self.assertIsNotNone(session)
        self.assertEqual(session.video_path, video_path)

    def test_session_persistence(self):
        """Test session persistence to disk."""
        video_path = os.path.join(self.temp_dir, "test.mp4")
        with open(video_path, "w") as f:
            f.write("dummy")

        session_id = self.manager.create_session(video_path)
        
        # Create new manager instance (simulating restart)
        new_manager = SessionManager(cache_dir=Path(self.temp_dir))
        session = new_manager.get_session(session_id)
        
        self.assertIsNotNone(session)
        self.assertEqual(session.video_path, video_path)


class TestCostGuardian(unittest.TestCase):
    """Test CostGuardian functionality."""

    def test_check_analyze(self):
        """Test cost check for analysis."""
        guardian = CostGuardian()
        
        # Short video should not require confirmation
        result = guardian.check_analyze("test.mp4", 300)  # 5 minutes
        self.assertFalse(result.requires_confirmation)
        
        # Long video should require confirmation
        result = guardian.check_analyze("test.mp4", 3600)  # 60 minutes
        self.assertTrue(result.requires_confirmation)

    def test_estimate_summary_cost(self):
        """Test summary cost estimation."""
        guardian = CostGuardian()
        cost = guardian.estimate_summary_cost(50)
        self.assertGreater(cost, 0)


class TestAgentResponse(unittest.TestCase):
    """Test AgentResponse factory methods."""

    def test_ready_for_edit(self):
        """Test ready_for_edit response."""
        response = AgentResponse.ready_for_edit(
            segment_count=5,
            duration=60.0,
            topics=["技术", "商业"],
        )
        self.assertEqual(response.state, "ready")
        self.assertEqual(response.data["segment_count"], 5)

    def test_awaiting_confirmation(self):
        """Test awaiting_confirmation response."""
        response = AgentResponse.awaiting_confirmation(
            strategy_description="Test strategy",
            target_duration=60.0,
            keep_count=3,
            cost=1.5,
        )
        self.assertEqual(response.state, "awaiting_confirm")
        self.assertEqual(response.data["estimated_cost"], 1.5)

    def test_completed(self):
        """Test completed response."""
        response = AgentResponse.completed(
            output_path="/tmp/output.mp4",
            output_duration=60.0,
        )
        self.assertEqual(response.state, "completed")
        self.assertEqual(response.data["output_path"], "/tmp/output.mp4")


class TestCache(unittest.TestCase):
    """Test MultiLevelCache functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.cache = MultiLevelCache(cache_dir=Path(self.temp_dir))

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_cache_operations(self):
        """Test basic cache operations."""
        video_hash = "test_hash_123"
        data = {"text": "test transcription"}

        # Store
        self.cache.set_semantics(video_hash, data)

        # Retrieve
        cached = self.cache.get_semantics(video_hash)
        self.assertIsNotNone(cached)
        self.assertEqual(cached["text"], "test transcription")

        # Non-existent key
        cached = self.cache.get_semantics("non_existent")
        self.assertIsNone(cached)


def run_tests():
    """Run all tests."""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(TestSemanticModels))
    suite.addTests(loader.loadTestsFromTestCase(TestSessionManager))
    suite.addTests(loader.loadTestsFromTestCase(TestCostGuardian))
    suite.addTests(loader.loadTestsFromTestCase(TestAgentResponse))
    suite.addTests(loader.loadTestsFromTestCase(TestCache))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
