"""Tests for SceneDetector."""

import pytest

from video_cut_skill.ai.scene_detector import (
    Scene,
    SceneDetectionResult,
    SceneDetector,
)


class TestScene:
    """Scene 测试."""

    def test_creation(self):
        """测试创建场景."""
        scene = Scene(
            start=0.0,
            end=10.0,
            start_frame=0,
            end_frame=300,
        )
        assert scene.start == 0.0
        assert scene.end == 10.0
        assert scene.duration == 10.0
        assert scene.frame_count == 300


class TestSceneDetectionResult:
    """SceneDetectionResult 测试."""

    def test_creation(self):
        """测试创建结果."""
        scenes = [
            Scene(start=0, end=10, start_frame=0, end_frame=300),
            Scene(start=10, end=20, start_frame=300, end_frame=600),
        ]
        result = SceneDetectionResult(
            scenes=scenes,
            video_path="test.mp4",
            detector_type="content",
            total_duration=20.0,
        )
        assert result.scene_count == 2
        assert result.detector_type == "content"

    def test_get_scene_at_time(self):
        """测试获取时间点场景."""
        scenes = [
            Scene(start=0, end=10, start_frame=0, end_frame=300),
            Scene(start=10, end=20, start_frame=300, end_frame=600),
        ]
        result = SceneDetectionResult(
            scenes=scenes,
            video_path="test.mp4",
            detector_type="content",
            total_duration=20.0,
        )

        scene = result.get_scene_at_time(5.0)
        assert scene is not None
        assert scene.start == 0

        scene = result.get_scene_at_time(25.0)
        assert scene is None

    def test_get_longest_scenes(self):
        """测试获取最长场景."""
        scenes = [
            Scene(start=0, end=5, start_frame=0, end_frame=150),
            Scene(start=5, end=20, start_frame=150, end_frame=600),
            Scene(start=20, end=25, start_frame=600, end_frame=750),
        ]
        result = SceneDetectionResult(
            scenes=scenes,
            video_path="test.mp4",
            detector_type="content",
            total_duration=25.0,
        )

        longest = result.get_longest_scenes(n=2)
        assert len(longest) == 2
        assert longest[0].duration == 15.0  # 5-20
        assert longest[1].duration == 5.0  # 0-5 或 20-25


class TestSceneDetector:
    """SceneDetector 测试类."""

    def test_initialization(self):
        """测试初始化."""
        detector = SceneDetector(detector_type="content")
        assert detector.detector_type == "content"

    def test_initialization_invalid(self):
        """测试无效检测器类型."""
        with pytest.raises(ValueError):
            SceneDetector(detector_type="invalid")

    def test_merge_similar_scenes(self):
        """测试合并相似场景."""
        scenes = [
            Scene(start=0, end=5, start_frame=0, end_frame=150),
            Scene(start=5.5, end=10, start_frame=165, end_frame=300),
            Scene(start=15, end=20, start_frame=450, end_frame=600),
        ]

        detector = SceneDetector()
        merged = detector.merge_similar_scenes(
            scenes,
            max_merge_gap=1.0,
            min_merged_duration=2.0,
        )

        assert len(merged) == 2  # 前两个合并，最后一个独立
        assert merged[0].duration == 10.0  # 0-10
        assert merged[1].duration == 5.0  # 15-20
