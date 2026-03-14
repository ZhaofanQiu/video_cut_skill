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
from video_cut_skill.core.ffmpeg_wrapper import FFmpegWrapper
from video_cut_skill.core.models import Clip, Project, Timeline, Track

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

__version__ = "0.3.0"
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
]
