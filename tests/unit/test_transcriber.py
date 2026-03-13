"""Tests for Transcriber."""

from unittest.mock import Mock, patch

import pytest

from video_cut_skill.ai.transcriber import (
    Transcriber,
    TranscriptResult,
    TranscriptSegment,
)


class TestTranscriptSegment:
    """TranscriptSegment 测试."""

    def test_creation(self):
        """测试创建片段."""
        seg = TranscriptSegment(
            start=0.0,
            end=5.0,
            text="Hello world",
        )
        assert seg.start == 0.0
        assert seg.end == 5.0
        assert seg.text == "Hello world"
        assert seg.duration == 5.0

    def test_with_words(self):
        """测试带单词时间戳."""
        words = [
            {"word": "Hello", "start": 0.0, "end": 0.5},
            {"word": "world", "start": 0.6, "end": 1.0},
        ]
        seg = TranscriptSegment(
            start=0.0,
            end=1.0,
            text="Hello world",
            words=words,
        )
        assert len(seg.words) == 2


class TestTranscriptResult:
    """TranscriptResult 测试."""

    def test_creation(self):
        """测试创建结果."""
        segments = [
            TranscriptSegment(start=0, end=5, text="First"),
            TranscriptSegment(start=5, end=10, text="Second"),
        ]
        result = TranscriptResult(
            text="First Second",
            segments=segments,
            language="en",
            duration=10.0,
        )
        assert result.language == "en"
        assert len(result.segments) == 2

    def test_get_segment_at_time(self):
        """测试获取时间点片段."""
        segments = [
            TranscriptSegment(start=0, end=5, text="First"),
            TranscriptSegment(start=5, end=10, text="Second"),
        ]
        result = TranscriptResult(
            text="First Second",
            segments=segments,
            language="en",
            duration=10.0,
        )

        seg = result.get_segment_at_time(3.0)
        assert seg is not None
        assert seg.text == "First"

        seg = result.get_segment_at_time(15.0)
        assert seg is None

    def test_search_text(self):
        """测试搜索文本."""
        segments = [
            TranscriptSegment(start=0, end=5, text="Hello World"),
            TranscriptSegment(start=5, end=10, text="Goodbye World"),
        ]
        result = TranscriptResult(
            text="Hello World Goodbye World",
            segments=segments,
            language="en",
            duration=10.0,
        )

        matches = result.search_text("world")
        assert len(matches) == 2

        matches = result.search_text("hello")
        assert len(matches) == 1

        matches = result.search_text("missing")
        assert len(matches) == 0


class TestTranscriber:
    """Transcriber 测试类."""

    def test_initialization(self):
        """测试初始化."""
        with patch("whisper.load_model") as mock_load:
            mock_model = Mock()
            mock_load.return_value = mock_model

            transcriber = Transcriber(model_size="base")

            assert transcriber.model_size == "base"
            mock_load.assert_called_once()

    def test_initialization_invalid_model(self):
        """测试无效模型大小."""
        with pytest.raises(ValueError):
            Transcriber(model_size="invalid")

    def test_transcribe_success(self):
        """测试成功转录."""
        with patch("whisper.load_model") as mock_load, \
             patch("os.path.exists") as mock_exists:
            mock_model = Mock()
            mock_model.transcribe.return_value = {
                "text": "Hello world",
                "language": "en",
                "segments": [
                    {
                        "start": 0.0,
                        "end": 2.0,
                        "text": "Hello world",
                        "words": [
                            {"word": "Hello", "start": 0.0, "end": 1.0},
                            {"word": "world", "start": 1.0, "end": 2.0},
                        ],
                    },
                ],
            }
            mock_load.return_value = mock_model
            mock_exists.return_value = True

            transcriber = Transcriber(model_size="base")
            result = transcriber.transcribe("test.mp4")

            assert result.text == "Hello world"
            assert result.language == "en"
            assert len(result.segments) == 1

    def test_transcribe_file_not_found(self):
        """测试文件不存在."""
        with patch("whisper.load_model") as mock_load, \
             patch("os.path.exists") as mock_exists:
            mock_load.return_value = Mock()
            mock_exists.return_value = False

            transcriber = Transcriber(model_size="base")
            with pytest.raises(FileNotFoundError):
                transcriber.transcribe("nonexistent.mp4")

    def test_export_srt(self, tmp_path):
        """测试导出 SRT."""
        segments = [
            TranscriptSegment(start=0, end=5, text="First line"),
            TranscriptSegment(start=5, end=10, text="Second line"),
        ]
        result = TranscriptResult(
            text="First line Second line",
            segments=segments,
            language="en",
            duration=10.0,
        )

        output_path = tmp_path / "test.srt"

        with patch("whisper.load_model") as mock_load:
            mock_load.return_value = Mock()
            transcriber = Transcriber(model_size="base")
            transcriber.export_srt(result, output_path)

            assert output_path.exists()
            content = output_path.read_text()
            assert "1" in content
            assert "00:00:00,000 --> 00:00:05,000" in content
            assert "First line" in content

    def test_detect_keywords(self):
        """测试关键词检测."""
        segments = [
            TranscriptSegment(start=0, end=5, text="Hello world"),
            TranscriptSegment(start=10, end=15, text="Hello again"),
            TranscriptSegment(start=20, end=25, text="Goodbye world"),
        ]
        result = TranscriptResult(
            text="Hello world Hello again Goodbye world",
            segments=segments,
            language="en",
            duration=25.0,
        )

        with patch("whisper.load_model") as mock_load:
            mock_load.return_value = Mock()
            transcriber = Transcriber(model_size="base")
            matches = transcriber.detect_keywords(
                result,
                keywords=["hello", "world"],
                context_seconds=1.0,
            )

            assert len(matches) == 4  # hello x2 + world x2
            assert all("keyword" in m for m in matches)
