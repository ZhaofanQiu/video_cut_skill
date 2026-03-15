"""Tests for auto editor (unified version)."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from video_cut_skill.ai.scene_detector import Scene, SceneDetectionResult
from video_cut_skill.ai.transcriber import Transcriber, TranscriptResult, TranscriptSegment
from video_cut_skill.auto_editor import (
    AutoEditor,
    EditConfig,
    EditResult,
    extract_highlights,
    process_video,
)


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
        assert config.highlight_keywords == []
        assert config.context_seconds == 2.0

    def test_custom_initialization(self):
        """Test custom values."""
        config = EditConfig(
            target_duration=60.0,
            aspect_ratio="9:16",
            add_subtitles=False,
            output_path="/output/video.mp4",
            whisper_model="small",
            highlight_keywords=["test", "highlight"],
            context_seconds=3.0,
        )
        assert config.target_duration == 60.0
        assert config.aspect_ratio == "9:16"
        assert config.add_subtitles is False
        assert config.output_path == "/output/video.mp4"
        assert config.whisper_model == "small"
        assert config.highlight_keywords == ["test", "highlight"]
        assert config.context_seconds == 3.0


class TestEditResult:
    """EditResult tests."""

    def test_initialization(self):
        """Test initialization."""
        result = EditResult(output_path=Path("/output/video.mp4"))
        assert result.output_path == Path("/output/video.mp4")
        assert result.transcript is None
        assert result.scenes is None
        assert result.duration == 0.0
        assert result.processing_time == 0.0
        assert result.error is None

    def test_initialization_with_all_fields(self):
        """Test initialization with all fields."""
        transcript = {"text": "Hello", "segments": [], "language": "en"}
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
            duration=60.0,
            processing_time=5.5,
            error=None,
        )
        assert result.transcript == transcript
        assert result.scenes == scenes
        assert result.duration == 60.0
        assert result.processing_time == 5.5


class TestAutoEditorBasicMode:
    """AutoEditor tests in basic mode (analysis_mode="visual")."""

    @pytest.fixture
    def editor(self):
        """Create editor instance with mocked dependencies (basic mode)."""
        mock_ffmpeg = MagicMock()
        mock_transcriber = MagicMock(spec=Transcriber)
        mock_detector = MagicMock()
        editor = AutoEditor(
            ffmpeg=mock_ffmpeg,
            analysis_mode="visual",
        )
        # Manually set the mocks
        editor.transcriber = mock_transcriber
        editor.scene_detector = mock_detector
        return editor

    @pytest.fixture
    def temp_video(self, tmp_path):
        """Create a temporary video file."""
        video_file = tmp_path / "test_video.mp4"
        video_file.write_text("fake video content")
        return video_file

    def test_initialization_default_basic(self):
        """Test default initialization in basic mode."""
        with patch("video_cut_skill.auto_editor.FFmpegWrapper"), patch("video_cut_skill.auto_editor.SceneDetector"):
            editor = AutoEditor(analysis_mode="visual")
            assert editor.ffmpeg is not None
            assert editor.transcriber is None  # Created lazily
            assert editor.scene_detector is not None
            assert editor.analysis_mode == "visual"

    def test_initialization_default_smart(self):
        """Test default initialization in audio analysis mode."""
        with patch("video_cut_skill.auto_editor.FFmpegWrapper"), patch("video_cut_skill.auto_editor.SmartTranscriber"):
            editor = AutoEditor(analysis_mode="audio")
            assert editor.ffmpeg is not None
            assert editor.transcriber is not None  # Created immediately
            assert editor.scene_detector is None  # Not used in audio mode
            assert editor.analysis_mode == "audio"

    def test_process_video_file_not_found(self, editor):
        """Test processing non-existent file returns error result."""
        config = EditConfig()
        result = editor.process_video("/nonexistent/video.mp4", config)
        assert result.error is not None
        assert "不存在" in result.error

    def test_process_video_basic(self, editor, temp_video):
        """Test basic video processing in basic mode."""
        # Setup mocks
        editor.ffmpeg.get_video_info.return_value = {
            "duration": 120.0,
            "width": 1920,
            "height": 1080,
            "has_audio": True,
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
            "has_audio": True,
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

        # Mock file operations
        from unittest.mock import patch

        with patch("shutil.copy"), patch("shutil.move"):
            config = EditConfig(add_subtitles=True)
            result = editor.process_video(temp_video, config)

        assert isinstance(result, EditResult)
        editor.transcriber.transcribe.assert_called_once()
        assert result.transcript is not None
        assert result.transcript["text"] == "Hello world"

    def test_cut_by_scenes(self, editor, temp_video, tmp_path):
        """Test cutting video by scenes (basic mode only)."""
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

    def test_cut_by_scenes_raises_in_smart_mode(self, temp_video, tmp_path):
        """Test cut_by_scenes raises error in smart mode."""
        editor = AutoEditor(analysis_mode="audio")
        with pytest.raises(RuntimeError, match="仅在视觉分析模式"):
            editor.cut_by_scenes(temp_video, tmp_path / "scenes")


class TestAutoEditorSmartMode:
    """AutoEditor tests in smart mode (analysis_mode="audio")."""

    @pytest.fixture
    def editor(self):
        """Create editor instance with mocked dependencies (smart mode)."""
        mock_ffmpeg = MagicMock()
        mock_smart_transcriber = MagicMock()
        editor = AutoEditor(
            ffmpeg=mock_ffmpeg,
            analysis_mode="audio",
        )
        # Manually set the mock transcriber
        editor.transcriber = mock_smart_transcriber
        editor._smart_transcriber = mock_smart_transcriber
        return editor

    @pytest.fixture
    def temp_video(self, tmp_path):
        """Create a temporary video file."""
        video_file = tmp_path / "test_video.mp4"
        video_file.write_text("fake video content")
        return video_file

    def test_smart_transcriber_audio_check(self, editor, temp_video):
        """Test audio stream check in smart mode."""
        editor._smart_transcriber.has_audio_stream.return_value = False
        editor.ffmpeg.get_video_info.return_value = {
            "duration": 60.0,
            "width": 1920,
            "height": 1080,
        }

        config = EditConfig()
        result = editor.process_video(temp_video, config)

        assert result.error is not None
        assert "无音频" in result.error

    def test_smart_transcriber_model_auto_selection(self, editor, temp_video):
        """Test automatic model selection based on duration."""
        from video_cut_skill.core.smart_transcriber import ModelSize

        # Short video
        editor._smart_transcriber.has_audio_stream.return_value = True
        editor._smart_transcriber.get_video_duration.return_value = 60.0  # < 300s

        # Create proper transcript dict
        transcript_dict = {
            "text": "Test",
            "segments": [{"start": 0.0, "end": 1.0, "text": "Test"}],
            "language": "en",
            "model_used": "base",
        }

        # Mock _transcribe to verify model selection
        original_transcribe = editor._transcribe

        def mock_transcribe(video_path, config):
            # Verify the correct model was selected
            if config.whisper_model == "auto":
                # Check that transcribe was called with BASE for short video
                editor._smart_transcriber.transcribe.assert_called_once()
                call_args = editor._smart_transcriber.transcribe.call_args
                assert call_args[1]["model"] == ModelSize.BASE
            return True, transcript_dict, None

        editor._transcribe = mock_transcribe

        editor.ffmpeg.get_video_info.return_value = {
            "duration": 60.0,
            "width": 1920,
            "height": 1080,
        }

        config = EditConfig(whisper_model="auto", add_subtitles=False)
        editor.process_video(temp_video, config)

        # Restore original
        editor._transcribe = original_transcribe

    def test_extract_highlights_smart_mode(self, editor, temp_video, tmp_path):
        """Test extract_highlights in smart mode."""
        output_path = tmp_path / "highlights.mp4"

        # Setup mocks - create a proper transcript dict
        transcript_dict = {
            "text": "Hello world test content",
            "segments": [
                {"start": 0.0, "end": 1.0, "text": "Hello world"},
                {"start": 2.0, "end": 3.0, "text": "test content"},
            ],
            "language": "en",
            "model_used": "base",
        }

        # Mock _transcribe to return our test data
        editor._transcribe = MagicMock(return_value=(True, transcript_dict, None))
        editor.ffmpeg.cut_clip = MagicMock()
        editor.ffmpeg.concatenate_clips = MagicMock()

        # Mock file operations
        from unittest.mock import patch

        with patch("shutil.copy"):
            result = editor.extract_highlights(
                temp_video,
                keywords=["hello"],
                output_path=output_path,
            )

        assert result.output_path == output_path
        assert result.error is None
        editor._transcribe.assert_called_once()
        editor.ffmpeg.cut_clip.assert_called_once()


class TestConvenienceFunctions:
    """Test convenience functions."""

    @patch("video_cut_skill.auto_editor.AutoEditor")
    def test_process_video_function(self, mock_editor_class):
        """Test process_video convenience function."""
        mock_editor = MagicMock()
        mock_editor_class.return_value = mock_editor
        mock_editor.process_video.return_value = EditResult(output_path=Path("/output.mp4"))

        result = process_video("/input.mp4", target_duration=60.0)

        mock_editor_class.assert_called_once_with(analysis_mode="audio")
        mock_editor.process_video.assert_called_once()
        assert result.output_path == Path("/output.mp4")

    @patch("video_cut_skill.auto_editor.AutoEditor")
    def test_process_video_function_basic_mode(self, mock_editor_class):
        """Test process_video with basic mode."""
        mock_editor = MagicMock()
        mock_editor_class.return_value = mock_editor
        mock_editor.process_video.return_value = EditResult(output_path=Path("/output.mp4"))

        process_video("/input.mp4", analysis_mode="visual")

        mock_editor_class.assert_called_once_with(analysis_mode="visual")

    @patch("video_cut_skill.auto_editor.AutoEditor")
    def test_extract_highlights_function(self, mock_editor_class):
        """Test extract_highlights convenience function."""
        mock_editor = MagicMock()
        mock_editor_class.return_value = mock_editor
        mock_editor.extract_highlights.return_value = Path("/highlights.mp4")

        result = extract_highlights("/input.mp4", keywords=["test"])

        mock_editor_class.assert_called_once_with(analysis_mode="audio")
        mock_editor.extract_highlights.assert_called_once()
        assert result == Path("/highlights.mp4")
