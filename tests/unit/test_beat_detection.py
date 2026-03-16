"""Tests for beat detection module."""

import tempfile
from pathlib import Path

import numpy as np
import pytest

from video_cut_skill.beat_detection import (
    BeatDetector,
    BeatInfo,
    BeatDetectionResult,
    BeatMatchingResult,
    BeatSyncEditor,
    CutPoint,
    detect_beats,
    generate_beat_cuts,
)


class TestBeatInfo:
    """Test BeatInfo class."""
    
    def test_beat_info_creation(self):
        """Test beat info creation."""
        beat = BeatInfo(
            time=1.5,
            strength=0.8,
            is_downbeat=True,
            bpm=120.0
        )
        
        assert beat.time == 1.5
        assert beat.strength == 0.8
        assert beat.is_downbeat is True
        assert beat.bpm == 120.0
    
    def test_beat_info_serialization(self):
        """Test beat info serialization."""
        beat = BeatInfo(time=1.0, strength=0.5, is_downbeat=False, bpm=120.0)
        data = beat.to_dict()
        
        assert data["time"] == 1.0
        assert data["strength"] == 0.5
        assert data["is_downbeat"] is False
        assert data["bpm"] == 120.0


class TestBeatDetectionResult:
    """Test BeatDetectionResult class."""
    
    def test_result_creation(self):
        """Test result creation."""
        beats = [
            BeatInfo(time=0.0, is_downbeat=True),
            BeatInfo(time=0.5, is_downbeat=False),
            BeatInfo(time=1.0, is_downbeat=False),
            BeatInfo(time=1.5, is_downbeat=False),
            BeatInfo(time=2.0, is_downbeat=True),
        ]
        
        result = BeatDetectionResult(
            bpm=120.0,
            beats=beats,
            downbeats=[beats[0], beats[4]],
            duration=60.0,
            method="librosa"
        )
        
        assert result.bpm == 120.0
        assert result.beat_count == 5
        assert result.downbeat_count == 2
        assert result.duration == 60.0
        assert result.method == "librosa"
    
    def test_get_beats_in_range(self):
        """Test getting beats in range."""
        beats = [
            BeatInfo(time=1.0),
            BeatInfo(time=2.0),
            BeatInfo(time=3.0),
            BeatInfo(time=4.0),
        ]
        
        result = BeatDetectionResult(
            bpm=120.0,
            beats=beats,
            downbeats=[],
            duration=10.0,
            method="test"
        )
        
        in_range = result.get_beats_in_range(1.5, 3.5)
        assert len(in_range) == 2
        assert in_range[0].time == 2.0
        assert in_range[1].time == 3.0
    
    def test_get_nearest_beat(self):
        """Test getting nearest beat."""
        beats = [
            BeatInfo(time=1.0),
            BeatInfo(time=2.0),
            BeatInfo(time=3.0),
        ]
        
        result = BeatDetectionResult(
            bpm=120.0,
            beats=beats,
            downbeats=[],
            duration=10.0,
            method="test"
        )
        
        nearest = result.get_nearest_beat(1.6)
        assert nearest is not None
        assert nearest.time == 2.0
        
        nearest = result.get_nearest_beat(2.4)
        assert nearest.time == 2.0
    
    def test_serialization(self):
        """Test result serialization."""
        beats = [BeatInfo(time=0.0), BeatInfo(time=0.5)]
        result = BeatDetectionResult(
            bpm=120.0,
            beats=beats,
            downbeats=[beats[0]],
            duration=60.0,
            method="test"
        )
        
        data = result.to_dict()
        
        assert data["bpm"] == 120.0
        assert data["beat_count"] == 2
        assert data["duration"] == 60.0


class TestCutPoint:
    """Test CutPoint class."""
    
    def test_cut_point_creation(self):
        """Test cut point creation."""
        beat = BeatInfo(time=1.0, strength=0.8)
        
        cut = CutPoint(
            time=1.0,
            beat=beat,
            confidence=0.9,
            reason="downbeat"
        )
        
        assert cut.time == 1.0
        assert cut.beat == beat
        assert cut.confidence == 0.9
        assert cut.reason == "downbeat"


class TestBeatMatchingResult:
    """Test BeatMatchingResult class."""
    
    def test_result_creation(self):
        """Test result creation."""
        cut_points = [
            CutPoint(time=0.0),
            CutPoint(time=5.0),
            CutPoint(time=10.0),
        ]
        
        result = BeatMatchingResult(
            cut_points=cut_points,
            target_duration=30.0,
            actual_duration=10.0,
            beat_sync_rate=1.0
        )
        
        assert len(result.cut_points) == 3
        assert result.target_duration == 30.0
        assert result.actual_duration == 10.0
        assert result.beat_sync_rate == 1.0
    
    def test_serialization(self):
        """Test serialization."""
        result = BeatMatchingResult(
            cut_points=[CutPoint(time=0.0), CutPoint(time=5.0)],
            target_duration=30.0,
            actual_duration=5.0,
            beat_sync_rate=1.0
        )
        
        data = result.to_dict()
        
        assert data["target_duration"] == 30.0
        assert data["cut_point_count"] == 2
        assert data["beat_sync_rate"] == 1.0


class TestBeatDetector:
    """Test BeatDetector class."""
    
    def test_initialization(self):
        """Test detector initialization."""
        detector = BeatDetector(method="librosa", bpm_range=(60, 180))
        
        assert detector.bpm_range == (60, 180)
        assert detector.min_beat_strength == 0.3
    
    def test_method_resolution_auto(self):
        """Test method resolution for 'auto'."""
        detector = BeatDetector(method="auto")
        # Should resolve to available method
        assert detector.method in ["librosa", "madmom", "basic"]
    
    def test_method_resolution_specific(self):
        """Test specific method resolution."""
        detector = BeatDetector(method="librosa")
        assert detector.method == "librosa"
        
        detector = BeatDetector(method="basic")
        assert detector.method == "basic"
    
    def test_detect_nonexistent_file(self):
        """Test detection with non-existent file."""
        detector = BeatDetector()
        
        with pytest.raises(FileNotFoundError):
            detector.detect("/nonexistent/file.mp3")
    
    def test_generate_cuts_without_beats(self):
        """Test cut generation without beat detection."""
        detector = BeatDetector()
        
        # Create a mock result with no beats
        result = BeatDetectionResult(
            bpm=120.0,
            beats=[],
            downbeats=[],
            duration=60.0,
            method="basic"
        )
        
        cuts = detector.generate_cuts(
            beat_result=result,
            target_duration=30.0,
            align_to_beat=True
        )
        
        assert len(cuts.cut_points) > 0
        assert cuts.beat_sync_rate == 0.0
    
    def test_generate_cuts_with_beats(self):
        """Test cut generation with beats."""
        detector = BeatDetector()
        
        # Create mock beats
        beats = [
            BeatInfo(time=i * 0.5, strength=0.8, is_downbeat=(i % 4 == 0))
            for i in range(20)
        ]
        downbeats = [b for b in beats if b.is_downbeat]
        
        result = BeatDetectionResult(
            bpm=120.0,
            beats=beats,
            downbeats=downbeats,
            duration=10.0,
            method="test"
        )
        
        cuts = detector.generate_cuts(
            beat_result=result,
            target_duration=5.0,
            align_to_beat=True,
            prefer_downbeat=True
        )
        
        assert len(cuts.cut_points) > 0
        assert cuts.beat_sync_rate > 0
    
    def test_generate_uniform_cuts(self):
        """Test uniform cut generation fallback."""
        detector = BeatDetector()
        
        result = BeatDetectionResult(
            bpm=120.0,
            beats=[],
            downbeats=[],
            duration=60.0,
            method="basic"
        )
        
        cuts = detector.generate_cuts(
            beat_result=result,
            target_duration=30.0,
            align_to_beat=False,
            min_segment_duration=3.0,
            max_segment_duration=6.0
        )
        
        assert len(cuts.cut_points) > 0
        # Check that cuts are roughly uniform
        for i in range(len(cuts.cut_points) - 1):
            duration = cuts.cut_points[i+1].time - cuts.cut_points[i].time
            assert 2.0 <= duration <= 7.0  # Allow some variance
    
    def test_get_tempo_changes(self):
        """Test tempo change detection."""
        detector = BeatDetector()
        
        # Create mock result
        beats = [BeatInfo(time=i * 0.5, bpm=120.0) for i in range(100)]
        result = BeatDetectionResult(
            bpm=120.0,
            beats=beats,
            downbeats=[],
            duration=50.0,
            method="test"
        )
        
        detector._last_result = result
        changes = detector.get_tempo_changes(window_size=10.0)
        
        # Should detect at least one tempo point
        assert isinstance(changes, list)
    
    def test_sync_video_to_beats(self):
        """Test video segment alignment to beats."""
        detector = BeatDetector()
        
        # Create mock beats
        beats = [BeatInfo(time=float(i), strength=0.8) for i in range(10)]
        result = BeatDetectionResult(
            bpm=60.0,
            beats=beats,
            downbeats=[beats[0], beats[4], beats[8]],
            duration=10.0,
            method="test"
        )
        
        # Test segments
        segments = [(0.9, 2.1), (3.9, 5.1)]
        aligned = detector.sync_video_to_beats(
            video_segments=segments,
            beat_result=result
        )
        
        assert len(aligned) == 2
        # Segments should be aligned to nearest beats


class TestBeatSyncEditor:
    """Test BeatSyncEditor class."""
    
    def test_initialization(self):
        """Test editor initialization."""
        detector = BeatDetector()
        editor = BeatSyncEditor(detector=detector)
        
        assert editor.detector == detector
        assert editor.beat_result is None
    
    def test_load_audio_without_file(self):
        """Test load_audio without file."""
        editor = BeatSyncEditor()
        
        with pytest.raises(FileNotFoundError):
            editor.load_audio("/nonexistent/audio.mp3")
    
    def test_create_beat_cut_strategy_without_audio(self):
        """Test creating strategy without loaded audio."""
        editor = BeatSyncEditor()
        
        with pytest.raises(ValueError):
            editor.create_beat_cut_strategy()
    
    def test_suggest_b_roll_insertion_points_without_audio(self):
        """Test B-roll suggestions without loaded audio."""
        editor = BeatSyncEditor()
        
        with pytest.raises(ValueError):
            editor.suggest_b_roll_insertion_points()
    
    def test_suggest_b_roll_insertion_points(self):
        """Test B-roll insertion point suggestions."""
        editor = BeatSyncEditor()
        
        # Create mock beat result
        beats = [
            BeatInfo(time=0.0, strength=1.0, is_downbeat=True),
            BeatInfo(time=0.5, strength=0.3, is_downbeat=False),  # Weak beat
            BeatInfo(time=1.0, strength=0.8, is_downbeat=False),  # Strong beat
            BeatInfo(time=1.5, strength=0.4, is_downbeat=False),  # Weak beat
            BeatInfo(time=2.0, strength=1.0, is_downbeat=True),
        ]
        
        editor.beat_result = BeatDetectionResult(
            bpm=120.0,
            beats=beats,
            downbeats=[beats[0], beats[4]],
            duration=10.0,
            method="test"
        )
        
        suggestions = editor.suggest_b_roll_insertion_points(min_interval=1.0)
        
        assert isinstance(suggestions, list)
        # Should suggest weak beats for B-roll
    
    def test_get_beat_markers(self):
        """Test beat markers export."""
        editor = BeatSyncEditor()
        
        # Create mock beat result
        beats = [
            BeatInfo(time=0.0, is_downbeat=True),
            BeatInfo(time=0.5, is_downbeat=False),
        ]
        
        editor.beat_result = BeatDetectionResult(
            bpm=120.0,
            beats=beats,
            downbeats=[beats[0]],
            duration=1.0,
            method="test"
        )
        
        markers = editor.get_beat_markers_for_export()
        
        assert len(markers) == 2
        assert markers[0]["type"] == "downbeat"
        assert markers[1]["type"] == "beat"
        assert markers[0]["label"] == "D"
        assert markers[1]["label"] == "B"
    
    def test_export_to_json_without_audio(self):
        """Test export without loaded audio."""
        editor = BeatSyncEditor()
        
        with pytest.raises(ValueError):
            editor.export_to_json("output.json")


class TestConvenienceFunctions:
    """Test convenience functions."""
    
    def test_detect_beats_nonexistent(self):
        """Test detect_beats with non-existent file."""
        with pytest.raises(FileNotFoundError):
            detect_beats("/nonexistent/file.mp3")
    
    def test_generate_beat_cuts_nonexistent(self):
        """Test generate_beat_cuts with non-existent file."""
        with pytest.raises(FileNotFoundError):
            generate_beat_cuts("/nonexistent/file.mp3")


class TestBasicDetection:
    """Test basic detection without external libraries."""
    
    def test_basic_detection(self):
        """Test basic detection method."""
        detector = BeatDetector(method="basic")
        
        # Create a temporary audio file mock
        # Note: This would require a real audio file for full testing
        # For now, just test the detector configuration
        assert detector.method == "basic"
