"""Tests for speaker recognition module."""

import json
import tempfile
from pathlib import Path

import numpy as np
import pytest

from video_cut_skill.speaker_recognition import (
    SpeakerAwareEditor,
    SpeakerDiarizationResult,
    SpeakerDiarizer,
    SpeakerProfile,
    SpeakerSegment,
    VoiceActivityDetector,
    VoiceActivitySegment,
    detect_voice_activity,
    diarize_speakers,
)


class TestVoiceActivitySegment:
    """Test VoiceActivitySegment class."""
    
    def test_segment_creation(self):
        """Test segment creation."""
        segment = VoiceActivitySegment(
            start=1.0,
            end=3.5,
            is_speech=True,
            confidence=0.95
        )
        
        assert segment.start == 1.0
        assert segment.end == 3.5
        assert segment.duration == 2.5
        assert segment.is_speech is True
        assert segment.confidence == 0.95
    
    def test_segment_serialization(self):
        """Test segment serialization."""
        segment = VoiceActivitySegment(start=0, end=5, is_speech=True)
        data = segment.to_dict()
        
        assert data["start"] == 0
        assert data["end"] == 5
        assert data["duration"] == 5
        assert data["is_speech"] is True


class TestSpeakerSegment:
    """Test SpeakerSegment class."""
    
    def test_segment_creation(self):
        """Test speaker segment creation."""
        segment = SpeakerSegment(
            start=0,
            end=10,
            speaker_id="SPEAKER_00",
            confidence=0.9
        )
        
        assert segment.start == 0
        assert segment.end == 10
        assert segment.duration == 10
        assert segment.speaker_id == "SPEAKER_00"
        assert segment.confidence == 0.9
    
    def test_segment_serialization(self):
        """Test speaker segment serialization."""
        segment = SpeakerSegment(start=0, end=5, speaker_id="SPEAKER_01")
        data = segment.to_dict()
        
        assert data["speaker_id"] == "SPEAKER_01"
        assert data["duration"] == 5


class TestSpeakerProfile:
    """Test SpeakerProfile class."""
    
    def test_profile_creation(self):
        """Test profile creation."""
        profile = SpeakerProfile(
            speaker_id="SPEAKER_00",
            name="John Doe",
            segments_count=5,
            total_duration=30.0
        )
        
        assert profile.speaker_id == "SPEAKER_00"
        assert profile.name == "John Doe"
        assert profile.segments_count == 5
        assert profile.total_duration == 30.0
    
    def test_profile_with_embedding(self):
        """Test profile with embedding."""
        embedding = np.array([0.1, 0.2, 0.3])
        profile = SpeakerProfile(
            speaker_id="SPEAKER_00",
            embedding=embedding
        )
        
        assert profile.embedding is not None
        np.testing.assert_array_equal(profile.embedding, embedding)
    
    def test_profile_serialization(self):
        """Test profile serialization."""
        profile = SpeakerProfile(
            speaker_id="SPEAKER_00",
            name="Test",
            segments_count=3,
            total_duration=15.0
        )
        
        data = profile.to_dict()
        
        assert data["speaker_id"] == "SPEAKER_00"
        assert data["name"] == "Test"
        assert data["has_embedding"] is False


class TestSpeakerDiarizationResult:
    """Test SpeakerDiarizationResult class."""
    
    def test_result_creation(self):
        """Test result creation."""
        speakers = [
            SpeakerProfile(speaker_id="SPEAKER_00"),
            SpeakerProfile(speaker_id="SPEAKER_01")
        ]
        
        segments = [
            SpeakerSegment(start=0, end=5, speaker_id="SPEAKER_00"),
            SpeakerSegment(start=5, end=10, speaker_id="SPEAKER_01")
        ]
        
        result = SpeakerDiarizationResult(
            segments=segments,
            speakers=speakers,
            duration=10.0,
            method="test"
        )
        
        assert result.num_speakers == 2
        assert result.duration == 10.0
        assert result.method == "test"
    
    def test_get_speaker_segments(self):
        """Test getting speaker segments."""
        segments = [
            SpeakerSegment(start=0, end=5, speaker_id="SPEAKER_00"),
            SpeakerSegment(start=5, end=8, speaker_id="SPEAKER_01"),
            SpeakerSegment(start=8, end=10, speaker_id="SPEAKER_00")
        ]
        
        result = SpeakerDiarizationResult(
            segments=segments,
            speakers=[],
            duration=10.0,
            method="test"
        )
        
        speaker0_segments = result.get_speaker_segments("SPEAKER_00")
        assert len(speaker0_segments) == 2
        
        speaker1_segments = result.get_speaker_segments("SPEAKER_01")
        assert len(speaker1_segments) == 1
    
    def test_get_speaker_duration(self):
        """Test getting speaker duration."""
        segments = [
            SpeakerSegment(start=0, end=5, speaker_id="SPEAKER_00"),
            SpeakerSegment(start=5, end=8, speaker_id="SPEAKER_01"),
            SpeakerSegment(start=8, end=10, speaker_id="SPEAKER_00")
        ]
        
        speakers = [
            SpeakerProfile(speaker_id="SPEAKER_00"),
            SpeakerProfile(speaker_id="SPEAKER_01")
        ]
        
        result = SpeakerDiarizationResult(
            segments=segments,
            speakers=speakers,
            duration=10.0,
            method="test"
        )
        
        assert result.get_speaker_duration("SPEAKER_00") == 7.0
        assert result.get_speaker_duration("SPEAKER_01") == 3.0
    
    def test_get_dominant_speaker(self):
        """Test getting dominant speaker."""
        segments = [
            SpeakerSegment(start=0, end=7, speaker_id="SPEAKER_00"),
            SpeakerSegment(start=7, end=10, speaker_id="SPEAKER_01")
        ]
        
        speakers = [
            SpeakerProfile(speaker_id="SPEAKER_00"),
            SpeakerProfile(speaker_id="SPEAKER_01")
        ]
        
        result = SpeakerDiarizationResult(
            segments=segments,
            speakers=speakers,
            duration=10.0,
            method="test"
        )
        
        dominant = result.get_dominant_speaker()
        assert dominant == "SPEAKER_00"
    
    def test_get_dominant_speaker_empty(self):
        """Test dominant speaker with empty result."""
        result = SpeakerDiarizationResult(
            segments=[],
            speakers=[],
            duration=0.0,
            method="test"
        )
        
        assert result.get_dominant_speaker() is None
    
    def test_serialization(self):
        """Test result serialization."""
        result = SpeakerDiarizationResult(
            segments=[SpeakerSegment(start=0, end=5, speaker_id="SPEAKER_00")],
            speakers=[SpeakerProfile(speaker_id="SPEAKER_00", name="Test")],
            duration=5.0,
            method="test"
        )
        
        data = result.to_dict()
        
        assert data["num_speakers"] == 1
        assert data["duration"] == 5.0
        assert len(data["segments"]) == 1


class TestVoiceActivityDetector:
    """Test VoiceActivityDetector class."""
    
    def test_initialization(self):
        """Test detector initialization."""
        detector = VoiceActivityDetector(
            aggressiveness=2,
            min_speech_duration=0.5
        )
        
        assert detector.aggressiveness == 2
        assert detector.min_speech_duration == 0.5
    
    def test_detect_nonexistent_file(self):
        """Test detection with non-existent file."""
        detector = VoiceActivityDetector()
        
        with pytest.raises(FileNotFoundError):
            detector.detect("/nonexistent/audio.mp3")


class TestSpeakerDiarizer:
    """Test SpeakerDiarizer class."""
    
    def test_initialization(self):
        """Test diarizer initialization."""
        diarizer = SpeakerDiarizer(
            method="basic",
            num_speakers=2,
            min_speakers=1,
            max_speakers=5
        )
        
        assert diarizer.method == "basic"
        assert diarizer.num_speakers == 2
        assert diarizer.min_speakers == 1
        assert diarizer.max_speakers == 5
    
    def test_method_resolution_auto(self):
        """Test method resolution for 'auto'."""
        diarizer = SpeakerDiarizer(method="auto")
        # Should resolve to available method
        assert diarizer.method in ["pyannote", "basic"]
    
    def test_diarize_nonexistent_file(self):
        """Test diarization with non-existent file."""
        diarizer = SpeakerDiarizer()
        
        with pytest.raises(FileNotFoundError):
            diarizer.diarize("/nonexistent/audio.mp3")
    
    def test_create_speaker_profile(self):
        """Test creating speaker profile."""
        diarizer = SpeakerDiarizer()
        
        # This would need a real audio file for full testing
        # For now, just test the interface
        profile = diarizer.create_speaker_profile(
            audio_path="dummy.mp3",
            speaker_id="SPEAKER_00",
            name="Test Speaker"
        )
        
        assert profile.speaker_id == "SPEAKER_00"
        assert profile.name == "Test Speaker"
    
    def test_compute_similarity(self):
        """Test embedding similarity computation."""
        diarizer = SpeakerDiarizer()
        
        # 相同向量，相似度应为 1
        emb1 = np.array([1.0, 0.0, 0.0])
        emb2 = np.array([1.0, 0.0, 0.0])
        
        similarity = diarizer._compute_similarity(emb1, emb2)
        assert abs(similarity - 1.0) < 1e-6
        
        # 正交向量，相似度应为 0
        emb3 = np.array([0.0, 1.0, 0.0])
        similarity = diarizer._compute_similarity(emb1, emb3)
        assert abs(similarity) < 1e-6
        
        # 相反向量，相似度应为 -1
        emb4 = np.array([-1.0, 0.0, 0.0])
        similarity = diarizer._compute_similarity(emb1, emb4)
        assert abs(similarity - (-1.0)) < 1e-6
    
    def test_compute_similarity_zero_vector(self):
        """Test similarity with zero vector."""
        diarizer = SpeakerDiarizer()
        
        emb1 = np.array([1.0, 0.0, 0.0])
        emb2 = np.array([0.0, 0.0, 0.0])
        
        similarity = diarizer._compute_similarity(emb1, emb2)
        assert similarity == 0.0


class TestSpeakerAwareEditor:
    """Test SpeakerAwareEditor class."""
    
    def test_initialization(self):
        """Test editor initialization."""
        editor = SpeakerAwareEditor()
        
        assert editor.diarizer is not None
        assert editor.vad is not None
    
    def test_initialization_with_custom_components(self):
        """Test initialization with custom components."""
        diarizer = SpeakerDiarizer(method="basic")
        vad = VoiceActivityDetector(aggressiveness=3)
        
        editor = SpeakerAwareEditor(diarizer=diarizer, vad=vad)
        
        assert editor.diarizer == diarizer
        assert editor.vad == vad
    
    def test_analyze_nonexistent_file(self):
        """Test analyze with non-existent file."""
        editor = SpeakerAwareEditor()
        
        with pytest.raises(FileNotFoundError):
            editor.analyze("/nonexistent/video.mp4")
    
    def test_get_speaker_timeline_without_analysis(self):
        """Test getting timeline without analysis."""
        editor = SpeakerAwareEditor()
        
        with pytest.raises(ValueError, match="No analysis result"):
            editor.get_speaker_timeline()
    
    def test_get_speaker_timeline(self):
        """Test getting speaker timeline."""
        editor = SpeakerAwareEditor()
        
        # 模拟分析结果
        editor._last_result = SpeakerDiarizationResult(
            segments=[
                SpeakerSegment(start=0, end=5, speaker_id="SPEAKER_00"),
                SpeakerSegment(start=5, end=10, speaker_id="SPEAKER_01")
            ],
            speakers=[
                SpeakerProfile(speaker_id="SPEAKER_00", name="Speaker A"),
                SpeakerProfile(speaker_id="SPEAKER_01", name="Speaker B")
            ],
            duration=10.0,
            method="test"
        )
        
        timeline = editor.get_speaker_timeline()
        
        assert len(timeline) == 2
        assert timeline[0]["speaker_name"] == "Speaker A"
        assert timeline[1]["speaker_name"] == "Speaker B"
    
    def test_extract_by_speaker_without_analysis(self):
        """Test extract without analysis."""
        editor = SpeakerAwareEditor()
        
        with pytest.raises(ValueError, match="No analysis result"):
            editor.extract_by_speaker()
    
    def test_extract_by_speaker_all(self):
        """Test extracting all speaker segments."""
        editor = SpeakerAwareEditor()
        
        editor._last_result = SpeakerDiarizationResult(
            segments=[
                SpeakerSegment(start=0, end=5, speaker_id="SPEAKER_00"),
                SpeakerSegment(start=5, end=10, speaker_id="SPEAKER_01")
            ],
            speakers=[
                SpeakerProfile(speaker_id="SPEAKER_00"),
                SpeakerProfile(speaker_id="SPEAKER_01")
            ],
            duration=10.0,
            method="test"
        )
        
        segments = editor.extract_by_speaker()
        
        assert len(segments) == 2
        assert segments[0] == (0, 5)
        assert segments[1] == (5, 10)
    
    def test_extract_by_specific_speaker(self):
        """Test extracting specific speaker segments."""
        editor = SpeakerAwareEditor()
        
        editor._last_result = SpeakerDiarizationResult(
            segments=[
                SpeakerSegment(start=0, end=5, speaker_id="SPEAKER_00"),
                SpeakerSegment(start=5, end=10, speaker_id="SPEAKER_01"),
                SpeakerSegment(start=10, end=15, speaker_id="SPEAKER_00")
            ],
            speakers=[
                SpeakerProfile(speaker_id="SPEAKER_00"),
                SpeakerProfile(speaker_id="SPEAKER_01")
            ],
            duration=15.0,
            method="test"
        )
        
        segments = editor.extract_by_speaker(speaker_id="SPEAKER_00")
        
        assert len(segments) == 2
        assert segments[0] == (0, 5)
        assert segments[1] == (10, 15)
    
    def test_extract_dominant_speaker(self):
        """Test extracting dominant speaker."""
        editor = SpeakerAwareEditor()
        
        editor._last_result = SpeakerDiarizationResult(
            segments=[
                SpeakerSegment(start=0, end=7, speaker_id="SPEAKER_00"),
                SpeakerSegment(start=7, end=10, speaker_id="SPEAKER_01")
            ],
            speakers=[
                SpeakerProfile(speaker_id="SPEAKER_00"),
                SpeakerProfile(speaker_id="SPEAKER_01")
            ],
            duration=10.0,
            method="test"
        )
        
        segments = editor.extract_by_speaker(dominant_only=True)
        
        assert len(segments) == 1
        assert segments[0] == (0, 7)
    
    def test_extract_with_min_duration(self):
        """Test extract with minimum duration filter."""
        editor = SpeakerAwareEditor()
        
        editor._last_result = SpeakerDiarizationResult(
            segments=[
                SpeakerSegment(start=0, end=0.5, speaker_id="SPEAKER_00"),
                SpeakerSegment(start=1, end=5, speaker_id="SPEAKER_00")
            ],
            speakers=[SpeakerProfile(speaker_id="SPEAKER_00")],
            duration=5.0,
            method="test"
        )
        
        segments = editor.extract_by_speaker(min_segment_duration=1.0)
        
        assert len(segments) == 1
        assert segments[0] == (1, 5)
    
    def test_create_speaker_subtitles_srt(self):
        """Test creating SRT subtitles."""
        editor = SpeakerAwareEditor()
        
        editor._last_result = SpeakerDiarizationResult(
            segments=[
                SpeakerSegment(start=0, end=5, speaker_id="SPEAKER_00"),
                SpeakerSegment(start=5, end=10, speaker_id="SPEAKER_01")
            ],
            speakers=[
                SpeakerProfile(speaker_id="SPEAKER_00", name="Alice"),
                SpeakerProfile(speaker_id="SPEAKER_01", name="Bob")
            ],
            duration=10.0,
            method="test"
        )
        
        srt = editor.create_speaker_subtitles(subtitle_format="srt")
        
        assert "1" in srt
        assert "00:00:00,000 --> 00:00:05,000" in srt
        assert "[Alice]" in srt
        assert "[Bob]" in srt
    
    def test_create_speaker_subtitles_vtt(self):
        """Test creating VTT subtitles."""
        editor = SpeakerAwareEditor()
        
        editor._last_result = SpeakerDiarizationResult(
            segments=[
                SpeakerSegment(start=0, end=5, speaker_id="SPEAKER_00")
            ],
            speakers=[SpeakerProfile(speaker_id="SPEAKER_00", name="Alice")],
            duration=5.0,
            method="test"
        )
        
        vtt = editor.create_speaker_subtitles(subtitle_format="vtt")
        
        assert "WEBVTT" in vtt
        assert "00:00:00.000 --> 00:00:05.000" in vtt
    
    def test_export_to_json_without_analysis(self):
        """Test export without analysis."""
        editor = SpeakerAwareEditor()
        
        with pytest.raises(ValueError, match="No analysis result"):
            with tempfile.NamedTemporaryFile(suffix=".json") as tmp:
                editor.export_to_json(tmp.name)
    
    def test_export_to_json(self):
        """Test exporting to JSON."""
        editor = SpeakerAwareEditor()
        
        editor._last_result = SpeakerDiarizationResult(
            segments=[SpeakerSegment(start=0, end=5, speaker_id="SPEAKER_00")],
            speakers=[SpeakerProfile(speaker_id="SPEAKER_00", name="Test")],
            duration=5.0,
            method="test"
        )
        
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as tmp:
            tmp_path = tmp.name
        
        try:
            editor.export_to_json(tmp_path)
            
            with open(tmp_path, "r") as f:
                data = json.load(f)
            
            assert data["duration"] == 5.0
            assert data["num_speakers"] == 1
            assert len(data["segments"]) == 1
        finally:
            Path(tmp_path).unlink(missing_ok=True)
    
    def test_time_formatting(self):
        """Test time formatting functions."""
        editor = SpeakerAwareEditor()
        
        # Test SRT format
        srt_time = editor._format_time_srt(3661.123)
        assert srt_time == "01:01:01,123"
        
        # Test VTT format
        vtt_time = editor._format_time_vtt(3661.123)
        assert vtt_time == "01:01:01.123"


class TestConvenienceFunctions:
    """Test convenience functions."""
    
    def test_detect_voice_activity_nonexistent(self):
        """Test detect_voice_activity with non-existent file."""
        with pytest.raises(FileNotFoundError):
            detect_voice_activity("/nonexistent/file.mp3")
    
    def test_diarize_speakers_nonexistent(self):
        """Test diarize_speakers with non-existent file."""
        with pytest.raises(FileNotFoundError):
            diarize_speakers("/nonexistent/file.mp3")


class TestSpeakerRecognitionIntegration:
    """Integration tests for speaker recognition."""
    
    def test_full_pipeline_simulation(self):
        """Test full pipeline simulation."""
        # 创建模拟的 diarization 结果
        result = SpeakerDiarizationResult(
            segments=[
                SpeakerSegment(start=0, end=5, speaker_id="SPEAKER_00"),
                SpeakerSegment(start=5, end=8, speaker_id="SPEAKER_01"),
                SpeakerSegment(start=8, end=12, speaker_id="SPEAKER_00")
            ],
            speakers=[
                SpeakerProfile(speaker_id="SPEAKER_00", name="Host"),
                SpeakerProfile(speaker_id="SPEAKER_01", name="Guest")
            ],
            duration=12.0,
            method="test"
        )
        
        # 验证说话人统计
        assert result.get_speaker_duration("SPEAKER_00") == 9.0
        assert result.get_speaker_duration("SPEAKER_01") == 3.0
        
        # 验证主导说话人
        dominant = result.get_dominant_speaker()
        assert dominant == "SPEAKER_00"
        
        # 验证片段查询
        host_segments = result.get_speaker_segments("SPEAKER_00")
        assert len(host_segments) == 2
        
        guest_segments = result.get_speaker_segments("SPEAKER_01")
        assert len(guest_segments) == 1
    
    def test_speaker_profile_embedding_operations(self):
        """Test speaker profile embedding operations."""
        # 创建带有 embedding 的 profile
        emb1 = np.random.randn(256)
        emb2 = np.random.randn(256)
        
        profile1 = SpeakerProfile(
            speaker_id="SPEAKER_00",
            embedding=emb1
        )
        
        profile2 = SpeakerProfile(
            speaker_id="SPEAKER_01",
            embedding=emb2
        )
        
        # 验证 embedding 存储
        assert profile1.embedding is not None
        assert profile1.embedding.shape == (256,)
        
        # 验证 serialization 不包含 embedding 数据
        data1 = profile1.to_dict()
        assert data1["has_embedding"] is True
        assert "embedding" not in data1
    
    def test_edge_cases(self):
        """Test edge cases."""
        # Empty result
        empty_result = SpeakerDiarizationResult(
            segments=[],
            speakers=[],
            duration=0.0,
            method="test"
        )
        
        assert empty_result.num_speakers == 0
        assert empty_result.get_dominant_speaker() is None
        
        # Single speaker
        single_result = SpeakerDiarizationResult(
            segments=[SpeakerSegment(start=0, end=10, speaker_id="SPEAKER_00")],
            speakers=[SpeakerProfile(speaker_id="SPEAKER_00")],
            duration=10.0,
            method="test"
        )
        
        assert single_result.num_speakers == 1
        assert single_result.get_dominant_speaker() == "SPEAKER_00"
        
        # Overlapping segments (shouldn't happen but test handling)
        overlapping_result = SpeakerDiarizationResult(
            segments=[
                SpeakerSegment(start=0, end=5, speaker_id="SPEAKER_00"),
                SpeakerSegment(start=3, end=8, speaker_id="SPEAKER_01")  # Overlap
            ],
            speakers=[
                SpeakerProfile(speaker_id="SPEAKER_00"),
                SpeakerProfile(speaker_id="SPEAKER_01")
            ],
            duration=8.0,
            method="test"
        )
        
        assert overlapping_result.num_speakers == 2
