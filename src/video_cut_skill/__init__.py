"""Video Cut Skill - Intelligent video editing for AI agents."""

# Audio
# Core
from video_cut_skill.ai.analyzer import ContentAnalysis, ContentAnalyzer
from video_cut_skill.ai.scene_detector import SceneDetector
from video_cut_skill.ai.strategy import (
    EditingStrategy,
    EditIntent,
    EditStyle,
    StrategyGenerator,
)
from video_cut_skill.ai.transcriber import Transcriber
from video_cut_skill.audio import AudioAnalyzer, AudioEnhancer

# AutoEditor
from video_cut_skill.auto_editor import (
    AutoEditor,
    EditConfig,
    EditResult,
    extract_highlights,
    process_video,
)
from video_cut_skill.beat_detection import (
    BeatDetector,
    BeatDetectionResult,
    BeatInfo,
    BeatMatchingResult,
    BeatSyncEditor,
    CutPoint,
    detect_beats,
    generate_beat_cuts,
)
from video_cut_skill.clients import AliyunClient
from video_cut_skill.config import Config, get_config, load_config
from video_cut_skill.core.cache import MultiLevelCache
from video_cut_skill.core.checkpoint_manager import (
    CheckpointManager,
    ProcessingStage,
    VideoCheckpoint,
)
from video_cut_skill.core.cost_guardian import CostCheckResult, CostGuardian
from video_cut_skill.core.ffmpeg_wrapper import FFmpegWrapper
from video_cut_skill.core.file_upload import (
    AliyunFileUploader,
    FileUploadError,
    upload_file_for_transcription,
)

# Interactive Editing (New in v0.4.0)
from video_cut_skill.core.interactive_editor import InteractiveEditor
from video_cut_skill.core.metrics_collector import (
    Alert,
    AlertSeverity,
    MetricsCollector,
    TaskMetrics,
)
from video_cut_skill.core.models import Clip, Project, Timeline, Track
from video_cut_skill.core.session_manager import SessionManager
from video_cut_skill.core.task_queue import (
    QueueStats,
    TaskPriority,
    TaskQueue,
    TaskStatus,
    VideoProcessor,
    VideoTask,
)
from video_cut_skill.exceptions import (
    LLMError,
    SessionNotFoundError,
    TranscriptionError,
    VideoCutSkillError,
)
from video_cut_skill.models import (
    AgentAction,
    AgentResponse,
    ContentSegment,
    EditSession,
    EditStrategy,
    VideoSemantics,
)

# Motion Graphics
from video_cut_skill.motion_graphics import (
    EasingFunction,
    EasingType,
    MGSpec,
    MotionGraphicsRenderer,
    ShapeElement,
    ShapeStyle,
    ShapeType,
    TextAlign,
    TextAnimation,
    TextAnimationConfig,
    TextElement,
    TextStyle,
)

# P0 Processing Service
from video_cut_skill.processing_service import (
    ProcessingResult,
    VideoProcessingService,
    process_video_with_queue,
)

# Utils
from video_cut_skill.utils import (
    API_RETRY,
    DOWNLOAD_RETRY,
    NETWORK_RETRY,
    CachedSceneDetector,
    CachedTranscriber,
    CacheManager,
    HardwareInfo,
    JSONFormatter,
    ProgressLogger,
    RetryableOperation,
    RetryError,
    get_logger,
    get_optimal_device,
    retry_with_backoff,
    setup_structured_logging,
)

__version__ = "0.4.0"
__all__ = [
    # Core
    "FFmpegWrapper",
    "Project",
    "Clip",
    "Track",
    "Timeline",
    # AI
    "Transcriber",
    "SceneDetector",
    "ContentAnalyzer",
    "ContentAnalysis",
    "StrategyGenerator",
    "EditingStrategy",
    "EditIntent",
    "EditStyle",
    # AutoEditor
    "AutoEditor",
    "EditConfig",
    "EditResult",
    "process_video",
    "extract_highlights",
    # Interactive Editing (New)
    "InteractiveEditor",
    "SessionManager",
    "MultiLevelCache",
    "CostGuardian",
    "CostCheckResult",
    # File Upload (New)
    "AliyunFileUploader",
    "FileUploadError",
    "upload_file_for_transcription",
    # Models (New)
    "ContentSegment",
    "VideoSemantics",
    "EditSession",
    "EditStrategy",
    "AgentResponse",
    "AgentAction",
    # Clients (New)
    "AliyunClient",
    # Config (New)
    "Config",
    "load_config",
    "get_config",
    # Exceptions (New)
    "VideoCutSkillError",
    "TranscriptionError",
    "LLMError",
    "SessionNotFoundError",
    # Motion Graphics
    "EasingFunction",
    "EasingType",
    "TextElement",
    "TextStyle",
    "TextAnimation",
    "TextAnimationConfig",
    "TextAlign",
    "ShapeElement",
    "ShapeType",
    "ShapeStyle",
    "MotionGraphicsRenderer",
    "MGSpec",
    # Audio
    "AudioEnhancer",
    "AudioAnalyzer",
    # Utils - Hardware
    "HardwareInfo",
    "get_optimal_device",
    # Utils - Cache
    "CacheManager",
    "CachedTranscriber",
    "CachedSceneDetector",
    # Utils - Logging
    "JSONFormatter",
    "ProgressLogger",
    "get_logger",
    "setup_structured_logging",
    # Utils - Retry
    "retry_with_backoff",
    "RetryableOperation",
    "RetryError",
    "NETWORK_RETRY",
    "DOWNLOAD_RETRY",
    "API_RETRY",
    # Beat Detection (P1)
    "BeatDetector",
    "BeatDetectionResult",
    "BeatInfo",
    "BeatMatchingResult",
    "BeatSyncEditor",
    "CutPoint",
    "detect_beats",
    "generate_beat_cuts",
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
    # P0 Processing Service
    "ProcessingResult",
    "VideoProcessingService",
    "process_video_with_queue",
]
