"""Video Cut Skill - Intelligent video editing for AI agents."""

# Core
from video_cut_skill.ai.analyzer import ContentAnalysis, ContentAnalyzer
from video_cut_skill.ai.scene_detector import SceneDetector
from video_cut_skill.ai.strategy import (
    EditingStrategy,
    EditIntent,
    EditStyle,
    StrategyGenerator,
)

# AI
from video_cut_skill.ai.transcriber import Transcriber

# AutoEditor
from video_cut_skill.auto_editor import AutoEditor, EditConfig
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
