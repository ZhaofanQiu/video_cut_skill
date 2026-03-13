"""Tests for FFmpeg wrapper."""

from unittest.mock import Mock, patch

import pytest

from video_cut_skill.core.ffmpeg_wrapper import FFmpegError, FFmpegWrapper


class TestFFmpegWrapper:
    """FFmpegWrapper 测试类."""

    def test_initialization_success(self):
        """测试成功初始化."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                stdout="ffmpeg version 4.4.2\n",
                returncode=0,
            )
            wrapper = FFmpegWrapper()
            assert wrapper.ffmpeg_path == "ffmpeg"
            assert wrapper.ffprobe_path == "ffprobe"

    def test_initialization_failure(self):
        """测试初始化失败."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError("ffmpeg not found")
            with pytest.raises(FFmpegError):
                FFmpegWrapper()


class TestFFmpegWrapperConcatenate:
    """拼接功能测试."""

    def test_concatenate_clips_empty(self):
        """测试空列表."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(stdout="version", returncode=0)

            wrapper = FFmpegWrapper()
            with pytest.raises(FFmpegError):
                wrapper.concatenate_clips([], "output.mp4")
