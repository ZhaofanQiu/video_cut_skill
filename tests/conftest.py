"""Test configuration and fixtures."""

import pytest
from pathlib import Path


@pytest.fixture
def test_data_dir() -> Path:
    """测试数据目录."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_video_path(test_data_dir: Path) -> Path:
    """示例视频路径."""
    return test_data_dir / "sample.mp4"
