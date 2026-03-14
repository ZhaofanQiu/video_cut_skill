"""Text Element - 动态文字元素."""

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Tuple


class TextAnimation(Enum):
    """文字动画类型."""

    NONE = "none"
    FADE = "fade"
    SLIDE_UP = "slide_up"
    SLIDE_DOWN = "slide_down"
    SLIDE_LEFT = "slide_left"
    SLIDE_RIGHT = "slide_right"
    SCALE = "scale"
    TYPEWRITER = "typewriter"
    BLUR = "blur"


class TextAlign(Enum):
    """文字对齐方式."""

    LEFT = "left"
    CENTER = "center"
    RIGHT = "right"


@dataclass
class TextStyle:
    """文字样式配置."""

    # 字体设置
    font_family: str = "Arial"
    font_size: int = 48
    font_color: str = "#FFFFFF"
    font_weight: str = "normal"  # normal, bold

    # 描边
    stroke_color: Optional[str] = None
    stroke_width: int = 0

    # 阴影
    shadow_color: Optional[str] = None
    shadow_offset: Tuple[int, int] = (2, 2)
    shadow_blur: int = 0

    # 背景
    background_color: Optional[str] = None
    background_padding: Tuple[int, int] = (10, 5)
    background_radius: int = 0

    # 对齐
    align: TextAlign = TextAlign.CENTER

    # 行高
    line_height: float = 1.2

    # 最大宽度 (用于自动换行)
    max_width: Optional[int] = None


@dataclass
class TextAnimationConfig:
    """文字动画配置."""

    animation_type: TextAnimation = TextAnimation.FADE
    duration: float = 0.5  # 动画持续时间(秒)
    delay: float = 0.0  # 动画延迟(秒)

    # 缓动类型
    easing: str = "ease_out_quad"

    # 滑动距离 (用于 slide 动画)
    slide_distance: int = 50

    # 打字机效果速度 (字符/秒)
    typewriter_speed: float = 10.0


@dataclass
class TextElement:
    """文字元素.

    用于创建动态文字叠加效果.

    Example:
        >>> text = TextElement(
        ...     text="Hello World",
        ...     position=(100, 200),
        ...     style=TextStyle(font_size=64, font_color="#FF0000"),
        ...     entry_animation=TextAnimationConfig(
        ...         animation_type=TextAnimation.SLIDE_UP,
        ...         duration=0.5
        ...     )
        ... )
    """

    # 文字内容
    text: str

    # 位置 (x, y)，相对于视频的像素坐标
    position: Tuple[int, int] = (0, 0)

    # 样式
    style: Optional[TextStyle] = None

    # 入场动画
    entry_animation: Optional[TextAnimationConfig] = None

    # 出场动画
    exit_animation: Optional[TextAnimationConfig] = None

    # 显示时间范围 (相对于视频开始的时间，秒)
    start_time: float = 0.0
    end_time: float = 5.0

    def __post_init__(self):
        """初始化默认值."""
        if self.style is None:
            self.style = TextStyle()

    @property
    def duration(self) -> float:
        """元素显示总时长."""
        return self.end_time - self.start_time

    def is_visible_at(self, time: float) -> bool:
        """检查在指定时间是否可见."""
        return self.start_time <= time < self.end_time

    def get_animation_progress(self, time: float, animation_config: TextAnimationConfig, is_entry: bool = True) -> float:
        """获取动画进度.

        Args:
            time: 当前时间
            animation_config: 动画配置
            is_entry: 是否为入场动画

        Returns:
            动画进度 [0, 1]
        """
        if is_entry:
            anim_start = self.start_time + animation_config.delay
            anim_end = anim_start + animation_config.duration
        else:
            anim_end = self.end_time - animation_config.delay
            anim_start = anim_end - animation_config.duration

        if time < anim_start:
            return 0.0
        if time >= anim_end:
            return 1.0

        return (time - anim_start) / animation_config.duration

    def to_ass_style(self) -> str:
        """转换为 ASS 字幕样式.

        Returns:
            ASS 样式字符串
        """
        style = self.style
        if style is None:
            style = TextStyle()  # type: ignore[assignment]

        # 转换颜色格式 (RGB -> BGR for ASS)
        def convert_color(hex_color: str) -> str:
            """将十六进制颜色转换为 ASS 格式.

            Args:
                hex_color: 十六进制颜色字符串 (#RRGGBB)

            Returns:
                ASS 格式的颜色字符串 (&HBBGGRR&)
            """
            hex_color = hex_color.lstrip("#")
            r, g, b = hex_color[0:2], hex_color[2:4], hex_color[4:6]
            return f"&H{b}{g}{r}&"

        font_color = convert_color(style.font_color)

        # ASS 样式格式
        # Name, Fontname, Fontsize, PrimaryColour, SecondaryColour,
        # OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut,
        # ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow,
        # Alignment, MarginL, MarginR, MarginV, Encoding
        bold = 1 if style.font_weight == "bold" else 0

        return (
            f"Style: {self.text[:20]},{style.font_family},{style.font_size},"
            f"{font_color},{font_color},{font_color},{font_color},"
            f"{bold},0,0,0,100,100,0,0,1,{style.stroke_width},0,"
            f"{2 if style.align == TextAlign.CENTER else (1 if style.align == TextAlign.LEFT else 3)},"
            f"10,10,10,1"
        )

    def __repr__(self) -> str:
        """返回文本元素的字符串表示.

        Returns:
            格式为 "TextElement('text...' @ position)" 的字符串
        """
        return f"TextElement('{self.text[:30]}...' @ {self.position})"
