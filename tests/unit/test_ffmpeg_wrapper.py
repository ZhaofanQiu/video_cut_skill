"""Tests for FFmpeg wrapper."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from video_cut_skill.core.ffmpeg_wrapper import FFmpegWrapper, FFmpegError


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
    
    def test_probe_success(self):
        """测试成功获取视频信息."""
        with patch("subprocess.run") as mock_run, \
             patch("ffmpeg.probe") as mock_probe:
            mock_run.return_value = Mock(stdout="version", returncode=0)
            mock_probe.return_value = {
                "streams": [
                    {"codec_type": "video", "width": 1920, "height": 1080},
                    {"codec_type": "audio"},
                ],
                "format": {"duration": "60.0"},
            }
            
            wrapper = FFmpegWrapper()
            result = wrapper.probe("test.mp4")
            
            assert result["format"]["duration"] == "60.0"
            assert len(result["streams"]) == 2
    
    def test_probe_failure(self):
        """测试获取信息失败."""
        with patch("subprocess.run") as mock_run, \
             patch("ffmpeg.probe") as mock_probe:
            mock_run.return_value = Mock(stdout="version", returncode=0)
            mock_probe.side_effect = ffmpeg.Error(
                "ffprobe", b"", b"Error: file not found"
            )
            
            wrapper = FFmpegWrapper()
            with pytest.raises(FFmpegError):
                wrapper.probe("nonexistent.mp4")
    
    def test_get_video_info(self):
        """测试获取视频信息摘要."""
        with patch("subprocess.run") as mock_run, \
             patch("ffmpeg.probe") as mock_probe:
            mock_run.return_value = Mock(stdout="version", returncode=0)
            mock_probe.return_value = {
                "streams": [
                    {
                        "codec_type": "video",
                        "width": 1920,
                        "height": 1080,
                        "r_frame_rate": "30/1",
                        "codec_name": "h264",
                    },
                    {"codec_type": "audio"},
                ],
                "format": {"duration": "60.0", "bit_rate": "1000000"},
            }
            
            wrapper = FFmpegWrapper()
            info = wrapper.get_video_info("test.mp4")
            
            assert info["duration"] == 60.0
            assert info["width"] == 1920
            assert info["height"] == 1080
            assert info["fps"] == 30.0
            assert info["codec"] == "h264"
            assert info["has_audio"] is True
    
    def test_get_video_info_no_video_stream(self):
        """测试没有视频流的情况."""
        with patch("subprocess.run") as mock_run, \
             patch("ffmpeg.probe") as mock_probe:
            mock_run.return_value = Mock(stdout="version", returncode=0)
            mock_probe.return_value = {
                "streams": [{"codec_type": "audio"}],
                "format": {"duration": "60.0"},
            }
            
            wrapper = FFmpegWrapper()
            with pytest.raises(FFmpegError):
                wrapper.get_video_info("audio_only.mp3")


class TestFFmpegWrapperCut:
    """剪辑功能测试."""
    
    def test_cut_clip_success(self):
        """测试成功剪辑."""
        with patch("subprocess.run") as mock_run, \
             patch("ffmpeg.input") as mock_input, \
             patch("ffmpeg.output") as mock_output, \
             patch("ffmpeg.run") as mock_run_ffmpeg:
            mock_run.return_value = Mock(stdout="version", returncode=0)
            
            wrapper = FFmpegWrapper()
            result = wrapper.cut_clip(
                "input.mp4",
                "output.mp4",
                start_time=10.0,
                end_time=20.0,
            )
            
            assert result == Path("output.mp4")
            mock_run_ffmpeg.assert_called_once()
    
    def test_cut_clip_failure(self):
        """测试剪辑失败."""
        with patch("subprocess.run") as mock_run, \
             patch("ffmpeg.input") as mock_input, \
             patch("ffmpeg.output") as mock_output, \
             patch("ffmpeg.run") as mock_run_ffmpeg:
            mock_run.return_value = Mock(stdout="version", returncode=0)
            mock_run_ffmpeg.side_effect = ffmpeg.Error(
                "ffmpeg", b"", b"Error: invalid input"
            )
            
            wrapper = FFmpegWrapper()
            with pytest.raises(FFmpegError):
                wrapper.cut_clip("input.mp4", "output.mp4", 0, 10)


class TestFFmpegWrapperConcatenate:
    """拼接功能测试."""
    
    def test_concatenate_clips_empty(self):
        """测试空列表."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(stdout="version", returncode=0)
            
            wrapper = FFmpegWrapper()
            with pytest.raises(FFmpegError):
                wrapper.concatenate_clips([], "output.mp4")
    
    def test_concatenate_clips_success(self):
        """测试成功拼接."""
        with patch("subprocess.run") as mock_run, \
             patch("ffmpeg.input") as mock_input, \
             patch("ffmpeg.output") as mock_output, \
             patch("ffmpeg.run") as mock_run_ffmpeg, \
             patch("tempfile.NamedTemporaryFile") as mock_temp:
            mock_run.return_value = Mock(stdout="version", returncode=0)
            mock_temp.return_value.__enter__.return_value = Mock(
                name="temp.txt",
                write=Mock(),
            )
            
            wrapper = FFmpegWrapper()
            result = wrapper.concatenate_clips(
                ["clip1.mp4", "clip2.mp4"],
                "output.mp4",
                reencode=False,
            )
            
            assert result == Path("output.mp4")


# 需要导入 ffmpeg 模块以进行模拟
import ffmpeg
