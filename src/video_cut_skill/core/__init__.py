"""Core engine module."""

from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import ffmpeg

from video_cut_skill.core.project import Project
from video_cut_skill.utils.logger import get_logger

logger = get_logger(__name__)


class EditingEngine:
    """视频编辑核心引擎.
    
    负责执行编辑项目，调用 FFmpeg 进行视频处理.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """初始化引擎.
        
        Args:
            config: 引擎配置
        """
        self.config = config or {}
        self._check_ffmpeg()
    
    def _check_ffmpeg(self) -> None:
        """检查 FFmpeg 是否可用."""
        try:
            ffmpeg.probe("-version")
        except ffmpeg.Error:
            raise RuntimeError("FFmpeg not found. Please install FFmpeg first.")
    
    def execute(
        self,
        project: Project,
        output_path: str,
        progress_callback: Optional[callable] = None,
    ) -> str:
        """执行编辑项目.
        
        Args:
            project: 编辑项目
            output_path: 输出路径
            progress_callback: 进度回调函数
            
        Returns:
            str: 输出文件路径
        """
        logger.info(f"Executing project, output: {output_path}")
        # TODO: 实现项目执行逻辑
        return output_path
    
    def probe(self, video_path: str) -> Dict[str, Any]:
        """获取视频信息.
        
        Args:
            video_path: 视频路径
            
        Returns:
            Dict: 视频元数据
        """
        try:
            return ffmpeg.probe(video_path)
        except ffmpeg.Error as e:
            logger.error(f"Failed to probe video: {e}")
            raise
