"""Video Cut Skill - Intelligent video editing for AI agents."""

# Core
from video_cut_skill.core.models import Project, Clip, Track, Timeline
from video_cut_skill.core.ffmpeg_wrapper import FFmpegWrapper

# AI
from video_cut_skill.ai.transcriber import Transcriber
from video_cut_skill.ai.scene_detector import SceneDetector
from video_cut_skill.ai.analyzer import ContentAnalyzer, ContentAnalysis
from video_cut_skill.ai.strategy import (
    StrategyGenerator,
    EditingStrategy,
    EditIntent,
    EditStyle,
)

# AutoEditor
from video_cut_skill.auto_editor import AutoEditor, EditConfig

# Motion Graphics
from video_cut_skill.motion_graphics import (
    EasingFunction,
    EasingType,
    TextElement,
    TextStyle,
    TextAnimation,
    TextAnimationConfig,
    TextAlign,
    ShapeElement,
    ShapeType,
    ShapeStyle,
    MotionGraphicsRenderer,
    MGSpec,
)

__version__ = "0.2.0"
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
]
