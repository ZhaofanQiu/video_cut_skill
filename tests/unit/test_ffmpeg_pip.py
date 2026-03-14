"""Tests for PIP (Picture-in-Picture) functionality."""

import pytest

from video_cut_skill.core.ffmpeg_wrapper import FFmpegWrapper


@pytest.fixture
def wrapper():
    """Create FFmpegWrapper instance."""
    return FFmpegWrapper()


@pytest.fixture
def sample_video(tmp_path):
    """Create a sample video for testing."""
    video_path = tmp_path / "test.mp4"
    # Create a simple test video using FFmpeg
    import subprocess

    subprocess.run(
        [
            "ffmpeg",
            "-f",
            "lavfi",
            "-i",
            "testsrc=duration=5:size=640x480:rate=30",
            "-pix_fmt",
            "yuv420p",
            "-y",
            str(video_path),
        ],
        capture_output=True,
        check=True,
    )
    return video_path


@pytest.fixture
def sample_video_2(tmp_path):
    """Create another sample video for testing."""
    video_path = tmp_path / "test2.mp4"
    import subprocess

    subprocess.run(
        [
            "ffmpeg",
            "-f",
            "lavfi",
            "-i",
            "testsrc=duration=3:size=320x240:rate=30",
            "-pix_fmt",
            "yuv420p",
            "-y",
            str(video_path),
        ],
        capture_output=True,
        check=True,
    )
    return video_path


class TestOverlayVideo:
    """Tests for overlay_video (PIP) functionality."""

    def test_overlay_video_basic(self, wrapper, sample_video, sample_video_2, tmp_path):
        """Test basic PIP functionality."""
        output = tmp_path / "output.mp4"
        result = wrapper.overlay_video(
            sample_video,
            sample_video_2,
            output,
            position="right_bottom",
            scale=0.25,
        )
        assert result.exists()
        info = wrapper.get_video_info(result)
        assert info["width"] == 640
        assert info["height"] == 480

    def test_overlay_video_position_left_top(self, wrapper, sample_video, sample_video_2, tmp_path):
        """Test PIP with left_top position."""
        output = tmp_path / "output.mp4"
        result = wrapper.overlay_video(
            sample_video,
            sample_video_2,
            output,
            position="left_top",
            scale=0.25,
        )
        assert result.exists()

    def test_overlay_video_position_right_top(self, wrapper, sample_video, sample_video_2, tmp_path):
        """Test PIP with right_top position."""
        output = tmp_path / "output.mp4"
        result = wrapper.overlay_video(
            sample_video,
            sample_video_2,
            output,
            position="right_top",
            scale=0.25,
        )
        assert result.exists()

    def test_overlay_video_position_left_bottom(self, wrapper, sample_video, sample_video_2, tmp_path):
        """Test PIP with left_bottom position."""
        output = tmp_path / "output.mp4"
        result = wrapper.overlay_video(
            sample_video,
            sample_video_2,
            output,
            position="left_bottom",
            scale=0.25,
        )
        assert result.exists()

    def test_overlay_video_position_center(self, wrapper, sample_video, sample_video_2, tmp_path):
        """Test PIP with center position."""
        output = tmp_path / "output.mp4"
        result = wrapper.overlay_video(
            sample_video,
            sample_video_2,
            output,
            position="center",
            scale=0.25,
        )
        assert result.exists()

    def test_overlay_video_custom_scale(self, wrapper, sample_video, sample_video_2, tmp_path):
        """Test PIP with custom scale."""
        output = tmp_path / "output.mp4"
        result = wrapper.overlay_video(
            sample_video,
            sample_video_2,
            output,
            position="right_bottom",
            scale=0.5,
        )
        assert result.exists()

    def test_overlay_video_custom_margin(self, wrapper, sample_video, sample_video_2, tmp_path):
        """Test PIP with custom margin."""
        output = tmp_path / "output.mp4"
        result = wrapper.overlay_video(
            sample_video,
            sample_video_2,
            output,
            position="right_bottom",
            scale=0.25,
            margin=50,
        )
        assert result.exists()

    def test_overlay_video_with_time_range(self, wrapper, sample_video, sample_video_2, tmp_path):
        """Test PIP with time range."""
        output = tmp_path / "output.mp4"
        result = wrapper.overlay_video(
            sample_video,
            sample_video_2,
            output,
            position="right_bottom",
            scale=0.25,
            start_time=1.0,
            end_time=3.0,
        )
        assert result.exists()

    def test_overlay_video_invalid_position(self, wrapper, sample_video, sample_video_2, tmp_path):
        """Test PIP with invalid position."""
        output = tmp_path / "output.mp4"
        with pytest.raises(ValueError, match="Invalid position"):
            wrapper.overlay_video(
                sample_video,
                sample_video_2,
                output,
                position="invalid_position",
                scale=0.25,
            )


class TestMergeVideosSideBySide:
    """Tests for merge_videos_side_by_side functionality."""

    def test_merge_side_by_side_basic(self, wrapper, sample_video, sample_video_2, tmp_path):
        """Test basic side-by-side merge."""
        output = tmp_path / "output.mp4"
        result = wrapper.merge_videos_side_by_side(
            sample_video,
            sample_video_2,
            output,
        )
        assert result.exists()
        info = wrapper.get_video_info(result)
        # Output should be side-by-side, so width should be wider
        assert info["width"] > 640

    def test_merge_side_by_side_fit_mode(self, wrapper, sample_video, sample_video_2, tmp_path):
        """Test side-by-side merge with fit mode."""
        output = tmp_path / "output.mp4"
        result = wrapper.merge_videos_side_by_side(
            sample_video,
            sample_video_2,
            output,
            mode="fit",
        )
        assert result.exists()

    def test_merge_side_by_side_stretch_mode(self, wrapper, sample_video, sample_video_2, tmp_path):
        """Test side-by-side merge with stretch mode."""
        output = tmp_path / "output.mp4"
        result = wrapper.merge_videos_side_by_side(
            sample_video,
            sample_video_2,
            output,
            mode="stretch",
        )
        assert result.exists()

    def test_merge_side_by_side_fill_mode(self, wrapper, sample_video, sample_video_2, tmp_path):
        """Test side-by-side merge with fill mode."""
        output = tmp_path / "output.mp4"
        result = wrapper.merge_videos_side_by_side(
            sample_video,
            sample_video_2,
            output,
            mode="fill",
        )
        assert result.exists()


class TestStackVideosVertical:
    """Tests for stack_videos_vertical functionality."""

    def test_stack_vertical_basic(self, wrapper, sample_video, sample_video_2, tmp_path):
        """Test basic vertical stack."""
        output = tmp_path / "output.mp4"
        result = wrapper.stack_videos_vertical(
            sample_video,
            sample_video_2,
            output,
        )
        assert result.exists()
        info = wrapper.get_video_info(result)
        # Output should be stacked, so height should be taller
        assert info["height"] > 480

    def test_stack_vertical_fit_mode(self, wrapper, sample_video, sample_video_2, tmp_path):
        """Test vertical stack with fit mode."""
        output = tmp_path / "output.mp4"
        result = wrapper.stack_videos_vertical(
            sample_video,
            sample_video_2,
            output,
            mode="fit",
        )
        assert result.exists()

    def test_stack_vertical_stretch_mode(self, wrapper, sample_video, sample_video_2, tmp_path):
        """Test vertical stack with stretch mode."""
        output = tmp_path / "output.mp4"
        result = wrapper.stack_videos_vertical(
            sample_video,
            sample_video_2,
            output,
            mode="stretch",
        )
        assert result.exists()

    def test_stack_vertical_fill_mode(self, wrapper, sample_video, sample_video_2, tmp_path):
        """Test vertical stack with fill mode."""
        output = tmp_path / "output.mp4"
        result = wrapper.stack_videos_vertical(
            sample_video,
            sample_video_2,
            output,
            mode="fill",
        )
        assert result.exists()
