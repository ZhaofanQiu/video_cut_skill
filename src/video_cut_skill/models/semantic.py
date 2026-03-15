"""Semantic models for interactive video editing."""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from enum import Enum


class SegmentType(Enum):
    """Type of content segment."""

    SPEECH = "speech"
    SILENCE = "silence"
    SCENE = "scene"
    TRANSITION = "transition"


class Modality(Enum):
    """Content modality."""

    AUDIO = "audio"
    VISUAL = "visual"
    HYBRID = "hybrid"


@dataclass
class WordTimestamp:
    """Word-level timestamp from ASR.

    Attributes:
        text: The word text
        begin_time: Start time in milliseconds
        end_time: End time in milliseconds
        punctuation: Punctuation after the word (if any)
    """

    text: str
    begin_time: int
    end_time: int
    punctuation: str = ""


@dataclass
class Sentence:
    """Sentence-level ASR result.

    Attributes:
        text: Full sentence text
        begin_time: Start time in milliseconds
        end_time: End time in milliseconds
        words: List of word-level timestamps
        speaker_id: Speaker identifier (if speaker diarization enabled)
    """

    text: str
    begin_time: int
    end_time: int
    words: List[WordTimestamp] = field(default_factory=list)
    speaker_id: Optional[int] = None


@dataclass
class TranscriptionResult:
    """Complete transcription result from ASR.

    Attributes:
        full_text: Complete transcribed text
        sentences: List of sentence results
        duration_ms: Total duration in milliseconds
        audio_format: Audio format (e.g., 'pcm_s16le')
        sample_rate: Audio sample rate in Hz
        channel_id: Audio channel index
        content_duration_ms: Actual speech duration (excluding silence)
    """

    full_text: str
    sentences: List[Sentence]
    duration_ms: int
    audio_format: str
    sample_rate: int
    channel_id: int = 0
    content_duration_ms: Optional[int] = None


@dataclass
class ContentSegment:
    """Unified semantic segment for video content.

    This is the core data unit for interactive editing, supporting
    both audio (speech) and visual content with a unified interface.

    Attributes:
        segment_id: Unique identifier
        start_time: Start time in seconds
        end_time: End time in seconds
        duration: Duration in seconds
        text: Transcribed text (for speech segments)
        visual_desc: Visual description (for visual segments, optional)
        segment_type: Type of segment
        modality: Content modality
        confidence: Detection confidence (0-1)
        summary: One-sentence summary (LLM-generated)
        keywords: Extracted keywords
        topics: Topic tags
        importance: Importance score (0-1)
        speaker_id: Speaker identifier
        filler_words: List of filler words with positions
        keyframe_path: Path to representative keyframe
        source_data: Raw source data reference
    """

    segment_id: str
    start_time: float
    end_time: float
    duration: float

    # Content (multi-modal)
    text: Optional[str] = None
    visual_desc: Optional[str] = None

    # Metadata
    segment_type: SegmentType = SegmentType.SPEECH
    modality: Modality = Modality.AUDIO
    confidence: float = 1.0

    # Semantic labels (LLM-generated)
    summary: Optional[str] = None
    keywords: List[str] = field(default_factory=list)
    topics: List[str] = field(default_factory=list)
    importance: float = 0.5

    # Audio-specific
    speaker_id: Optional[int] = None
    filler_words: List[Dict[str, Any]] = field(default_factory=list)

    # Visual-specific
    keyframe_path: Optional[str] = None

    # Source reference
    source_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class VideoSemantics:
    """Complete semantic representation of a video.

    Attributes:
        video_path: Path to the video file
        video_hash: Hash for caching
        duration: Total duration in seconds
        segments: List of semantic segments
        transcription: Raw transcription result
        all_topics: Aggregated topics
        all_keywords: Aggregated keywords
    """

    video_path: str
    video_hash: str
    duration: float
    segments: List[ContentSegment]
    transcription: Optional[TranscriptionResult] = None
    all_topics: List[str] = field(default_factory=list)
    all_keywords: List[str] = field(default_factory=list)

    def get_segment_by_time(self, time_sec: float) -> Optional[ContentSegment]:
        """Find segment containing the given time."""
        for seg in self.segments:
            if seg.start_time <= time_sec < seg.end_time:
                return seg
        return None

    def search_by_keyword(self, keyword: str) -> List[ContentSegment]:
        """Search segments by keyword."""
        results = []
        keyword_lower = keyword.lower()
        for seg in self.segments:
            text_match = seg.text and keyword_lower in seg.text.lower()
            summary_match = seg.summary and keyword_lower in seg.summary.lower()
            keyword_match = keyword_lower in [k.lower() for k in seg.keywords]
            if text_match or summary_match or keyword_match:
                results.append(seg)
        return results

    def get_segments_by_topic(self, topic: str) -> List[ContentSegment]:
        """Get segments by topic."""
        return [seg for seg in self.segments if topic in seg.topics]
