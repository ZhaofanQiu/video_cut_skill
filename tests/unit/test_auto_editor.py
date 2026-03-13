"""Tests for AutoEditor."""

import pytest

from video_cut_skill.auto_editor import AutoEditor, EditConfig


class TestAutoEditor:
    """AutoEditor 测试."""

    def test_initialization(self):
        """测试初始化."""
        editor = AutoEditor()
        assert editor.ffmpeg is not None
        assert editor.scene_detector is not None
        assert editor.transcriber is None

    def test_process_video_file_not_found(self):
        """测试文件不存在."""
        editor = AutoEditor()
        with pytest.raises(FileNotFoundError):
            editor.process_video(
                video_path="/nonexistent/video.mp4",
                config=EditConfig(),
            )
