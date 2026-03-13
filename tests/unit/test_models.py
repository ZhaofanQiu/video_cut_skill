"""Tests for core models."""

import pytest

from video_cut_skill.core.models import Clip, Project, Timeline, Track


class TestClip:
    """Clip 模型测试."""

    def test_clip_creation(self):
        """测试创建 Clip."""
        clip = Clip(
            source_path="test.mp4",
            start_time=0.0,
            end_time=10.0,
        )
        assert clip.source_path == "test.mp4"
        assert clip.start_time == 0.0
        assert clip.end_time == 10.0
        assert clip.duration == 10.0

    def test_clip_invalid_time(self):
        """测试无效时间."""
        with pytest.raises(ValueError):
            Clip(
                source_path="test.mp4",
                start_time=10.0,
                end_time=5.0,  # end < start
            )

    def test_clip_negative_start(self):
        """测试负开始时间."""
        with pytest.raises(ValueError):
            Clip(
                source_path="test.mp4",
                start_time=-1.0,
                end_time=10.0,
            )


class TestTrack:
    """Track 模型测试."""

    def test_track_creation(self):
        """测试创建 Track."""
        track = Track(name="Video 1", track_type="video")
        assert track.name == "Video 1"
        assert track.track_type == "video"

    def test_add_clip(self):
        """测试添加 Clip."""
        track = Track(name="Video", track_type="video")
        clip = Clip(source_path="test.mp4", start_time=0.0, end_time=5.0)
        track.add_clip(clip)
        assert len(track.clips) == 1


class TestTimeline:
    """Timeline 模型测试."""

    def test_timeline_creation(self):
        """测试创建 Timeline."""
        timeline = Timeline()
        assert timeline.duration == 0.0
        assert timeline.resolution == (1920, 1080)

    def test_add_track(self):
        """测试添加 Track."""
        timeline = Timeline()
        track = Track(name="Video", track_type="video")
        timeline.add_track(track)
        assert len(timeline.tracks) == 1
        assert track.index == 0


class TestProject:
    """Project 模型测试."""

    def test_project_creation(self):
        """测试创建 Project."""
        project = Project(name="Test Project")
        assert project.name == "Test Project"
