"""Core module for video editing engine."""

from video_cut_skill.core.cache import MultiLevelCache
from video_cut_skill.core.checkpoint_manager import (
    CheckpointManager,
    ProcessingStage,
    VideoCheckpoint,
)
from video_cut_skill.core.cost_guardian import CostCheckResult, CostGuardian
from video_cut_skill.core.ffmpeg_wrapper import FFmpegError, FFmpegWrapper
from video_cut_skill.core.file_upload import (
    AliyunFileUploader,
    FileUploadError,
    upload_file_for_transcription,
)
from video_cut_skill.core.interactive_editor import InteractiveEditor
from video_cut_skill.core.metrics_collector import (
    Alert,
    AlertSeverity,
    MetricsCollector,
    TaskMetrics,
)
from video_cut_skill.core.models import Clip, Effect, Project, Timeline, Track
from video_cut_skill.core.session_manager import SessionManager
from video_cut_skill.core.task_queue import (
    QueueStats,
    TaskPriority,
    TaskQueue,
    TaskStatus,
    VideoProcessor,
    VideoTask,
)

__all__ = [
    # Legacy
    "FFmpegWrapper",
    "FFmpegError",
    "Clip",
    "Track",
    "Timeline",
    "Project",
    "Effect",
    # Interactive editing
    "MultiLevelCache",
    "SessionManager",
    "CostGuardian",
    "CostCheckResult",
    "InteractiveEditor",
    # File upload
    "AliyunFileUploader",
    "FileUploadError",
    "upload_file_for_transcription",
    # P0 Features - Task Queue
    "TaskQueue",
    "VideoTask",
    "TaskStatus",
    "TaskPriority",
    "QueueStats",
    "VideoProcessor",
    # P0 Features - Checkpoint
    "CheckpointManager",
    "VideoCheckpoint",
    "ProcessingStage",
    # P0 Features - Metrics
    "MetricsCollector",
    "TaskMetrics",
    "Alert",
    "AlertSeverity",
]
