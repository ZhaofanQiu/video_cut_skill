"""Motion Graphics System - 动效生成系统 (Phase 2)."""

from video_cut_skill.motion_graphics.animations.easing import EasingFunction, EasingType
from video_cut_skill.motion_graphics.elements.shape import ShapeElement, ShapeStyle, ShapeType
from video_cut_skill.motion_graphics.elements.text import (
    TextAlign,
    TextAnimation,
    TextAnimationConfig,
    TextElement,
    TextStyle,
)
from video_cut_skill.motion_graphics.renderer import MGSpec, MotionGraphicsRenderer

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
