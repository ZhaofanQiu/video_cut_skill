"""Motion Graphics Renderer - 动效渲染器."""

import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Union

from video_cut_skill.motion_graphics.elements.shape import ShapeElement
from video_cut_skill.motion_graphics.elements.text import TextElement


@dataclass
class MGSpec:
    """Motion Graphics 规格.

    定义动效合成配置.
    """

    # 画布尺寸
    width: int = 1920
    height: int = 1080

    # 持续时间 (秒)
    duration: float = 5.0

    # 帧率
    fps: int = 30

    # 背景颜色
    background_color: Optional[str] = None

    # 元素列表
    elements: Optional[List[Union[TextElement, ShapeElement]]] = None

    def __post_init__(self):
        """初始化默认值."""
        if self.elements is None:
            self.elements = []


class MotionGraphicsRenderer:
    """动效渲染器.

    将动效元素渲染成视频或图片序列.

    Example:
        >>> renderer = MotionGraphicsRenderer()
        >>> spec = MGSpec(
        ...     width=1920,
        ...     height=1080,
        ...     elements=[
        ...         TextElement(
        ...             text="Hello",
        ...             position=(960, 540),
        ...             start_time=0,
        ...             end_time=3
        ...         )
        ...     ]
        ... )
        >>> output = renderer.render(spec, "/tmp/output.mp4")
    """

    def __init__(self, ffmpeg_path: str = "ffmpeg"):
        """初始化渲染器.

        Args:
            ffmpeg_path: FFmpeg 可执行文件路径
        """
        self.ffmpeg_path = ffmpeg_path

    def render(
        self,
        spec: MGSpec,
        output_path: Union[str, Path],
    ) -> Path:
        """渲染动效到视频文件.

        Args:
            spec: 动效规格
            output_path: 输出路径

        Returns:
            输出文件路径
        """
        output_path = Path(output_path)

        # TODO: 实现完整的动效渲染
        # 当前版本使用占位实现

        # 创建临时目录用于帧序列
        with tempfile.TemporaryDirectory() as temp_dir:
            # 生成帧序列 (简化版本)
            self._generate_frames(spec, temp_dir)

            # 使用 FFmpeg 合成视频
            self._encode_video(
                temp_dir,
                output_path,
                spec.fps,
                spec.duration,
            )

        return output_path

    def _generate_frames(self, spec: MGSpec, output_dir: str):
        """生成帧序列.

        Args:
            spec: 动效规格
            output_dir: 输出目录
        """
        # TODO: 实现完整的帧生成
        # 使用 PIL 或其他库绘制每一帧

        # 简化版本：创建空白帧
        total_frames = int(spec.duration * spec.fps)

        from PIL import Image

        for i in range(total_frames):
            time = i / spec.fps

            # 创建空白画布
            img = Image.new("RGB", (spec.width, spec.height), spec.background_color or "#000000")

            # TODO: 绘制可见元素
            elements = spec.elements or []
            for element in elements:
                if element.is_visible_at(time):
                    self._draw_element(img, element, time)

            # 保存帧
            frame_path = Path(output_dir) / f"frame_{i:05d}.png"
            img.save(frame_path)

    def _draw_element(
        self,
        img,
        element: Union[TextElement, ShapeElement],
        time: float,
    ):
        """在图像上绘制元素.

        Args:
            img: PIL Image 对象
            element: 元素
            time: 当前时间
        """
        from PIL import ImageDraw, ImageFont

        draw = ImageDraw.Draw(img)

        if isinstance(element, TextElement):
            # 绘制文字
            # 简化版本，不考虑动画
            x, y = element.position
            text = element.text
            style = element.style
            if style is None:
                from video_cut_skill.motion_graphics.elements.text import TextStyle

                style = TextStyle()  # type: ignore[assignment]

            # 尝试加载字体
            try:
                font: Union[ImageFont.FreeTypeFont, ImageFont.ImageFont] = ImageFont.truetype(style.font_family, style.font_size)
            except Exception:
                font = ImageFont.load_default()

            # 绘制文字
            draw.text((x, y), text, fill=style.font_color, font=font)

        elif isinstance(element, ShapeElement):
            # 绘制形状
            # 简化版本
            pass

    def _encode_video(
        self,
        frame_dir: str,
        output_path: Path,
        fps: int,
        duration: float,
    ):
        """使用 FFmpeg 编码视频.

        Args:
            frame_dir: 帧序列目录
            output_path: 输出路径
            fps: 帧率
            duration: 持续时间
        """
        import subprocess

        cmd = [
            self.ffmpeg_path,
            "-y",
            "-framerate",
            str(fps),
            "-i",
            f"{frame_dir}/frame_%05d.png",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-t",
            str(duration),
            str(output_path),
        ]

        subprocess.run(cmd, capture_output=True, check=True)

    def render_text_overlay(
        self,
        video_path: Union[str, Path],
        text_elements: List[TextElement],
        output_path: Union[str, Path],
    ) -> Path:
        """在视频上叠加文字动效.

        Args:
            video_path: 输入视频路径
            text_elements: 文字元素列表
            output_path: 输出路径

        Returns:
            输出文件路径
        """
        # TODO: 实现视频叠加渲染
        # 使用 FFmpeg 的 filter_complex

        return Path(output_path)

    def generate_ass_subtitle(
        self,
        text_elements: List[TextElement],
        output_path: Union[str, Path],
    ) -> Path:
        """生成 ASS 字幕文件.

        Args:
            text_elements: 文字元素列表
            output_path: 输出路径

        Returns:
            ASS 文件路径
        """
        output_path = Path(output_path)

        # ASS 文件头
        ass_header = """[Script Info]
Title: Motion Graphics Subtitle
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
"""

        # 添加样式
        styles = []
        events = []

        for i, element in enumerate(text_elements):
            style_name = f"Style{i}"
            styles.append(element.to_ass_style().replace(f"Style: {element.text[:20]}", f"Style: {style_name}"))

            # 创建事件 (简化版本)
            start_time = self._seconds_to_ass_time(element.start_time)
            end_time = self._seconds_to_ass_time(element.end_time)
            x, y = element.position

            event = f"Dialogue: 0,{start_time},{end_time},{style_name},,0,0,0,,{element.text}"
            events.append(event)

        # 写入文件
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(ass_header)
            f.write("\n".join(styles))
            f.write("\n\n[Events]\n")
            f.write("Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")
            f.write("\n".join(events))

        return output_path

    def _seconds_to_ass_time(self, seconds: float) -> str:
        """将秒数转换为 ASS 时间格式.

        Args:
            seconds: 秒数

        Returns:
            ASS 时间字符串 (H:MM:SS.cc)
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        centis = int((seconds % 1) * 100)
        return f"{hours}:{minutes:02d}:{secs:02d}.{centis:02d}"
