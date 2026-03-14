"""Tests for auto editor."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from video_cut_skill.ai.scene_detector import Scene, SceneDetectionResult
from video_cut_skill.ai.transcriber import TranscriptResult, TranscriptSegment
from video_cut_skill.auto_editor import AutoEditor, EditConfig, EditResult


class TestEditConfig:
    """EditConfig tests."""

    def test_default_initialization(self):
        """Test default values."""
        config = EditConfig()
        assert config.target_duration is None
        assert config.aspect_ratio == "original"
        assert config.add_subtitles is True
        assert config.output_path is None
        assert config.whisper_model == "base"

    def test_custom_initialization(self):
        """Test custom values."""
        config = EditConfig(
            target_duration=60.0,
            aspect_ratio="9:16",
            add_subtitles=False,
            output_path="/output/video.mp4",
            whisper_model="small",
        )
        assert config.target_duration == 60.0
        assert config.aspect_ratio == "9:16"
        assert config.add_subtitles is False
        assert config.output_path == "/output/video.mp4"
        assert config.whisper_model == "small"


class TestEditResult:
    """EditResult tests."""

    def test_initialization(self):
        """Test initialization."""
        result = EditResult(output_path=Path("/output/video.mp4"))
        assert result.output_path == Path("/output/video.mp4")
        assert result.transcript is None
        assert result.scenes is None

    def test_initialization_with_optional_fields(self):
        """Test initialization with all fields."""
        transcript = TranscriptResult(
            text="Hello",
            segments=[TranscriptSegment(start=0.0, end=1.0, text="Hello")],
            language="en",
            duration=1.0,
        )
        scenes = SceneDetectionResult(
            scenes=[],
            video_path="/path/to/video.mp4",
            detector_type="content",
            total_duration=60.0,
        )
        result = EditResult(
            output_path=Path("/output/video.mp4"),
            transcript=transcript,
            scenes=scenes,
        )
        assert result.transcript == transcript
        assert result.scenes == scenes


class TestAutoEditor:
    """AutoEditor tests."""

    @pytest.fixture
    def editor(self):
        """Create editor instance with mocked dependencies."""
        mock_ffmpeg = MagicMock()
        mock_transcriber = MagicMock()
        mock_detector = MagicMock()
        return AutoEditor(
            ffmpeg=mock_ffmpeg,
            transcriber=mock_transcriber,
            scene_detector=mock_detector,
        )

    @pytest.fixture
    def temp_video(self, tmp_path):
        """Create a temporary video file."""
        video_file = tmp_path / "test_video.mp4"
        video_file.write_text("fake video content")
        return video_file

    def test_initialization_default(self):
        """Test default initialization creates components."""
        with patch("video_cut_skill.auto_editor.FFmpegWrapper"), patch("video_cut_skill.auto_editor.SceneDetector"):
            editor = AutoEditor()
            assert editor.ffmpeg is not None
            assert editor.transcriber is None  # Created lazily
            assert editor.scene_detector is not None

    def test_initialization_with_custom_components(self):
        """Test initialization with custom components."""
        mock_ffmpeg = MagicMock()
        mock_transcriber = MagicMock()
        mock_detector = MagicMock()

        editor = AutoEditor(
            ffmpeg=mock_ffmpeg,
            transcriber=mock_transcriber,
            scene_detector=mock_detector,
        )

        assert editor.ffmpeg == mock_ffmpeg
        assert editor.transcriber == mock_transcriber
        assert editor.scene_detector == mock_detector

    def test_process_video_file_not_found(self, editor):
        """Test processing non-existent file raises error."""
        config = EditConfig()
        with pytest.raises(FileNotFoundError):
            editor.process_video("/nonexistent/video.mp4", config)

    def test_process_video_basic(self, editor, temp_video):
        """Test basic video processing."""
        # Setup mocks
        editor.ffmpeg.get_video_info.return_value = {
            "duration": 120.0,
            "width": 1920,
            "height": 1080,
        }
        editor.scene_detector.detect.return_value = SceneDetectionResult(
            scenes=[Scene(start=0.0, end=10.0, start_frame=0, end_frame=300)],
            video_path=str(temp_video),
            detector_type="content",
            total_duration=120.0,
        )

        config = EditConfig(add_subtitles=False)
        result = editor.process_video(temp_video, config)

        assert isinstance(result, EditResult)
        assert result.output_path.exists()
        editor.ffmpeg.get_video_info.assert_called_once()
        editor.scene_detector.detect.assert_called_once()

    def test_process_video_with_subtitles(self, editor, temp_video, tmp_path):
        """Test video processing with subtitles."""
        # Setup mocks
        editor.ffmpeg.get_video_info.return_value = {
            "duration": 60.0,
            "width": 1920,
            "height": 1080,
        }
        editor.scene_detector.detect.return_value = SceneDetectionResult(
            scenes=[],
            video_path=str(temp_video),
            detector_type="content",
            total_duration=60.0,
        )

        transcript = TranscriptResult(
            text="Hello world",
            segments=[TranscriptSegment(start=0.0, end=1.0, text="Hello world")],
            language="en",
            duration=1.0,
        )
        editor.transcriber.transcribe.return_value = transcript
        editor.transcriber.export_srt = MagicMock()
        editor.ffmpeg.add_subtitle = MagicMock()

        config = EditConfig(add_subtitles=True)
        result = editor.process_video(temp_video, config)

        assert isinstance(result, EditResult)
        editor.transcriber.transcribe.assert_called_once()
        assert result.transcript == transcript

    def test_process_video_with_duration_cut(self, editor, temp_video):
        """Test video processing with target duration."""
        # Setup mocks
        editor.ffmpeg.get_video_info.return_value = {
            "duration": 120.0,
            "width": 1920,
            "height": 1080,
        }
        editor.scene_detector.detect.return_value = SceneDetectionResult(
            scenes=[],
            video_path=str(temp_video),
            detector_type="content",
            total_duration=120.0,
        )

        config = EditConfig(target_duration=30.0, add_subtitles=False)
        _ = editor.process_video(temp_video, config)

        editor.ffmpeg.cut_clip.assert_called_once()
        call_args = editor.ffmpeg.cut_clip.call_args
        assert call_args[1]["start_time"] == 0
        assert call_args[1]["end_time"] == 30.0

    def test_process_video_no_duration_cut(self, editor, temp_video):
        """Test video processing without duration cut copies file."""
        # Setup mocks
        editor.ffmpeg.get_video_info.return_value = {
            "duration": 60.0,
            "width": 1920,
            "height": 1080,
        }
        editor.scene_detector.detect.return_value = SceneDetectionResult(
            scenes=[],
            video_path=str(temp_video),
            detector_type="content",
            total_duration=60.0,
        )

        config = EditConfig(target_duration=120.0, add_subtitles=False)  # Longer than video
        result = editor.process_video(temp_video, config)

        # Should not call cut_clip, should copy instead
        editor.ffmpeg.cut_clip.assert_not_called()
        assert result.output_path.exists()

    def test_cut_by_scenes(self, editor, temp_video, tmp_path):
        """Test cutting video by scenes."""
        output_dir = tmp_path / "scenes"

        # Setup mocks
        scenes = SceneDetectionResult(
            scenes=[
                Scene(start=0.0, end=5.0, start_frame=0, end_frame=150),
                Scene(start=5.0, end=10.0, start_frame=150, end_frame=300),
            ],
            video_path=str(temp_video),
            detector_type="content",
            total_duration=10.0,
        )
        editor.scene_detector.detect.return_value = scenes
        editor.scene_detector.split_video.return_value = [
            output_dir / "scene_001.mp4",
            output_dir / "scene_002.mp4",
        ]

        result = editor.cut_by_scenes(temp_video, output_dir)

        assert len(result) == 2
        editor.scene_detector.detect.assert_called_once()
        editor.scene_detector.split_video.assert_called_once()

    def test_cut_by_scenes_creates_output_dir(self, editor, temp_video, tmp_path):
        """Test cut_by_scenes creates output directory."""
        output_dir = tmp_path / "new_scenes_dir"

        # Setup mocks
        editor.scene_detector.detect.return_value = SceneDetectionResult(
            scenes=[],
            video_path=str(temp_video),
            detector_type="content",
            total_duration=60.0,
        )
        editor.scene_detector.split_video.return_value = []

        editor.cut_by_scenes(temp_video, output_dir)

        assert output_dir.exists()

    def test_extract_highlights_no_matches(self, editor, temp_video, tmp_path):
        """Test extracting highlights with no keyword matches."""
        output_path = tmp_path / "highlights.mp4"

        # Setup mocks
        transcript = TranscriptResult(
            text="Some content",
            segments=[TranscriptSegment(start=0.0, end=1.0, text="Some content")],
            language="en",
            duration=1.0,
        )
        editor.transcriber.transcribe.return_value = transcript
        editor.transcriber.detect_keywords.return_value = []

        result = editor.extract_highlights(
            temp_video,
            keywords=["nonexistent"],
            output_path=output_path,
        )

        # Should return original video path when no matches
        assert result == temp_video

    def test_extract_highlights_with_matches(self, editor, temp_video, tmp_path):
        """Test extracting highlights with keyword matches."""
        output_path = tmp_path / "highlights.mp4"

        # Setup mocks
        transcript = TranscriptResult(
            text="Hello world",
            segments=[TranscriptSegment(start=0.0, end=1.0, text="Hello world")],
            language="en",
            duration=1.0,
        )
        editor.transcriber.transcribe.return_value = transcript
        editor.transcriber.detect_keywords.return_value = [
            {"start": 0.0, "end": 1.0, "keyword": "hello"},
        ]
        editor.ffmpeg.cut_clip = MagicMock()

        # Create temp dir and clip file for the test
        import os

        os.makedirs("/tmp/video_cut_skill", exist_ok=True)
        with open("/tmp/video_cut_skill/highlight_000.mp4", "w") as f:
            f.write("fake clip")

        try:
            result = editor.extract_highlights(
                temp_video,
                keywords=["hello"],
                output_path=output_path,
            )

            assert result == output_path
            editor.ffmpeg.cut_clip.assert_called_once()
        finally:
            # Cleanup
            import shutil

            if os.path.exists("/tmp/video_cut_skill"):
                shutil.rmtree("/tmp/video_cut_skill")

    def test_extract_highlights_creates_transcriber(self, editor, temp_video, tmp_path):
        """Test extract_highlights creates transcriber if None."""
        output_path = tmp_path / "highlights.mp4"
        editor.transcriber = None

        with patch("video_cut_skill.auto_editor.Transcriber") as mock_transcriber_class:
            mock_transcriber = MagicMock()
            mock_transcriber.transcribe.return_value = TranscriptResult(
                text="Test",
                segments=[TranscriptSegment(start=0.0, end=1.0, text="Test")],
                language="en",
                duration=1.0,
            )
            mock_transcriber.detect_keywords.return_value = []
            mock_transcriber_class.return_value = mock_transcriber

            editor.extract_highlights(
                temp_video,
                keywords=["test"],
                output_path=output_path,
                whisper_model="small",
            )

            mock_transcriber_class.assert_called_once_with(model_size="small")

    def test_extract_highlights_concatenates_multiple_clips(self, editor, temp_video, tmp_path):
        """Test extracting multiple highlights concatenates them."""
        output_path = tmp_path / "highlights.mp4"

        # Setup mocks
        transcript = TranscriptResult(
            text="Hello world test",
            segments=[TranscriptSegment(start=0.0, end=3.0, text="Hello world test")],
            language="en",
            duration=3.0,
        )
        editor.transcriber.transcribe.return_value = transcript
        editor.transcriber.detect_keywords.return_value = [
            {"start": 0.0, "end": 1.0, "keyword": "hello"},
            {"start": 2.0, "end": 3.0, "keyword": "test"},
        ]
        editor.ffmpeg.cut_clip = MagicMock()
        editor.ffmpeg.concatenate_clips = MagicMock()

        editor.extract_highlights(
            temp_video,
            keywords=["hello", "test"],
            output_path=output_path,
        )

        # Should concatenate since there are multiple clips
        assert editor.ffmpeg.cut_clip.call_count == 2
        editor.ffmpeg.concatenate_clips.assert_called_once()
