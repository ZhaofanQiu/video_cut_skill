"""Utilities module."""

import logging
import sys

from video_cut_skill.utils.cache import (
    CachedSceneDetector,
    CachedTranscriber,
    CacheManager,
)
from video_cut_skill.utils.hardware import HardwareInfo, get_optimal_device


def get_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """获取配置好的 logger.

    Args:
        name: logger 名称
        level: 日志级别

    Returns:
        logging.Logger: 配置好的 logger
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(level)
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger


__all__ = [
    "CacheManager",
    "CachedTranscriber",
    "CachedSceneDetector",
    "HardwareInfo",
    "get_optimal_device",
    "get_logger",
]
