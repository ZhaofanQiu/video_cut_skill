"""Tests for scene detector module."""

from unittest.mock import MagicMock, patch

import pytest

from video_cut_skill.ai.scene_detector import Scene, SceneDetectionResult, SceneDetector


class TestScene:
    """Scene dataclass tests."""

    def test_scene_creation(self):
        """Test creating Scene."""
        scene = Scene(start=0.0, end=10.0, start_frame=0, end_frame=300)
        assert scene.start == 0.0
        assert scene.end == 10.0
        assert scene.start_frame == 0
        assert scene.end_frame == 300

    def test_duration_property(self):
        """Test duration property."""
        scene = Scene(start=5.0, end=15.0, start_frame=150, end_frame=450)
        assert scene.duration == 10.0

    def test_frame_count_property(self):
        """Test frame_count property."""
        scene = Scene(start=0.0, end=10.0, start_frame=0, end_frame=300)
        assert scene.frame_count == 300


class TestSceneDetectionResult:
    """SceneDetectionResult tests."""

    @pytest.fixture
    def sample_scenes(self):
        """Create sample scenes for testing."""
        return [
            Scene(start=0.0, end=5.0, start_frame=0, end_frame=150),
            Scene(start=5.0, end=15.0, start_frame=150, end_frame=450),
            Scene(start=15.0, end=20.0, start_frame=450, end_frame=600),
        ]

    @pytest.fixture
    def sample_result(self, sample_scenes):
        """Create sample detection result."""
        return SceneDetectionResult(
            scenes=sample_scenes,
            video_path="/path/to/video.mp4",
            detector_type="content",
            total_duration=20.0,
        )

    def test_scene_count_property(self, sample_result):
        """Test scene_count property."""
        assert sample_result.scene_count == 3

    def test_scene_count_empty(self):
        """Test scene_count with empty scenes."""
        result = SceneDetectionResult(
            scenes=[],
            video_path="/path/to/video.mp4",
            detector_type="content",
            total_duration=0.0,
        )
        assert result.scene_count == 0

    def test_get_scene_at_time_found(self, sample_result):
        """Test getting scene at specific time."""
        scene = sample_result.get_scene_at_time(7.0)
        assert scene is not None
        assert scene.start == 5.0
        assert scene.end == 15.0

    def test_get_scene_at_time_at_boundary(self, sample_result):
        """Test getting scene at boundary time."""
        # At exactly 5.0, both scenes could match (0-5 and 5-15)
        # The first matching scene is returned
        scene = sample_result.get_scene_at_time(5.0)
        assert scene is not None
        # The first scene (0-5) should match because it includes the end boundary
        assert scene.start == 0.0

    def test_get_scene_at_time_not_found(self, sample_result):
        """Test getting scene when none matches."""
        scene = sample_result.get_scene_at_time(25.0)
        assert scene is None

    def test_get_longest_scenes(self, sample_result):
        """Test getting longest scenes."""
        longest = sample_result.get_longest_scenes(n=2)
        assert len(longest) == 2
        # Second scene (10s) should be first, first scene (5s) should be second
        assert longest[0].duration == 10.0
        assert longest[1].duration == 5.0

    def test_get_longest_scenes_empty(self):
        """Test getting longest scenes from empty result."""
        result = SceneDetectionResult(
            scenes=[],
            video_path="/path/to/video.mp4",
            detector_type="content",
            total_duration=0.0,
        )
        longest = result.get_longest_scenes(n=5)
        assert longest == []


class TestSceneDetector:
    """SceneDetector tests."""

    def test_initialization_content(self):
        """Test initialization with content detector."""
        detector = SceneDetector(detector_type="content")
        assert detector.detector_type == "content"

    def test_initialization_threshold(self):
        """Test initialization with threshold detector."""
        detector = SceneDetector(detector_type="threshold")
        assert detector.detector_type == "threshold"

    def test_initialization_adaptive(self):
        """Test initialization with adaptive detector."""
        detector = SceneDetector(detector_type="adaptive")
        assert detector.detector_type == "adaptive"

    def test_initialization_invalid_type(self):
        """Test initialization with invalid detector type."""
        with pytest.raises(ValueError, match="Invalid detector type"):
            SceneDetector(detector_type="invalid")

    @patch("video_cut_skill.ai.scene_detector.detect")
    def test_detect_content(self, mock_detect):
        """Test scene detection with content detector."""
        # Mock scenedetect results
        mock_start1 = MagicMock()
        mock_start1.get_seconds.return_value = 0.0
        mock_start1.get_frames.return_value = 0
        mock_end1 = MagicMock()
        mock_end1.get_seconds.return_value = 5.0
        mock_end1.get_frames.return_value = 150

        mock_start2 = MagicMock()
        mock_start2.get_seconds.return_value = 5.0
        mock_start2.get_frames.return_value = 150
        mock_end2 = MagicMock()
        mock_end2.get_seconds.return_value = 15.0
        mock_end2.get_frames.return_value = 450

        mock_detect.return_value = [
            (mock_start1, mock_end1),
            (mock_start2, mock_end2),
        ]

        detector = SceneDetector(detector_type="content")
        result = detector.detect("/path/to/video.mp4")

        assert isinstance(result, SceneDetectionResult)
        assert result.detector_type == "content"
        assert len(result.scenes) == 2
        mock_detect.assert_called_once()

    @patch("video_cut_skill.ai.scene_detector.detect")
    def test_detect_filters_short_scenes(self, mock_detect):
        """Test that short scenes are filtered."""
        # Create scenes with very short duration
        mock_start = MagicMock()
        mock_start.get_seconds.return_value = 0.0
        mock_start.get_frames.return_value = 0
        mock_end = MagicMock()
        mock_end.get_seconds.return_value = 0.1  # Less than min_scene_len
        mock_end.get_frames.return_value = 3

        mock_detect.return_value = [(mock_start, mock_end)]

        detector = SceneDetector(detector_type="content")
        result = detector.detect("/path/to/video.mp4", min_scene_len=0.5)

        # Short scene should be filtered out
        assert len(result.scenes) == 0

    @patch("video_cut_skill.ai.scene_detector.detect")
    def test_detect_empty_result(self, mock_detect):
        """Test detection with no scenes found."""
        mock_detect.return_value = []

        detector = SceneDetector(detector_type="content")
        result = detector.detect("/path/to/video.mp4")

        assert result.scene_count == 0
        assert result.total_duration == 0

    @patch("video_cut_skill.ai.scene_detector.detect")
    def test_detect_error_handling(self, mock_detect):
        """Test error handling during detection."""
        mock_detect.side_effect = Exception("Detection failed")

        detector = SceneDetector(detector_type="content")
        with pytest.raises(Exception, match="Detection failed"):
            detector.detect("/path/to/video.mp4")

    @patch("video_cut_skill.ai.scene_detector.split_video_ffmpeg")
    def test_split_video(self, mock_split, tmp_path):
        """Test video splitting."""
        mock_split.return_value = None  # split_video_ffmpeg returns None

        detector = SceneDetector(detector_type="content")
        scenes = [
            Scene(start=0.0, end=5.0, start_frame=0, end_frame=150),
            Scene(start=5.0, end=10.0, start_frame=150, end_frame=300),
        ]

        video_file = tmp_path / "test.mp4"
        video_file.write_text("fake video")
        output_dir = tmp_path / "output"

        result = detector.split_video(video_file, scenes, output_dir)

        assert isinstance(result, list)
        mock_split.assert_called_once()

    @patch("video_cut_skill.ai.scene_detector.split_video_ffmpeg")
    def test_split_video_creates_output_dir(self, mock_split, tmp_path):
        """Test that split_video creates output directory."""
        mock_split.return_value = None

        detector = SceneDetector(detector_type="content")
        scenes = [Scene(start=0.0, end=5.0, start_frame=0, end_frame=150)]

        video_file = tmp_path / "test.mp4"
        video_file.write_text("fake video")
        output_dir = tmp_path / "new_output_dir"

        detector.split_video(video_file, scenes, output_dir)

        assert output_dir.exists()

    @patch("video_cut_skill.ai.scene_detector.detect")
    def test_detect_with_multiple_methods(self, mock_detect):
        """Test detection with multiple methods."""
        # Mock successful detection
        mock_start = MagicMock()
        mock_start.get_seconds.return_value = 0.0
        mock_start.get_frames.return_value = 0
        mock_end = MagicMock()
        mock_end.get_seconds.return_value = 10.0
        mock_end.get_frames.return_value = 300

        mock_detect.return_value = [(mock_start, mock_end)]

        detector = SceneDetector(detector_type="content")
        results = detector.detect_with_multiple_methods(
            "/path/to/video.mp4",
            methods=["content", "threshold"],
        )

        assert isinstance(results, dict)
        assert "content" in results or "threshold" in results

    @patch("video_cut_skill.ai.scene_detector.detect")
    def test_detect_with_multiple_methods_some_fail(self, mock_detect):
        """Test multiple methods when some fail."""
        # First call succeeds, second fails
        mock_start = MagicMock()
        mock_start.get_seconds.return_value = 0.0
        mock_start.get_frames.return_value = 0
        mock_end = MagicMock()
        mock_end.get_seconds.return_value = 10.0
        mock_end.get_frames.return_value = 300

        mock_detect.side_effect = [
            [(mock_start, mock_end)],  # First method succeeds
            Exception("Second method failed"),  # Second method fails
        ]

        detector = SceneDetector(detector_type="content")
        results = detector.detect_with_multiple_methods(
            "/path/to/video.mp4",
            methods=["content", "adaptive"],
        )

        # Should still have results from successful methods
        assert isinstance(results, dict)

    def test_split_video_error_handling(self, tmp_path):
        """Test error handling in split_video."""
        with patch("video_cut_skill.ai.scene_detector.split_video_ffmpeg") as mock_split:
            mock_split.side_effect = Exception("Split failed")

            detector = SceneDetector(detector_type="content")
            scenes = [Scene(start=0.0, end=5.0, start_frame=0, end_frame=150)]

            video_file = tmp_path / "test.mp4"
            video_file.write_text("fake video")
            output_dir = tmp_path / "output"

            with pytest.raises(Exception, match="Split failed"):
                detector.split_video(video_file, scenes, output_dir)

    @patch("video_cut_skill.ai.scene_detector.detect")
    def test_detect_custom_parameters(self, mock_detect):
        """Test detection with custom parameters."""
        mock_start = MagicMock()
        mock_start.get_seconds.return_value = 0.0
        mock_end = MagicMock()
        mock_end.get_seconds.return_value = 10.0

        mock_detect.return_value = [(mock_start, mock_end)]

        detector = SceneDetector(detector_type="content")
        result = detector.detect(
            "/path/to/video.mp4",
            threshold=30.0,
            min_scene_len=1.0,
            show_progress=True,
        )

        assert isinstance(result, SceneDetectionResult)
        # Verify detect was called with the detector
        call_args = mock_detect.call_args
        assert call_args[1]["show_progress"] is True
