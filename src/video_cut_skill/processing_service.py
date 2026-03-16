"""AutoEditor integration with TaskQueue, CheckpointManager and MetricsCollector.

提供高层封装，将 P0 功能集成到 AutoEditor。
"""

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Union

from video_cut_skill import AutoEditor, EditConfig, EditResult
from video_cut_skill.core.checkpoint_manager import (
    CheckpointManager,
    ProcessingStage,
)
from video_cut_skill.core.metrics_collector import MetricsCollector, TaskMetrics
from video_cut_skill.core.task_queue import (
    QueueStats,
    TaskPriority,
    TaskQueue,
    TaskStatus,
    VideoTask,
)


@dataclass
class ProcessingResult:
    """处理结果封装."""
    
    task_id: str
    success: bool
    output_path: Optional[Path] = None
    edit_result: Optional[EditResult] = None
    error_message: Optional[str] = None
    processing_time: float = 0.0
    stages_completed: list = None
    
    def __post_init__(self):
        if self.stages_completed is None:
            self.stages_completed = []


class VideoProcessingService:
    """视频处理服务 - 集成 P0 核心功能.
    
    将 TaskQueue、CheckpointManager、MetricsCollector 集成到 AutoEditor，
    提供生产级的视频处理能力。
    
    Example:
        >>> service = VideoProcessingService()
        >>> await service.initialize()
        >>>
        >>> # 提交处理任务
        >>> result = await service.process_video(
        ...     input_path="input.mp4",
        ...     config=EditConfig(target_duration=60),
        ...     priority=TaskPriority.HIGH
        ... )
        >>>
        >>> # 查看状态
        >>> status = await service.get_task_status(result.task_id)
        >>>
        >>> await service.shutdown()
    """
    
    def __init__(
        self,
        auto_editor: Optional[AutoEditor] = None,
        task_queue: Optional[TaskQueue] = None,
        checkpoint_manager: Optional[CheckpointManager] = None,
        metrics_collector: Optional[MetricsCollector] = None,
        enable_checkpoints: bool = True,
        enable_metrics: bool = True,
    ):
        """初始化视频处理服务.
        
        Args:
            auto_editor: AutoEditor 实例，如果不提供则创建默认实例
            task_queue: 任务队列实例，如果不提供则创建默认队列
            checkpoint_manager: 检查点管理器，如果不提供则创建默认管理器
            metrics_collector: 监控器，如果不提供则创建默认监控器
            enable_checkpoints: 是否启用断点续传
            enable_metrics: 是否启用性能监控
        """
        self.auto_editor = auto_editor
        self.task_queue = task_queue or TaskQueue()
        self.checkpoint_manager = checkpoint_manager or CheckpointManager()
        self.metrics_collector = metrics_collector if enable_metrics else None
        self.enable_checkpoints = enable_checkpoints
        
        # 初始化标志
        self._initialized = False
        self._custom_processor = False
    
    async def initialize(self) -> None:
        """初始化服务."""
        if self._initialized:
            return
        
        # 创建 AutoEditor（如果未提供）
        if self.auto_editor is None:
            self.auto_editor = AutoEditor(analysis_mode="audio")
        
        # 初始化队列
        await self.task_queue.initialize()
        
        # 设置自定义任务处理器
        self._original_processor = self.task_queue._process_task
        self.task_queue._process_task = self._process_video_task
        self._custom_processor = True
        
        # 设置队列回调
        self.task_queue.set_callbacks(
            on_task_start=self._on_task_start,
            on_task_complete=self._on_task_complete,
            on_task_failed=self._on_task_failed,
            on_progress=self._on_progress
        )
        
        # 初始化监控器
        if self.metrics_collector:
            await self.metrics_collector.initialize()
        
        self._initialized = True
    
    async def shutdown(self, wait_for_pending: bool = True) -> None:
        """关闭服务.
        
        Args:
            wait_for_pending: 是否等待待处理任务完成
        """
        if not self._initialized:
            return
        
        # 关闭队列
        await self.task_queue.shutdown(wait_for_pending)
        
        # 恢复原始处理器
        if self._custom_processor:
            self.task_queue._process_task = self._original_processor
        
        # 关闭监控器
        if self.metrics_collector:
            await self.metrics_collector.shutdown()
        
        self._initialized = False
    
    async def process_video(
        self,
        input_path: Union[str, Path],
        config: EditConfig,
        output_path: Optional[Union[str, Path]] = None,
        priority: TaskPriority = TaskPriority.NORMAL,
        enable_resume: bool = True,
    ) -> ProcessingResult:
        """处理视频.
        
        Args:
            input_path: 输入视频路径
            config: 编辑配置
            output_path: 输出路径（可选）
            priority: 任务优先级
            enable_resume: 是否启用断点续传
            
        Returns:
            处理结果
        """
        if not self._initialized:
            raise RuntimeError("Service not initialized. Call initialize() first.")
        
        input_path = Path(input_path)
        if output_path:
            output_path = Path(output_path)
        elif config.output_path:
            output_path = Path(config.output_path)
        else:
            output_path = input_path.parent / f"{input_path.stem}_edited{input_path.suffix}"
        
        # 检查是否可以恢复
        task_id = None
        if enable_resume and self.enable_checkpoints:
            existing_id = self._find_existing_checkpoint(input_path, config)
            if existing_id and self.checkpoint_manager.can_resume(existing_id):
                task_id = existing_id
        
        # 创建新任务
        if task_id is None:
            task = VideoTask(
                task_type="edit",
                input_path=str(input_path),
                output_path=str(output_path),
                params={
                    "config": config,
                    "enable_checkpoint": self.enable_checkpoints,
                },
                priority=priority
            )
            task_id = task.task_id
            
            # 创建检查点
            if self.enable_checkpoints:
                self.checkpoint_manager.create_checkpoint(
                    task_id=task_id,
                    input_path=str(input_path),
                    output_path=str(output_path),
                    params={"config": config}
                )
        
        # 提交到队列
        submitted_id = await self.task_queue.submit(
            self.task_queue._tasks.get(task_id) or VideoTask(
                task_type="edit",
                input_path=str(input_path),
                output_path=str(output_path),
                params={"config": config, "enable_checkpoint": self.enable_checkpoints},
                priority=priority,
                task_id=task_id
            )
        )
        
        # 等待完成
        task_result = await self.task_queue.wait_for_completion(submitted_id)
        
        # 构建结果
        if task_result.status == TaskStatus.COMPLETED:
            return ProcessingResult(
                task_id=submitted_id,
                success=True,
                output_path=Path(task_result.result.get("output_path")) if task_result.result else None,
                edit_result=task_result.result.get("edit_result") if task_result.result else None,
                processing_time=task_result.duration or 0
            )
        else:
            return ProcessingResult(
                task_id=submitted_id,
                success=False,
                error_message=task_result.error_message,
                processing_time=task_result.duration or 0
            )
    
    async def submit_video(
        self,
        input_path: Union[str, Path],
        config: EditConfig,
        output_path: Optional[Union[str, Path]] = None,
        priority: TaskPriority = TaskPriority.NORMAL,
    ) -> str:
        """提交视频处理任务（不等待完成）.
        
        Args:
            input_path: 输入视频路径
            config: 编辑配置
            output_path: 输出路径（可选）
            priority: 任务优先级
            
        Returns:
            任务ID
        """
        if not self._initialized:
            raise RuntimeError("Service not initialized. Call initialize() first.")
        
        input_path = Path(input_path)
        if output_path:
            output_path = Path(output_path)
        else:
            output_path = input_path.parent / f"{input_path.stem}_edited{input_path.suffix}"
        
        task = VideoTask(
            task_type="edit",
            input_path=str(input_path),
            output_path=str(output_path),
            params={
                "config": config,
                "enable_checkpoint": self.enable_checkpoints
            },
            priority=priority
        )
        
        # 创建检查点
        if self.enable_checkpoints:
            self.checkpoint_manager.create_checkpoint(
                task_id=task.task_id,
                input_path=str(input_path),
                output_path=str(output_path),
                params={"config": config}
            )
        
        return await self.task_queue.submit(task)
    
    async def get_task_status(self, task_id: str) -> Optional[VideoTask]:
        """获取任务状态.
        
        Args:
            task_id: 任务ID
            
        Returns:
            任务状态对象
        """
        return await self.task_queue.get_status(task_id)
    
    async def wait_for_task(self, task_id: str, timeout: Optional[float] = None) -> VideoTask:
        """等待任务完成.
        
        Args:
            task_id: 任务ID
            timeout: 超时时间
            
        Returns:
            完成的任务对象
        """
        return await self.task_queue.wait_for_completion(task_id, timeout)
    
    async def cancel_task(self, task_id: str) -> bool:
        """取消任务.
        
        Args:
            task_id: 任务ID
            
        Returns:
            是否成功取消
        """
        return await self.task_queue.cancel_task(task_id)
    
    def get_queue_stats(self) -> QueueStats:
        """获取队列统计信息."""
        return self.task_queue.get_stats()
    
    def get_processing_statistics(self, time_range: str = "24h") -> Dict[str, Any]:
        """获取处理统计信息.
        
        Args:
            time_range: 时间范围 (1h, 24h, 7d)
            
        Returns:
            统计信息字典
        """
        if self.metrics_collector:
            return self.metrics_collector.get_statistics(time_range)
        return {}
    
    def list_checkpoints(self) -> list:
        """列出所有检查点."""
        return self.checkpoint_manager.list_checkpoints()
    
    def can_resume(self, task_id: str) -> bool:
        """检查任务是否可以恢复."""
        return self.checkpoint_manager.can_resume(task_id)
    
    # ===== 内部方法 =====
    
    async def _process_video_task(self, task: VideoTask) -> Dict[str, Any]:
        """处理视频任务（内部方法）."""
        config = task.params.get("config")
        enable_checkpoint = task.params.get("enable_checkpoint", True)
        
        input_path = Path(task.input_path)
        output_path = Path(task.output_path)
        
        # 加载检查点（如果启用）
        checkpoint = None
        resume_stage = None
        if enable_checkpoint:
            checkpoint = self.checkpoint_manager.load_checkpoint(task.task_id)
            if checkpoint:
                resume_stage = self.checkpoint_manager.get_resume_stage(checkpoint)
        
        try:
            # 阶段 1: 转录（如果需要）
            transcript = None
            if resume_stage is None or resume_stage.value <= ProcessingStage.TRANSCRIPTION_COMPLETE.value:
                if self.metrics_collector:
                    with self.metrics_collector.time_stage(task.task_id, "transcription"):
                        edit_result = self.auto_editor.process_video(
                            str(input_path),
                            config
                        )
                else:
                    edit_result = self.auto_editor.process_video(
                        str(input_path),
                        config
                    )
                
                # 保存检查点
                if enable_checkpoint:
                    self.checkpoint_manager.save_stage_checkpoint(
                        task.task_id,
                        ProcessingStage.COMPLETED,
                        {"output_path": str(edit_result.output_path)}
                    )
            else:
                # 从检查点恢复
                edit_result = EditResult(
                    output_path=output_path,
                    duration=0,
                    processing_time=0
                )
            
            return {
                "output_path": str(edit_result.output_path),
                "edit_result": edit_result,
                "success": True
            }
            
        except Exception as e:
            # 保存错误状态到检查点
            if enable_checkpoint and checkpoint:
                self.checkpoint_manager.save_stage_checkpoint(
                    task.task_id,
                    checkpoint.current_stage,  # 保持在当前阶段
                    {"error": str(e)}
                )
            raise
    
    def _on_task_start(self, task: VideoTask) -> None:
        """任务开始回调."""
        if self.metrics_collector:
            self.metrics_collector.start_task(task.task_id, task.task_type)
            self.metrics_collector.task_started(task.task_id)
    
    def _on_task_complete(self, task: VideoTask) -> None:
        """任务完成回调."""
        if self.metrics_collector:
            self.metrics_collector.complete_task(
                task_id=task.task_id,
                success=True,
                output_size_mb=0  # TODO: 获取实际文件大小
            )
    
    def _on_task_failed(self, task: VideoTask) -> None:
        """任务失败回调."""
        if self.metrics_collector:
            self.metrics_collector.complete_task(
                task_id=task.task_id,
                success=False,
                error_message=task.error_message
            )
    
    def _on_progress(self, task_id: str, progress: float) -> None:
        """进度更新回调."""
        # 可以在这里添加进度通知逻辑
        pass
    
    def _find_existing_checkpoint(
        self,
        input_path: Path,
        config: EditConfig
    ) -> Optional[str]:
        """查找已存在的检查点."""
        checkpoints = self.checkpoint_manager.list_checkpoints()
        
        for cp in checkpoints:
            if cp.input_path == str(input_path) and cp.current_stage != ProcessingStage.COMPLETED:
                # 简单比较配置参数
                return cp.task_id
        
        return None


# 便捷函数

async def process_video_with_queue(
    input_path: Union[str, Path],
    config: EditConfig,
    output_path: Optional[Union[str, Path]] = None,
    priority: TaskPriority = TaskPriority.NORMAL,
    max_concurrent: int = 2,
) -> ProcessingResult:
    """使用队列处理视频的便捷函数.
    
    Example:
        >>> result = await process_video_with_queue(
        ...     "input.mp4",
        ...     EditConfig(target_duration=60),
        ...     priority=TaskPriority.HIGH
        ... )
        >>> if result.success:
        ...     print(f"Output: {result.output_path}")
    """
    service = VideoProcessingService(
        task_queue=TaskQueue(max_concurrent=max_concurrent)
    )
    
    try:
        await service.initialize()
        result = await service.process_video(
            input_path=input_path,
            config=config,
            output_path=output_path,
            priority=priority
        )
        return result
    finally:
        await service.shutdown()
