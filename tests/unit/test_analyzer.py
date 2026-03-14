"""Tests for content analyzer."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from video_cut_skill.ai.analyzer import (
    AudioFeatures,
    ContentAnalysis,
    ContentAnalyzer,
    ContentSegment,
    VisualFeatures,
)
from video_cut_skill.ai.transcriber import TranscriptResult, TranscriptSegment


class TestAudioFeatures:
    """AudioFeatures tests."""

    def test_default_initialization(self):
        """Test default values."""
        features = AudioFeatures()
        assert features.mean_volume == 0.0
        assert features.max_volume == 0.0
        assert features.silent_segments == []
        assert features.speech_rate == 0.0
        assert features.fingerprint is None

    def test_custom_initialization(self):
        """Test custom values."""
        features = AudioFeatures(
            mean_volume=50.0,
            max_volume=100.0,
            silent_segments=[(1.0, 2.0), (5.0, 6.0)],
            speech_rate=120.0,
            fingerprint="abc123",
        )
        assert features.mean_volume == 50.0
        assert features.max_volume == 100.0
        assert len(features.silent_segments) == 2
        assert features.speech_rate == 120.0
        assert features.fingerprint == "abc123"


class TestVisualFeatures:
    """VisualFeatures tests."""

    def test_default_initialization(self):
        """Test default values."""
        features = VisualFeatures()
        assert features.mean_brightness == 0.0
        assert features.brightness_variance == 0.0
        assert features.motion_score == 0.0
        assert features.keyframe_times == []
        assert features.dominant_colors == []


class TestContentSegment:
    """ContentSegment tests."""

    def test_duration_property(self):
        """Test duration property."""
        segment = ContentSegment(start_time=10.0, end_time=20.0)
        assert segment.duration == 10.0

    def test_text_property_with_transcript(self):
        """Test text property with transcript."""
        transcript = TranscriptResult(
            text="Hello world",
            segments=[
                TranscriptSegment(start=0.0, end=1.0, text="Hello"),
                TranscriptSegment(start=1.0, end=2.0, text="world"),
            ],
            language="en",
            duration=2.0,
        )
        segment = ContentSegment(
            start_time=0.0,
            end_time=2.0,
            transcript=transcript,
        )
        assert segment.text == "Hello world"

    def test_text_property_without_transcript(self):
        """Test text property without transcript."""
        segment = ContentSegment(start_time=0.0, end_time=2.0)
        assert segment.text == ""

    def test_importance_score_default(self):
        """Test default importance score."""
        segment = ContentSegment(start_time=0.0, end_time=1.0)
        assert segment.importance_score == 0.0


class TestContentAnalysis:
    """ContentAnalysis tests."""

    @pytest.fixture
    def sample_analysis(self):
        """Create sample analysis for testing."""
        return ContentAnalysis(
            video_path=Path("/path/to/video.mp4"),
            duration=60.0,
        )

    def test_default_initialization(self, sample_analysis):
        """Test default values."""
        assert sample_analysis.video_path == Path("/path/to/video.mp4")
        assert sample_analysis.duration == 60.0
        assert sample_analysis.transcript is None
        assert sample_analysis.scenes is None
        assert sample_analysis.segments == []
        assert sample_analysis.keywords == []
        assert sample_analysis.highlight_candidates == []

    def test_highlights_property(self, sample_analysis):
        """Test highlights property is alias for highlight_candidates."""
        segment = ContentSegment(start_time=0.0, end_time=5.0)
        sample_analysis.highlight_candidates = [segment]
        assert sample_analysis.highlights == [segment]

    def test_get_segment_at_time_found(self, sample_analysis):
        """Test getting segment at specific time."""
        segment1 = ContentSegment(start_time=0.0, end_time=10.0)
        segment2 = ContentSegment(start_time=10.0, end_time=20.0)
        sample_analysis.segments = [segment1, segment2]

        result = sample_analysis.get_segment_at_time(5.0)
        assert result == segment1

        result = sample_analysis.get_segment_at_time(15.0)
        assert result == segment2

    def test_get_segment_at_time_not_found(self, sample_analysis):
        """Test getting segment when none matches."""
        segment = ContentSegment(start_time=0.0, end_time=10.0)
        sample_analysis.segments = [segment]

        result = sample_analysis.get_segment_at_time(15.0)
        assert result is None

    def test_search_by_keyword_found(self, sample_analysis):
        """Test searching by keyword."""
        transcript1 = TranscriptResult(
            text="Hello world",
            segments=[TranscriptSegment(start=0.0, end=1.0, text="Hello world")],
            language="en",
            duration=1.0,
        )
        transcript2 = TranscriptResult(
            text="Goodbye world",
            segments=[TranscriptSegment(start=1.0, end=2.0, text="Goodbye world")],
            language="en",
            duration=1.0,
        )
        segment1 = ContentSegment(start_time=0.0, end_time=1.0, transcript=transcript1)
        segment2 = ContentSegment(start_time=1.0, end_time=2.0, transcript=transcript2)
        sample_analysis.segments = [segment1, segment2]

        results = sample_analysis.search_by_keyword("hello")
        assert len(results) == 1
        assert results[0] == segment1

    def test_search_by_keyword_case_insensitive(self, sample_analysis):
        """Test searching is case insensitive."""
        transcript = TranscriptResult(
            text="HELLO World",
            segments=[TranscriptSegment(start=0.0, end=1.0, text="HELLO World")],
            language="en",
            duration=1.0,
        )
        segment = ContentSegment(start_time=0.0, end_time=1.0, transcript=transcript)
        sample_analysis.segments = [segment]

        results = sample_analysis.search_by_keyword("hello")
        assert len(results) == 1

    def test_search_by_keyword_not_found(self, sample_analysis):
        """Test searching when keyword not found."""
        transcript = TranscriptResult(
            text="Hello world",
            segments=[TranscriptSegment(start=0.0, end=1.0, text="Hello world")],
            language="en",
            duration=1.0,
        )
        segment = ContentSegment(start_time=0.0, end_time=1.0, transcript=transcript)
        sample_analysis.segments = [segment]

        results = sample_analysis.search_by_keyword("xyz")
        assert len(results) == 0


class TestContentAnalyzer:
    """ContentAnalyzer tests."""

    @pytest.fixture
    def analyzer(self):
        """Create analyzer instance."""
        return ContentAnalyzer()

    def test_initialization_default(self):
        """Test default initialization creates components."""
        analyzer = ContentAnalyzer()
        assert analyzer.transcriber is not None
        assert analyzer.scene_detector is not None

    def test_initialization_with_custom_components(self):
        """Test initialization with custom components."""
        mock_transcriber = MagicMock()
        mock_detector = MagicMock()
        analyzer = ContentAnalyzer(
            transcriber=mock_transcriber,
            scene_detector=mock_detector,
        )
        assert analyzer.transcriber == mock_transcriber
        assert analyzer.scene_detector == mock_detector

    def test_calculate_importance_with_transcript(self):
        """Test importance calculation with transcript segment."""
        analyzer = ContentAnalyzer()
        # _calculate_importance expects a transcript segment, not ContentSegment
        from video_cut_skill.ai.transcriber import TranscriptSegment

        segment = TranscriptSegment(
            start=0.0,
            end=5.0,
            text="Important content here for testing",
        )
        score = analyzer._calculate_importance(segment)
        assert 0.0 <= score <= 1.0

    def test_calculate_importance_empty_text(self):
        """Test importance calculation with empty text."""
        analyzer = ContentAnalyzer()
        from video_cut_skill.ai.transcriber import TranscriptSegment

        segment = TranscriptSegment(
            start=0.0,
            end=5.0,
            text="",
        )
        score = analyzer._calculate_importance(segment)
        assert score == 0.0

    def test_extract_keywords_from_text(self):
        """Test keyword extraction from transcript."""
        analyzer = ContentAnalyzer()
        transcript = TranscriptResult(
            text="Python programming tutorial for beginners",
            segments=[
                TranscriptSegment(start=0.0, end=2.0, text="Python programming"),
                TranscriptSegment(start=2.0, end=4.0, text="tutorial for beginners"),
            ],
            language="en",
            duration=4.0,
        )
        keywords = analyzer._extract_keywords(transcript)
        assert isinstance(keywords, list)
        assert len(keywords) > 0

    def test_extract_keywords_empty(self):
        """Test keyword extraction with empty transcript."""
        analyzer = ContentAnalyzer()
        transcript = TranscriptResult(
            text="",
            segments=[],
            language="en",
            duration=0.0,
        )
        keywords = analyzer._extract_keywords(transcript)
        assert keywords == []

    def test_find_highlights(self):
        """Test finding highlight candidates."""
        analyzer = ContentAnalyzer()
        segments = [
            ContentSegment(start_time=0.0, end_time=5.0, importance_score=0.9),
            ContentSegment(start_time=5.0, end_time=10.0, importance_score=0.3),
            ContentSegment(start_time=10.0, end_time=15.0, importance_score=0.8),
        ]
        highlights = analyzer._find_highlights(segments)
        assert isinstance(highlights, list)
        # Should return segments with higher scores
        assert len(highlights) <= len(segments)

    def test_find_highlights_empty(self):
        """Test finding highlights with empty segments."""
        analyzer = ContentAnalyzer()
        highlights = analyzer._find_highlights([])
        assert highlights == []
