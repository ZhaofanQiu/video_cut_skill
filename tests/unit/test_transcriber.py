"""Tests for transcriber module."""

from unittest.mock import MagicMock, patch

import pytest

from video_cut_skill.ai.transcriber import (
    Transcriber,
    TranscriptResult,
    TranscriptSegment,
)


class TestTranscriptSegment:
    """TranscriptSegment tests."""

    def test_segment_creation(self):
        """Test creating TranscriptSegment."""
        segment = TranscriptSegment(start=0.0, end=5.0, text="Hello world")
        assert segment.start == 0.0
        assert segment.end == 5.0
        assert segment.text == "Hello world"
        assert segment.words is None

    def test_segment_with_words(self):
        """Test TranscriptSegment with word timestamps."""
        words = [
            {"word": "Hello", "start": 0.0, "end": 0.5},
            {"word": "world", "start": 0.5, "end": 1.0},
        ]
        segment = TranscriptSegment(start=0.0, end=1.0, text="Hello world", words=words)
        assert segment.words == words

    def test_duration_property(self):
        """Test duration property."""
        segment = TranscriptSegment(start=10.0, end=20.0, text="Test")
        assert segment.duration == 10.0


class TestTranscriptResult:
    """TranscriptResult tests."""

    @pytest.fixture
    def sample_segments(self):
        """Create sample segments."""
        return [
            TranscriptSegment(start=0.0, end=5.0, text="First segment"),
            TranscriptSegment(start=5.0, end=10.0, text="Second segment"),
            TranscriptSegment(start=10.0, end=15.0, text="Third segment"),
        ]

    @pytest.fixture
    def sample_result(self, sample_segments):
        """Create sample transcript result."""
        return TranscriptResult(
            text="First segment Second segment Third segment",
            segments=sample_segments,
            language="en",
            duration=15.0,
        )

    def test_result_creation(self, sample_segments):
        """Test creating TranscriptResult."""
        result = TranscriptResult(
            text="Hello world",
            segments=sample_segments,
            language="en",
            duration=15.0,
        )
        assert result.text == "Hello world"
        assert result.language == "en"
        assert result.duration == 15.0
        assert len(result.segments) == 3

    def test_get_segment_at_time_found(self, sample_result):
        """Test getting segment at specific time."""
        segment = sample_result.get_segment_at_time(7.0)
        assert segment is not None
        assert segment.text == "Second segment"

    def test_get_segment_at_time_boundary(self, sample_result):
        """Test getting segment at boundary time."""
        # At exactly 5.0, the first segment (0-5) should match because it includes the end
        segment = sample_result.get_segment_at_time(5.0)
        assert segment is not None
        # First segment ends at 5.0, so it should be returned
        assert segment.text == "First segment"

    def test_get_segment_at_time_not_found(self, sample_result):
        """Test getting segment when none matches."""
        segment = sample_result.get_segment_at_time(25.0)
        assert segment is None

    def test_search_text_found(self, sample_result):
        """Test searching for keyword."""
        matches = sample_result.search_text("second")
        assert len(matches) == 1
        assert matches[0].text == "Second segment"

    def test_search_text_case_insensitive(self, sample_result):
        """Test searching is case insensitive."""
        matches = sample_result.search_text("SECOND")
        assert len(matches) == 1

    def test_search_text_not_found(self, sample_result):
        """Test searching when keyword not found."""
        matches = sample_result.search_text("nonexistent")
        assert len(matches) == 0

    def test_search_text_multiple_matches(self):
        """Test searching with multiple matches."""
        segments = [
            TranscriptSegment(start=0.0, end=5.0, text="Hello world"),
            TranscriptSegment(start=5.0, end=10.0, text="Hello again"),
        ]
        result = TranscriptResult(
            text="Hello world Hello again",
            segments=segments,
            language="en",
            duration=10.0,
        )
        matches = result.search_text("hello")
        assert len(matches) == 2


class TestTranscriber:
    """Transcriber tests."""

    def test_model_sizes_defined(self):
        """Test that model sizes are defined."""
        assert "tiny" in Transcriber.MODEL_SIZES
        assert "base" in Transcriber.MODEL_SIZES
        assert "small" in Transcriber.MODEL_SIZES
        assert "medium" in Transcriber.MODEL_SIZES
        assert "large" in Transcriber.MODEL_SIZES
        assert "turbo" in Transcriber.MODEL_SIZES

    def test_model_sizes_structure(self):
        """Test model sizes structure."""
        for _size, info in Transcriber.MODEL_SIZES.items():
            assert "params" in info
            assert "speed" in info
            assert "memory" in info

    @patch("whisper.load_model")
    @patch("video_cut_skill.ai.transcriber.get_optimal_device", return_value="cpu")
    def test_initialization_default(self, mock_device, mock_load_model):
        """Test default initialization."""
        transcriber = Transcriber()
        assert transcriber.model_size == "base"
        assert transcriber.device == "cpu"
        mock_load_model.assert_called_once()

    @patch("whisper.load_model")
    @patch("video_cut_skill.ai.transcriber.get_optimal_device", return_value="cuda")
    def test_initialization_with_model_size(self, mock_device, mock_load_model):
        """Test initialization with specific model size."""
        transcriber = Transcriber(model_size="small")
        assert transcriber.model_size == "small"

    @patch("whisper.load_model")
    @patch("video_cut_skill.ai.transcriber.get_optimal_device")
    def test_initialization_with_device(self, mock_device, mock_load_model):
        """Test initialization with specific device."""
        mock_device.return_value = "cuda"
        transcriber = Transcriber(device="cuda")
        assert transcriber.device == "cuda"

    def test_initialization_invalid_model_size(self):
        """Test initialization with invalid model size."""
        with pytest.raises(ValueError, match="Invalid model size"):
            Transcriber(model_size="invalid")

    @patch("whisper.load_model")
    @patch("video_cut_skill.ai.transcriber.get_optimal_device", return_value="cpu")
    def test_initialization_model_load_failure(self, mock_device, mock_load_model):
        """Test handling of model load failure."""
        mock_load_model.side_effect = Exception("Model load failed")
        with pytest.raises(Exception, match="Model load failed"):
            Transcriber()

    @patch("whisper.load_model")
    @patch("video_cut_skill.ai.transcriber.get_optimal_device", return_value="cpu")
    def test_transcribe_file_not_found(self, mock_device, mock_load_model, tmp_path):
        """Test transcribing non-existent file."""
        transcriber = Transcriber()
        with pytest.raises(FileNotFoundError):
            transcriber.transcribe("/nonexistent/file.mp4")

    @patch("whisper.load_model")
    @patch("video_cut_skill.ai.transcriber.get_optimal_device", return_value="cpu")
    def test_transcribe_success(self, mock_device, mock_load_model, tmp_path):
        """Test successful transcription."""
        # Create mock model
        mock_model = MagicMock()
        mock_model.transcribe.return_value = {
            "text": "Hello world",
            "segments": [
                {
                    "start": 0.0,
                    "end": 2.0,
                    "text": "Hello world",
                    "words": [{"word": "Hello", "start": 0.0, "end": 1.0}],
                }
            ],
            "language": "en",
        }
        mock_load_model.return_value = mock_model

        transcriber = Transcriber()
        transcriber.model = mock_model

        video_file = tmp_path / "test.mp4"
        video_file.write_text("fake video")

        result = transcriber.transcribe(video_file)

        assert isinstance(result, TranscriptResult)
        assert result.text == "Hello world"
        assert result.language == "en"
        assert len(result.segments) == 1

    @patch("whisper.load_model")
    @patch("video_cut_skill.ai.transcriber.get_optimal_device", return_value="cpu")
    def test_transcribe_with_language(self, mock_device, mock_load_model, tmp_path):
        """Test transcription with specified language."""
        mock_model = MagicMock()
        mock_model.transcribe.return_value = {
            "text": "Hello",
            "segments": [],
            "language": "en",
        }
        mock_load_model.return_value = mock_model

        transcriber = Transcriber()
        transcriber.model = mock_model

        video_file = tmp_path / "test.mp4"
        video_file.write_text("fake video")

        transcriber.transcribe(video_file, language="en")

        # Verify language was passed to model
        call_kwargs = mock_model.transcribe.call_args[1]
        assert call_kwargs["language"] == "en"

    @patch("whisper.load_model")
    @patch("video_cut_skill.ai.transcriber.get_optimal_device", return_value="cpu")
    def test_export_srt(self, mock_device, mock_load_model, tmp_path):
        """Test SRT export."""
        transcriber = Transcriber()

        segments = [
            TranscriptSegment(start=0.0, end=5.0, text="First line"),
            TranscriptSegment(start=5.0, end=10.0, text="Second line"),
        ]
        transcript = TranscriptResult(
            text="First line Second line",
            segments=segments,
            language="en",
            duration=10.0,
        )

        output_path = tmp_path / "output.srt"
        result = transcriber.export_srt(transcript, output_path)

        assert result == output_path
        assert output_path.exists()
        content = output_path.read_text()
        assert "1" in content
        assert "First line" in content

    @patch("whisper.load_model")
    @patch("video_cut_skill.ai.transcriber.get_optimal_device", return_value="cpu")
    def test_export_ass(self, mock_device, mock_load_model, tmp_path):
        """Test ASS export."""
        transcriber = Transcriber()

        segments = [
            TranscriptSegment(start=0.0, end=5.0, text="First line"),
        ]
        transcript = TranscriptResult(
            text="First line",
            segments=segments,
            language="en",
            duration=5.0,
        )

        output_path = tmp_path / "output.ass"
        result = transcriber.export_ass(transcript, output_path)

        assert result == output_path
        assert output_path.exists()
        content = output_path.read_text()
        assert "[Script Info]" in content
        assert "First line" in content

    @patch("whisper.load_model")
    @patch("video_cut_skill.ai.transcriber.get_optimal_device", return_value="cpu")
    def test_export_ass_custom_style(self, mock_device, mock_load_model, tmp_path):
        """Test ASS export with custom style."""
        transcriber = Transcriber()

        segments = [
            TranscriptSegment(start=0.0, end=5.0, text="Test"),
        ]
        transcript = TranscriptResult(
            text="Test",
            segments=segments,
            language="en",
            duration=5.0,
        )

        custom_style = {
            "font": "Helvetica",
            "fontsize": 32,
            "color": "&H0000FFFF",
        }
        output_path = tmp_path / "output.ass"
        transcriber.export_ass(transcript, output_path, style=custom_style)

        content = output_path.read_text()
        assert "Helvetica" in content
        assert "32" in content

    @patch("whisper.load_model")
    @patch("video_cut_skill.ai.transcriber.get_optimal_device", return_value="cpu")
    def test_detect_keywords(self, mock_device, mock_load_model):
        """Test keyword detection."""
        transcriber = Transcriber()

        segments = [
            TranscriptSegment(start=0.0, end=5.0, text="Hello world"),
            TranscriptSegment(start=5.0, end=10.0, text="Hello again"),
        ]
        transcript = TranscriptResult(
            text="Hello world Hello again",
            segments=segments,
            language="en",
            duration=10.0,
        )

        results = transcriber.detect_keywords(transcript, ["hello"], context_seconds=1.0)

        assert len(results) == 2
        assert results[0]["keyword"] == "hello"
        assert "start" in results[0]
        assert "end" in results[0]

    @patch("whisper.load_model")
    @patch("video_cut_skill.ai.transcriber.get_optimal_device", return_value="cpu")
    def test_detect_keywords_sorted(self, mock_device, mock_load_model):
        """Test that keyword detection results are sorted by time."""
        transcriber = Transcriber()

        segments = [
            TranscriptSegment(start=10.0, end=15.0, text="Later segment"),
            TranscriptSegment(start=0.0, end=5.0, text="Earlier segment"),
        ]
        transcript = TranscriptResult(
            text="Later segment Earlier segment",
            segments=segments,
            language="en",
            duration=15.0,
        )

        results = transcriber.detect_keywords(transcript, ["segment"])

        # Results should be sorted by start time
        assert results[0]["start"] < results[1]["start"]

    @patch("whisper.load_model")
    @patch("video_cut_skill.ai.transcriber.get_optimal_device", return_value="cpu")
    def test_detect_keywords_no_matches(self, mock_device, mock_load_model):
        """Test keyword detection with no matches."""
        transcriber = Transcriber()

        segments = [
            TranscriptSegment(start=0.0, end=5.0, text="Hello world"),
        ]
        transcript = TranscriptResult(
            text="Hello world",
            segments=segments,
            language="en",
            duration=5.0,
        )

        results = transcriber.detect_keywords(transcript, ["nonexistent"])

        assert len(results) == 0
