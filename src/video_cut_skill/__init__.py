"""Video Cut Skill - Intelligent video editing for AI agents."""

from video_cut_skill.core.models import Project, Clip, Track, Timeline
from video_cut_skill.core.ffmpeg_wrapper import FFmpegWrapper
from video_cut_skill.ai.transcriber import Transcriber
from video_cut_skill.ai.scene_detector import SceneDetector

__version__ = "0.1.0"
__all__ = [
    "FFmpegWrapper",
    "Transcriber", 
    "SceneDetector",
    "Project",
    "Clip",
    "Track",
    "Timeline",
]
