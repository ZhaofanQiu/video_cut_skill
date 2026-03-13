"""Tests for AutoEditor."""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from video_cut_skill.auto_editor import AutoEditor, EditConfig, EditResult
from video_cut_skill.core.ffmpeg_wrapper import FFmpegWrapper


class TestAutoEditor:
    """AutoEditor 测试."""

    def test_initialization(self):
        """测试初始化."""
        editor = AutoEditor()
        assert editor.ffmpeg is not None
        assert editor.scene_detector is not None
        assert editor.transcriber is None  # 默认未初始化

    def test_initialization_with_custom_ffmpeg(self):
        """测试使用自定义 FFmpeg 初始化."""
        mock_ffmpeg = Mock(spec=FFmpegWrapper)
        editor = AutoEditor(ffmpeg=mock_ffmpeg)
        assert editor.ffmpeg is mock_ffmpeg

    @patch("video_cut_skill.auto_editor.Path.exists")
    def test_process_video_file_not_found(self, mock_exists):
        """测试文件不存在."""
        mock_exists.return_value = False

        editor = AutoEditor()
        with pytest.raises(FileNotFoundError):
            editor.process_video(
                video_path="/nonexistent/video.mp4",
                config=EditConfig(),
            )

    @patch("video_cut_skill.auto_editor.Path.exists")
    @patch("video_cut_skill.auto_editor.FFmpegWrapper.get_video_info")
    def test_process_video_success(self, mock_get_info, mock_exists):
        """测试成功处理视频."""
        mock_exists.return_value = True
        mock_get_info.return_value = {
            "duration": 60.0,
            "width": 1920,
            "height": 1080,
            "fps": 30.0,
            "bitrate": 5000000,
            "codec": "h264",
            "has_audio": True,
        }

        editor = AutoEditor()
        # 使用 Mock 替换 ffmpeg.cut_clip 和 shutil.copy
        with patch("video_cut_skill.auto_editor.FFmpegWrapper.cut_clip") as mock_cut, patch("shutil.copy") as mock_copy:
            mock_cut.return_value = Path("/tmp/output.mp4")
            mock_copy.return_value = None

            result = editor.process_video(
                video_path="/path/to/input.mp4",
                config=EditConfig(target_duration=30.0, add_subtitles=False),
            )

            assert isinstance(result, EditResult)
            assert result.output_path is not None
            mock_cut.assert_called_once()
