"""Task queue and concurrency control for video processing.

提供视频处理任务的队列管理、并发控制和状态跟踪功能。
"""

import asyncio
import json
import time
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set
import logging

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """任务状态枚举."""
    PENDING = "pending"          # 等待中
    RUNNING = "running"          # 运行中
    PAUSED = "paused"            # 已暂停
    COMPLETED = "completed"      # 已完成
    FAILED = "failed"            # 失败
    CANCELLED = "cancelled"      # 已取消
    RETRYING = "retrying"        # 重试中


class TaskPriority(Enum):
    """任务优先级枚举."""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


@dataclass
class VideoTask:
    """视频处理任务定义.
    
    Attributes:
        task_type: 任务类型 (edit/transcode/analyze)
        input_path: 输入视频路径
        output_path: 输出视频路径
        params: 处理参数
        priority: 任务优先级
        max_retries: 最大重试次数
    """
    task_type: str  # "edit", "transcode", "analyze", "extract"
    input_path: str
    output_path: Optional[str] = None
    params: Dict[str, Any] = field(default_factory=dict)
    priority: TaskPriority = TaskPriority.NORMAL
    max_retries: int = 2
    
    # 内部字段
    task_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: float = field(default_factory=time.time)
    status: TaskStatus = TaskStatus.PENDING
    current_retry: int = 0
    
    # 运行时信息
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    progress: float = 0.0  # 0.0 ~ 1.0
    error_message: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典."""
        data = asdict(self)
        data['status'] = self.status.value
        data['priority'] = self.priority.value
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "VideoTask":
        """从字典创建."""
        data = data.copy()
        data['status'] = TaskStatus(data['status'])
        data['priority'] = TaskPriority(data['priority'])
        return cls(**data)
    
    @property
    def duration(self) -> Optional[float]:
        """任务处理时长(秒)."""
        if self.started_at is None:
            return None
        end = self.completed_at or time.time()
        return end - self.started_at
    
    @property
    def wait_time(self) -> float:
        """等待时长(秒)."""
        if self.started_at is None:
            return time.time() - self.created_at
        return self.started_at - self.created_at


@dataclass
class QueueStats:
    """队列统计信息."""
    total_pending: int = 0
    total_running: int = 0
    total_completed: int = 0
    total_failed: int = 0
    avg_wait_time: float = 0.0
    avg_process_time: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class TaskQueue:
    """视频处理任务队列.
    
    提供并发控制、任务调度、状态跟踪功能。
    
    Example:
        >>> queue = TaskQueue(max_concurrent=2)
        >>> 
        >>> # 提交任务
        >>> task = VideoTask(
        ...     task_type="edit",
        ...     input_path="input.mp4",
        ...     output_path="output.mp4",
        ...     params={"target_duration": 60}
        ... )
        >>> task_id = await queue.submit(task)
        >>> 
        >>> # 查询状态
        >>> status = await queue.get_status(task_id)
        >>> 
        >>> # 等待完成
        >>> result = await queue.wait_for_completion(task_id)
    """
    
    def __init__(
        self,
        max_concurrent: int = 2,
        max_queue_size: int = 10,
        timeout_seconds: float = 3600,
        retry_count: int = 2,
        retry_delay_seconds: float = 30,
        persistence_path: Optional[str] = None
    ):
        """初始化任务队列.
        
        Args:
            max_concurrent: 最大并发任务数
            max_queue_size: 队列最大长度
            timeout_seconds: 任务超时时间(秒)
            retry_count: 失败重试次数
            retry_delay_seconds: 重试间隔(秒)
            persistence_path: 持久化存储路径
        """
        self.max_concurrent = max_concurrent
        self.max_queue_size = max_queue_size
        self.timeout_seconds = timeout_seconds
        self.retry_count = retry_count
        self.retry_delay_seconds = retry_delay_seconds
        
        # 任务存储
        self._tasks: Dict[str, VideoTask] = {}
        self._pending_queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self._running_tasks: Set[str] = set()
        self._completed_tasks: Dict[str, VideoTask] = {}
        
        # 并发控制
        self._semaphore: Optional[asyncio.Semaphore] = None
        self._shutdown: bool = False
        self._worker_task: Optional[asyncio.Task] = None
        
        # 回调函数
        self._on_task_start: Optional[Callable[[VideoTask], None]] = None
        self._on_task_complete: Optional[Callable[[VideoTask], None]] = None
        self._on_task_failed: Optional[Callable[[VideoTask], None]] = None
        self._on_progress: Optional[Callable[[str, float], None]] = None
        
        # 持久化
        self._persistence_path = persistence_path
        if persistence_path:
            self._load_state()
    
    async def initialize(self) -> None:
        """初始化队列，启动工作线程."""
        self._semaphore = asyncio.Semaphore(self.max_concurrent)
        self._worker_task = asyncio.create_task(self._worker_loop())
        logger.info(f"TaskQueue initialized: max_concurrent={self.max_concurrent}")
    
    async def shutdown(self, wait_for_pending: bool = True) -> None:
        """关闭队列.
        
        Args:
            wait_for_pending: 是否等待待处理任务完成
        """
        self._shutdown = True
        
        if wait_for_pending:
            # 等待所有任务完成
            while not self._pending_queue.empty() or self._running_tasks:
                await asyncio.sleep(0.5)
        else:
            # 取消所有待处理任务
            while not self._pending_queue.empty():
                try:
                    _, task_id = self._pending_queue.get_nowait()
                    task = self._tasks.get(task_id)
                    if task:
                        task.status = TaskStatus.CANCELLED
                except asyncio.QueueEmpty:
                    break
        
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
        
        self._save_state()
        logger.info("TaskQueue shutdown complete")
    
    async def submit(
        self,
        task: VideoTask,
        block: bool = True,
        timeout: Optional[float] = None
    ) -> str:
        """提交任务到队列.
        
        Args:
            task: 视频处理任务
            block: 是否阻塞等待队列空间
            timeout: 阻塞超时时间
            
        Returns:
            任务ID
            
        Raises:
            asyncio.QueueFull: 如果队列已满且 block=False
        """
        if self._shutdown:
            raise RuntimeError("TaskQueue is shutdown")
        
        # 检查队列空间
        if self._pending_queue.qsize() >= self.max_queue_size:
            if not block:
                raise asyncio.QueueFull("Task queue is full")
            
            # 等待队列空间
            start = time.time()
            while self._pending_queue.qsize() >= self.max_queue_size:
                if timeout and (time.time() - start) > timeout:
                    raise TimeoutError("Timeout waiting for queue space")
                await asyncio.sleep(0.1)
        
        # 存储任务
        self._tasks[task.id] = task
        
        # 加入优先级队列 (优先级数值越小越优先，所以用负值)
        priority = (-task.priority.value, task.created_at)
        await self._pending_queue.put((priority, task.task_id))
        
        logger.info(f"Task submitted: {task.task_id}, type={task.task_type}")
        return task.task_id
    
    async def get_status(self, task_id: str) -> Optional[VideoTask]:
        """获取任务状态和详情.
        
        Args:
            task_id: 任务ID
            
        Returns:
            任务对象，如果不存在返回None
        """
        return self._tasks.get(task_id)
    
    async def cancel_task(self, task_id: str) -> bool:
        """取消任务.
        
        Args:
            task_id: 任务ID
            
        Returns:
            是否成功取消
        """
        task = self._tasks.get(task_id)
        if not task:
            return False
        
        if task.status == TaskStatus.PENDING:
            task.status = TaskStatus.CANCELLED
            logger.info(f"Task cancelled: {task_id}")
            return True
        elif task.status == TaskStatus.RUNNING:
            # 运行中的任务无法直接取消，标记为需要取消
            task.status = TaskStatus.CANCELLED
            logger.info(f"Task marked for cancellation: {task_id}")
            return True
        
        return False
    
    async def wait_for_completion(
        self,
        task_id: str,
        timeout: Optional[float] = None,
        poll_interval: float = 0.5
    ) -> VideoTask:
        """等待任务完成.
        
        Args:
            task_id: 任务ID
            timeout: 超时时间
            poll_interval: 轮询间隔
            
        Returns:
            完成的任务对象
            
        Raises:
            TimeoutError: 如果超时
        """
        start = time.time()
        while True:
            task = await self.get_status(task_id)
            if not task:
                raise ValueError(f"Task not found: {task_id}")
            
            if task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED):
                return task
            
            if timeout and (time.time() - start) > timeout:
                raise TimeoutError(f"Timeout waiting for task {task_id}")
            
            await asyncio.sleep(poll_interval)
    
    async def get_stats(self) -> QueueStats:
        """获取队列统计信息."""
        pending = sum(1 for t in self._tasks.values() if t.status == TaskStatus.PENDING)
        running = sum(1 for t in self._tasks.values() if t.status == TaskStatus.RUNNING)
        completed = sum(1 for t in self._tasks.values() if t.status == TaskStatus.COMPLETED)
        failed = sum(1 for t in self._tasks.values() if t.status == TaskStatus.FAILED)
        
        # 计算平均等待时间和处理时间
        wait_times = [t.wait_time for t in self._tasks.values() if t.started_at is not None]
        process_times = [t.duration for t in self._tasks.values() if t.duration is not None]
        
        return QueueStats(
            total_pending=pending,
            total_running=running,
            total_completed=completed,
            total_failed=failed,
            avg_wait_time=sum(wait_times) / len(wait_times) if wait_times else 0.0,
            avg_process_time=sum(process_times) / len(process_times) if process_times else 0.0
        )
    
    def set_callbacks(
        self,
        on_task_start: Optional[Callable[[VideoTask], None]] = None,
        on_task_complete: Optional[Callable[[VideoTask], None]] = None,
        on_task_failed: Optional[Callable[[VideoTask], None]] = None,
        on_progress: Optional[Callable[[str, float], None]] = None
    ) -> None:
        """设置回调函数."""
        self._on_task_start = on_task_start
        self._on_task_complete = on_task_complete
        self._on_task_failed = on_task_failed
        self._on_progress = on_progress
    
    def update_progress(self, task_id: str, progress: float) -> None:
        """更新任务进度.
        
        Args:
            task_id: 任务ID
            progress: 进度值 (0.0 ~ 1.0)
        """
        task = self._tasks.get(task_id)
        if task:
            task.progress = max(0.0, min(1.0, progress))
            if self._on_progress:
                self._on_progress(task_id, task.progress)
    
    async def _worker_loop(self) -> None:
        """工作线程主循环."""
        while not self._shutdown:
            try:
                # 获取下一个任务
                priority, task_id = await asyncio.wait_for(
                    self._pending_queue.get(),
                    timeout=1.0
                )
                
                task = self._tasks.get(task_id)
                if not task or task.status != TaskStatus.PENDING:
                    continue
                
                # 使用信号量控制并发
                async with self._semaphore:
                    await self._execute_task(task)
                    
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Worker loop error: {e}")
    
    async def _execute_task(self, task: VideoTask) -> None:
        """执行单个任务."""
        task.status = TaskStatus.RUNNING
        task.started_at = time.time()
        self._running_tasks.add(task.task_id)
        
        if self._on_task_start:
            self._on_task_start(task)
        
        try:
            # 设置超时
            result = await asyncio.wait_for(
                self._process_task(task),
                timeout=self.timeout_seconds
            )
            
            task.status = TaskStatus.COMPLETED
            task.result = result
            task.completed_at = time.time()
            self._completed_tasks[task.task_id] = task
            
            if self._on_task_complete:
                self._on_task_complete(task)
            
            logger.info(f"Task completed: {task.task_id}, duration={task.duration:.1f}s")
            
        except asyncio.TimeoutError:
            await self._handle_task_error(task, f"Task timeout after {self.timeout_seconds}s")
        except Exception as e:
            await self._handle_task_error(task, str(e))
        finally:
            self._running_tasks.discard(task.task_id)
            self._save_state()
    
    async def _process_task(self, task: VideoTask) -> Dict[str, Any]:
        """处理具体任务逻辑.
        
        这是一个抽象方法，实际处理逻辑由外部注入。
        """
        # 默认实现：返回占位结果
        # 实际使用时，应该通过 set_task_processor 注入处理函数
        return {"status": "completed", "message": "Task processed"}
    
    async def _handle_task_error(self, task: VideoTask, error_message: str) -> None:
        """处理任务错误."""
        task.error_message = error_message
        task.current_retry += 1
        
        if task.current_retry <= task.max_retries:
            # 重试
            task.status = TaskStatus.RETRYING
            logger.warning(f"Task failed, retrying ({task.current_retry}/{task.max_retries}): {task.task_id}")
            
            await asyncio.sleep(self.retry_delay_seconds)
            
            # 重新加入队列
            priority = (-task.priority.value, time.time())
            await self._pending_queue.put((priority, task.task_id))
            task.status = TaskStatus.PENDING
        else:
            # 重试次数耗尽
            task.status = TaskStatus.FAILED
            task.completed_at = time.time()
            
            if self._on_task_failed:
                self._on_task_failed(task)
            
            logger.error(f"Task failed after {task.max_retries} retries: {task.task_id}, error={error_message}")
    
    def _save_state(self) -> None:
        """保存队列状态到磁盘."""
        if not self._persistence_path:
            return
        
        try:
            state = {
                "tasks": {tid: t.to_dict() for tid, t in self._tasks.items()},
                "timestamp": time.time()
            }
            Path(self._persistence_path).parent.mkdir(parents=True, exist_ok=True)
            with open(self._persistence_path, 'w', encoding='utf-8') as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to save queue state: {e}")
    
    def _load_state(self) -> None:
        """从磁盘加载队列状态."""
        if not self._persistence_path or not Path(self._persistence_path).exists():
            return
        
        try:
            with open(self._persistence_path, 'r', encoding='utf-8') as f:
                state = json.load(f)
            
            for tid, task_data in state.get("tasks", {}).items():
                task = VideoTask.from_dict(task_data)
                self._tasks[tid] = task
                
                # 恢复待处理任务到队列
                if task.status == TaskStatus.PENDING:
                    priority = (-task.priority.value, task.created_at)
                    # 注意：这里不能直接put，需要在initialize后
                    
            logger.info(f"Loaded {len(self._tasks)} tasks from persistence")
        except Exception as e:
            logger.error(f"Failed to load queue state: {e}")


class VideoProcessor:
    """视频处理器 - 集成 TaskQueue 和实际处理逻辑.
    
    这是一个高层封装，将 AutoEditor/InteractiveEditor 与 TaskQueue 集成。
    """
    
    def __init__(
        self,
        queue: Optional[TaskQueue] = None,
        auto_editor=None,
        interactive_editor=None
    ):
        """初始化视频处理器.
        
        Args:
            queue: 任务队列实例，如果不提供则创建默认队列
            auto_editor: AutoEditor 实例
            interactive_editor: InteractiveEditor 实例
        """
        self.queue = queue or TaskQueue()
        self.auto_editor = auto_editor
        self.interactive_editor = interactive_editor
        self._processor_registered = False
    
    async def initialize(self) -> None:
        """初始化处理器."""
        await self.queue.initialize()
        
        # 注册任务处理函数
        if not self._processor_registered:
            self.queue._process_task = self._process_task_wrapper
            self._processor_registered = True
    
    async def shutdown(self, wait_for_pending: bool = True) -> None:
        """关闭处理器."""
        await self.queue.shutdown(wait_for_pending)
    
    async def submit_edit_task(
        self,
        input_path: str,
        output_path: str,
        edit_config: Any,
        priority: TaskPriority = TaskPriority.NORMAL
    ) -> str:
        """提交编辑任务.
        
        Args:
            input_path: 输入视频路径
            output_path: 输出视频路径
            edit_config: 编辑配置 (EditConfig 对象)
            priority: 任务优先级
            
        Returns:
            任务ID
        """
        task = VideoTask(
            task_type="edit",
            input_path=input_path,
            output_path=output_path,
            params={"edit_config": edit_config},
            priority=priority
        )
        return await self.queue.submit(task)
    
    async def submit_transcode_task(
        self,
        input_path: str,
        output_path: str,
        codec: str = "h264",
        quality: str = "high",
        priority: TaskPriority = TaskPriority.NORMAL
    ) -> str:
        """提交转码任务."""
        task = VideoTask(
            task_type="transcode",
            input_path=input_path,
            output_path=output_path,
            params={"codec": codec, "quality": quality},
            priority=priority
        )
        return await self.queue.submit(task)
    
    async def _process_task_wrapper(self, task: VideoTask) -> Dict[str, Any]:
        """任务处理包装器."""
        if task.task_type == "edit" and self.auto_editor:
            return await self._process_edit_task(task)
        elif task.task_type == "transcode":
            return await self._process_transcode_task(task)
        else:
            raise ValueError(f"Unknown task type: {task.task_type}")
    
    async def _process_edit_task(self, task: VideoTask) -> Dict[str, Any]:
        """处理编辑任务."""
        from video_cut_skill import EditConfig
        
        config = task.params.get("edit_config")
        if not config:
            raise ValueError("Missing edit_config in task params")
        
        # 更新进度回调
        def progress_callback(progress: float):
            self.queue.update_progress(task.task_id, progress)
        
        # 执行编辑
        result = self.auto_editor.process_video(
            task.input_path,
            config,
            progress_callback=progress_callback
        )
        
        return {
            "output_path": result.output_path if hasattr(result, 'output_path') else str(result),
            "processing_time": result.processing_time if hasattr(result, 'processing_time') else 0
        }
    
    async def _process_transcode_task(self, task: VideoTask) -> Dict[str, Any]:
        """处理转码任务."""
        from video_cut_skill import FFmpegWrapper
        
        wrapper = FFmpegWrapper()
        output_path = task.output_path or task.input_path.replace(".mp4", "_transcoded.mp4")
        
        # 执行转码
        wrapper.run_command([
            "-i", task.input_path,
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "23",
            output_path
        ])
        
        return {"output_path": output_path}
