"""Checkpoint manager for resumable video processing.

提供断点续传功能，允许长视频处理任务在中断后从检查点恢复。
"""

import json
import hashlib
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable
import logging

logger = logging.getLogger(__name__)


class ProcessingStage(Enum):
    """视频处理阶段枚举."""
    INITIALIZED = "initialized"           # 已初始化
    TRANSCRIPTION_STARTED = "transcription_started"  # 转录开始
    TRANSCRIPTION_COMPLETE = "transcription_complete"  # 转录完成
    ANALYSIS_COMPLETE = "analysis_complete"  # 分析完成
    STRATEGY_GENERATED = "strategy_generated"  # 策略生成完成
    CLIPS_EXTRACTED = "clips_extracted"   # 片段提取完成
    RENDERING = "rendering"               # 渲染中
    RENDERING_COMPLETE = "rendering_complete"  # 渲染完成
    POST_PROCESSING = "post_processing"   # 后处理
    COMPLETED = "completed"               # 全部完成


@dataclass
class StageCheckpoint:
    """单个阶段的检查点数据.
    
    Attributes:
        stage: 处理阶段
        timestamp: 检查点时间戳
        data: 阶段数据 (如转录结果、分析结果等)
        metadata: 额外元数据
    """
    stage: ProcessingStage
    timestamp: float = field(default_factory=time.time)
    data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典."""
        return {
            "stage": self.stage.value,
            "timestamp": self.timestamp,
            "data": self.data,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StageCheckpoint":
        """从字典创建."""
        return cls(
            stage=ProcessingStage(data["stage"]),
            timestamp=data.get("timestamp", time.time()),
            data=data.get("data", {}),
            metadata=data.get("metadata", {})
        )


@dataclass
class VideoCheckpoint:
    """视频处理检查点.
    
    记录视频处理的完整状态和各个阶段的中间结果。
    """
    task_id: str
    input_path: str
    output_path: Optional[str] = None
    
    # 输入文件指纹 (用于验证文件是否变化)
    input_hash: Optional[str] = None
    input_size: int = 0
    input_mtime: float = 0.0
    
    # 处理参数
    params: Dict[str, Any] = field(default_factory=dict)
    
    # 检查点历史
    checkpoints: List[StageCheckpoint] = field(default_factory=list)
    
    # 当前状态
    current_stage: ProcessingStage = ProcessingStage.INITIALIZED
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    
    # 渲染进度 (帧级别)
    total_frames: int = 0
    rendered_frames: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典."""
        return {
            "task_id": self.task_id,
            "input_path": self.input_path,
            "output_path": self.output_path,
            "input_hash": self.input_hash,
            "input_size": self.input_size,
            "input_mtime": self.input_mtime,
            "params": self.params,
            "checkpoints": [cp.to_dict() for cp in self.checkpoints],
            "current_stage": self.current_stage.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "total_frames": self.total_frames,
            "rendered_frames": self.rendered_frames
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "VideoCheckpoint":
        """从字典创建."""
        return cls(
            task_id=data["task_id"],
            input_path=data["input_path"],
            output_path=data.get("output_path"),
            input_hash=data.get("input_hash"),
            input_size=data.get("input_size", 0),
            input_mtime=data.get("input_mtime", 0.0),
            params=data.get("params", {}),
            checkpoints=[StageCheckpoint.from_dict(cp) for cp in data.get("checkpoints", [])],
            current_stage=ProcessingStage(data.get("current_stage", "initialized")),
            created_at=data.get("created_at", time.time()),
            updated_at=data.get("updated_at", time.time()),
            total_frames=data.get("total_frames", 0),
            rendered_frames=data.get("rendered_frames", 0)
        )
    
    @property
    def progress(self) -> float:
        """整体进度 (0.0 ~ 1.0)."""
        if self.total_frames > 0:
            return self.rendered_frames / self.total_frames
        
        # 基于阶段估算
        stage_order = [
            ProcessingStage.INITIALIZED,
            ProcessingStage.TRANSCRIPTION_STARTED,
            ProcessingStage.TRANSCRIPTION_COMPLETE,
            ProcessingStage.ANALYSIS_COMPLETE,
            ProcessingStage.STRATEGY_GENERATED,
            ProcessingStage.CLIPS_EXTRACTED,
            ProcessingStage.RENDERING,
            ProcessingStage.RENDERING_COMPLETE,
            ProcessingStage.POST_PROCESSING,
            ProcessingStage.COMPLETED
        ]
        
        try:
            current_idx = stage_order.index(self.current_stage)
            return current_idx / len(stage_order)
        except ValueError:
            return 0.0
    
    def get_stage_checkpoint(self, stage: ProcessingStage) -> Optional[StageCheckpoint]:
        """获取指定阶段的检查点."""
        for cp in reversed(self.checkpoints):
            if cp.stage == stage:
                return cp
        return None
    
    def get_last_checkpoint(self) -> Optional[StageCheckpoint]:
        """获取最后一个检查点."""
        return self.checkpoints[-1] if self.checkpoints else None


class CheckpointManager:
    """检查点管理器.
    
    管理视频处理任务的检查点，支持断点续传。
    
    Example:
        >>> manager = CheckpointManager()
        >>> 
        >>> # 创建检查点
        >>> checkpoint = manager.create_checkpoint(
        ...     task_id="task_001",
        ...     input_path="input.mp4",
        ...     output_path="output.mp4"
        ... )
        >>> 
        >>> # 记录转录完成
        >>> manager.save_stage_checkpoint(
        ...     task_id="task_001",
        ...     stage=ProcessingStage.TRANSCRIPTION_COMPLETE,
        ...     data={"transcript": transcript_data}
        ... )
        >>> 
        >>> # 中断后恢复
        >>> checkpoint = manager.load_checkpoint("task_001")
        >>> resume_stage = manager.get_resume_stage(checkpoint)
        ...  # 从 resume_stage 继续处理
    """
    
    def __init__(
        self,
        checkpoint_dir: str = "~/.video_cut_skill/checkpoints",
        auto_save: bool = True,
        max_checkpoints_per_task: int = 10
    ):
        """初始化检查点管理器.
        
        Args:
            checkpoint_dir: 检查点存储目录
            auto_save: 是否自动保存
            max_checkpoints_per_task: 每个任务保留的最大检查点数量
        """
        self.checkpoint_dir = Path(checkpoint_dir).expanduser()
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self.auto_save = auto_save
        self.max_checkpoints_per_task = max_checkpoints_per_task
        
        # 内存缓存
        self._cache: Dict[str, VideoCheckpoint] = {}
    
    def create_checkpoint(
        self,
        task_id: str,
        input_path: str,
        output_path: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> VideoCheckpoint:
        """创建新的检查点.
        
        Args:
            task_id: 任务ID
            input_path: 输入视频路径
            output_path: 输出视频路径
            params: 处理参数
            
        Returns:
            新创建的检查点
        """
        input_path_obj = Path(input_path)
        
        # 计算输入文件指纹
        input_hash = self._compute_file_hash(input_path) if input_path_obj.exists() else None
        input_stat = input_path_obj.stat() if input_path_obj.exists() else None
        
        checkpoint = VideoCheckpoint(
            task_id=task_id,
            input_path=input_path,
            output_path=output_path,
            input_hash=input_hash,
            input_size=input_stat.st_size if input_stat else 0,
            input_mtime=input_stat.st_mtime if input_stat else 0.0,
            params=params or {}
        )
        
        # 保存初始检查点
        self._save_checkpoint(checkpoint)
        self._cache[task_id] = checkpoint
        
        logger.info(f"Checkpoint created: {task_id}")
        return checkpoint
    
    def load_checkpoint(self, task_id: str) -> Optional[VideoCheckpoint]:
        """加载检查点.
        
        Args:
            task_id: 任务ID
            
        Returns:
            检查点对象，如果不存在返回None
        """
        # 先检查缓存
        if task_id in self._cache:
            return self._cache[task_id]
        
        # 从磁盘加载
        checkpoint_path = self._get_checkpoint_path(task_id)
        if not checkpoint_path.exists():
            return None
        
        try:
            with open(checkpoint_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            checkpoint = VideoCheckpoint.from_dict(data)
            
            # 验证输入文件是否变化
            if not self._validate_checkpoint(checkpoint):
                logger.warning(f"Checkpoint validation failed for {task_id}: input file changed")
                return None
            
            self._cache[task_id] = checkpoint
            logger.info(f"Checkpoint loaded: {task_id}, stage={checkpoint.current_stage.value}")
            return checkpoint
            
        except Exception as e:
            logger.error(f"Failed to load checkpoint {task_id}: {e}")
            return None
    
    def save_stage_checkpoint(
        self,
        task_id: str,
        stage: ProcessingStage,
        data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """保存阶段检查点.
        
        Args:
            task_id: 任务ID
            stage: 处理阶段
            data: 阶段数据
            metadata: 额外元数据
        """
        checkpoint = self.load_checkpoint(task_id)
        if not checkpoint:
            raise ValueError(f"Checkpoint not found: {task_id}")
        
        # 创建阶段检查点
        stage_cp = StageCheckpoint(
            stage=stage,
            data=data,
            metadata=metadata or {}
        )
        
        # 更新检查点
        checkpoint.checkpoints.append(stage_cp)
        checkpoint.current_stage = stage
        checkpoint.updated_at = time.time()
        
        # 限制检查点数量
        if len(checkpoint.checkpoints) > self.max_checkpoints_per_task:
            checkpoint.checkpoints = checkpoint.checkpoints[-self.max_checkpoints_per_task:]
        
        # 保存
        self._save_checkpoint(checkpoint)
        self._cache[task_id] = checkpoint
        
        logger.debug(f"Stage checkpoint saved: {task_id}, stage={stage.value}")
    
    def update_rendering_progress(
        self,
        task_id: str,
        rendered_frames: int,
        total_frames: int
    ) -> None:
        """更新渲染进度.
        
        Args:
            task_id: 任务ID
            rendered_frames: 已渲染帧数
            total_frames: 总帧数
        """
        checkpoint = self.load_checkpoint(task_id)
        if not checkpoint:
            return
        
        checkpoint.rendered_frames = rendered_frames
        checkpoint.total_frames = total_frames
        checkpoint.current_stage = ProcessingStage.RENDERING
        checkpoint.updated_at = time.time()
        
        # 每100帧保存一次检查点
        if rendered_frames % 100 == 0:
            self._save_checkpoint(checkpoint)
            self._cache[task_id] = checkpoint
    
    def get_resume_stage(self, checkpoint: VideoCheckpoint) -> ProcessingStage:
        """获取恢复处理的起始阶段.
        
        根据检查点状态决定从哪个阶段开始恢复。
        
        Args:
            checkpoint: 检查点对象
            
        Returns:
            恢复阶段
        """
        stage_order = [
            ProcessingStage.INITIALIZED,
            ProcessingStage.TRANSCRIPTION_STARTED,
            ProcessingStage.TRANSCRIPTION_COMPLETE,
            ProcessingStage.ANALYSIS_COMPLETE,
            ProcessingStage.STRATEGY_GENERATED,
            ProcessingStage.CLIPS_EXTRACTED,
            ProcessingStage.RENDERING,
            ProcessingStage.RENDERING_COMPLETE,
            ProcessingStage.POST_PROCESSING,
            ProcessingStage.COMPLETED
        ]
        
        current_idx = stage_order.index(checkpoint.current_stage)
        
        # 如果当前是渲染中，需要从渲染阶段恢复
        if checkpoint.current_stage == ProcessingStage.RENDERING:
            return ProcessingStage.RENDERING
        
        # 如果已完成，无需恢复
        if checkpoint.current_stage == ProcessingStage.COMPLETED:
            return ProcessingStage.COMPLETED
        
        # 否则从下一个阶段开始
        if current_idx < len(stage_order) - 1:
            return stage_order[current_idx + 1]
        
        return checkpoint.current_stage
    
    def can_resume(self, task_id: str) -> bool:
        """检查任务是否可以恢复.
        
        Args:
            task_id: 任务ID
            
        Returns:
            是否可以恢复
        """
        checkpoint = self.load_checkpoint(task_id)
        if not checkpoint:
            return False
        
        if checkpoint.current_stage == ProcessingStage.COMPLETED:
            return False
        
        return self._validate_checkpoint(checkpoint)
    
    def list_checkpoints(
        self,
        status: Optional[ProcessingStage] = None
    ) -> List[VideoCheckpoint]:
        """列出所有检查点.
        
        Args:
            status: 按状态过滤
            
        Returns:
            检查点列表
        """
        checkpoints = []
        
        for checkpoint_file in self.checkpoint_dir.glob("*.json"):
            try:
                with open(checkpoint_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                checkpoint = VideoCheckpoint.from_dict(data)
                
                if status is None or checkpoint.current_stage == status:
                    checkpoints.append(checkpoint)
            except Exception as e:
                logger.error(f"Failed to load checkpoint file {checkpoint_file}: {e}")
        
        return sorted(checkpoints, key=lambda x: x.updated_at, reverse=True)
    
    def delete_checkpoint(self, task_id: str) -> bool:
        """删除检查点.
        
        Args:
            task_id: 任务ID
            
        Returns:
            是否成功删除
        """
        checkpoint_path = self._get_checkpoint_path(task_id)
        
        if checkpoint_path.exists():
            checkpoint_path.unlink()
            logger.info(f"Checkpoint deleted: {task_id}")
        
        if task_id in self._cache:
            del self._cache[task_id]
        
        return True
    
    def cleanup_old_checkpoints(self, max_age_days: int = 7) -> int:
        """清理旧检查点.
        
        Args:
            max_age_days: 最大保留天数
            
        Returns:
            清理的检查点数量
        """
        cutoff = time.time() - (max_age_days * 24 * 3600)
        deleted = 0
        
        for checkpoint_file in self.checkpoint_dir.glob("*.json"):
            try:
                with open(checkpoint_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                if data.get("updated_at", 0) < cutoff:
                    checkpoint_file.unlink()
                    deleted += 1
            except Exception as e:
                logger.error(f"Failed to cleanup checkpoint {checkpoint_file}: {e}")
        
        logger.info(f"Cleaned up {deleted} old checkpoints")
        return deleted
    
    def _get_checkpoint_path(self, task_id: str) -> Path:
        """获取检查点文件路径."""
        return self.checkpoint_dir / f"{task_id}.json"
    
    def _save_checkpoint(self, checkpoint: VideoCheckpoint) -> None:
        """保存检查点到磁盘."""
        checkpoint_path = self._get_checkpoint_path(checkpoint.task_id)
        
        try:
            with open(checkpoint_path, 'w', encoding='utf-8') as f:
                json.dump(checkpoint.to_dict(), f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to save checkpoint {checkpoint.task_id}: {e}")
    
    def _compute_file_hash(self, file_path: str, chunk_size: int = 8192) -> str:
        """计算文件哈希."""
        hasher = hashlib.md5()
        
        with open(file_path, 'rb') as f:
            while chunk := f.read(chunk_size):
                hasher.update(chunk)
        
        return hasher.hexdigest()
    
    def _validate_checkpoint(self, checkpoint: VideoCheckpoint) -> bool:
        """验证检查点有效性.
        
        检查输入文件是否变化。
        """
        input_path = Path(checkpoint.input_path)
        
        if not input_path.exists():
            logger.warning(f"Input file not found: {checkpoint.input_path}")
            return False
        
        stat = input_path.stat()
        
        # 检查文件大小和修改时间
        if stat.st_size != checkpoint.input_size:
            logger.warning(f"Input file size changed: {checkpoint.input_path}")
            return False
        
        if stat.st_mtime != checkpoint.input_mtime:
            # 文件被修改过，检查哈希
            current_hash = self._compute_file_hash(checkpoint.input_path)
            if current_hash != checkpoint.input_hash:
                logger.warning(f"Input file content changed: {checkpoint.input_path}")
                return False
        
        return True


class ResumableProcessor:
    """可恢复的视频处理器.
    
    集成 CheckpointManager 到视频处理流程中。
    """
    
    def __init__(
        self,
        checkpoint_manager: Optional[CheckpointManager] = None,
        auto_editor=None
    ):
        """初始化可恢复处理器.
        
        Args:
            checkpoint_manager: 检查点管理器
            auto_editor: AutoEditor 实例
        """
        self.checkpoint_manager = checkpoint_manager or CheckpointManager()
        self.auto_editor = auto_editor
    
    async def process_video(
        self,
        task_id: str,
        input_path: str,
        output_path: str,
        edit_config: Any,
        resume: bool = True
    ) -> Dict[str, Any]:
        """处理视频，支持断点续传.
        
        Args:
            task_id: 任务ID
            input_path: 输入路径
            output_path: 输出路径
            edit_config: 编辑配置
            resume: 是否尝试恢复
            
        Returns:
            处理结果
        """
        # 尝试加载已有检查点
        checkpoint = None
        if resume:
            checkpoint = self.checkpoint_manager.load_checkpoint(task_id)
        
        # 如果没有检查点或验证失败，创建新检查点
        if not checkpoint:
            checkpoint = self.checkpoint_manager.create_checkpoint(
                task_id=task_id,
                input_path=input_path,
                output_path=output_path,
                params={"edit_config": edit_config}
            )
        
        # 确定恢复阶段
        resume_stage = self.checkpoint_manager.get_resume_stage(checkpoint)
        logger.info(f"Processing {task_id} from stage: {resume_stage.value}")
        
        try:
            # 阶段 1: 转录 (如果需要)
            if resume_stage.value <= ProcessingStage.TRANSCRIPTION_COMPLETE.value:
                transcript = await self._do_transcription(checkpoint)
                self.checkpoint_manager.save_stage_checkpoint(
                    task_id,
                    ProcessingStage.TRANSCRIPTION_COMPLETE,
                    {"transcript": transcript}
                )
            else:
                # 从检查点加载转录结果
                cp_data = checkpoint.get_stage_checkpoint(ProcessingStage.TRANSCRIPTION_COMPLETE)
                transcript = cp_data.data.get("transcript") if cp_data else None
            
            # 阶段 2: 分析 (如果需要)
            if resume_stage.value <= ProcessingStage.ANALYSIS_COMPLETE.value:
                analysis = await self._do_analysis(checkpoint, transcript)
                self.checkpoint_manager.save_stage_checkpoint(
                    task_id,
                    ProcessingStage.ANALYSIS_COMPLETE,
                    {"analysis": analysis}
                )
            
            # 阶段 3: 渲染 (如果需要)
            if resume_stage.value <= ProcessingStage.RENDERING.value:
                result = await self._do_rendering(checkpoint, edit_config)
                self.checkpoint_manager.save_stage_checkpoint(
                    task_id,
                    ProcessingStage.COMPLETED,
                    {"output_path": result}
                )
            
            return {
                "success": True,
                "output_path": checkpoint.output_path,
                "stage": ProcessingStage.COMPLETED.value
            }
            
        except Exception as e:
            logger.error(f"Processing failed for {task_id}: {e}")
            raise
    
    async def _do_transcription(self, checkpoint: VideoCheckpoint) -> Any:
        """执行转录."""
        # 实际实现中调用 transcriber
        pass
    
    async def _do_analysis(self, checkpoint: VideoCheckpoint, transcript: Any) -> Any:
        """执行分析."""
        # 实际实现中调用 analyzer
        pass
    
    async def _do_rendering(self, checkpoint: VideoCheckpoint, edit_config: Any) -> str:
        """执行渲染."""
        # 实际实现中调用 ffmpeg
        pass
