"""Motion Graphics System - 动效生成系统 (Phase 2)."""

from video_cut_skill.motion_graphics.animations.easing import EasingFunction, EasingType
from video_cut_skill.motion_graphics.elements.text import TextElement, TextAnimation, TextStyle, TextAnimationConfig, TextAlign
from video_cut_skill.motion_graphics.elements.shape import ShapeElement, ShapeType, ShapeStyle
from video_cut_skill.motion_graphics.renderer import MotionGraphicsRenderer, MGSpec

__all__ = [
    # Animations
    "EasingFunction",
    "EasingType",
    # Elements
    "TextElement",
    "TextAnimation",
    "TextStyle",
    "TextAnimationConfig",
    "TextAlign",
    "ShapeElement",
    "ShapeType",
    "ShapeStyle",
    # Renderer
    "MotionGraphicsRenderer",
    "MGSpec",
]
