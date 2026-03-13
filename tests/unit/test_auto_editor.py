"""Tests for AutoEditor."""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from video_cut_skill.auto_editor import AutoEditor, EditIntent


class TestAutoEditor:
    """AutoEditor 测试."""

    def test_initialization(self):
        """测试初始化."""
        editor = AutoEditor()
        assert editor.engine is not None
        assert editor.analyzer is not None
        assert editor.strategy is not None

    def test_auto_edit_file_not_found(self):
        """测试文件不存在."""
        editor = AutoEditor()
        with pytest.raises(FileNotFoundError):
            editor.auto_edit(
                video_path="/nonexistent/video.mp4",
                intent=EditIntent(),
            )

    @patch("video_cut_skill.auto_editor.Path.exists")
    def test_auto_edit_success(self, mock_exists):
        """测试成功剪辑."""
        mock_exists.return_value = True

        # Mock 依赖
        editor = AutoEditor()
        editor.analyzer = Mock()
        editor.strategy = Mock()
        editor.mg_renderer = Mock()
        editor.engine = Mock()

        # 设置返回值
        editor.analyzer.analyze.return_value = Mock(duration=60.0)
        editor.strategy.generate.return_value = Mock(
            segments=[],
            mg_specs=[],
        )
        editor.mg_renderer.generate.return_value = Mock(assets=[])
        editor.engine.execute.return_value = "/path/to/output.mp4"

        result = editor.auto_edit(
            video_path="/path/to/input.mp4",
            intent=EditIntent(target_duration=30.0),
        )

        assert result.output_path == Path("/path/to/output.mp4")
        editor.analyzer.analyze.assert_called_once()
        editor.strategy.generate.assert_called_once()
