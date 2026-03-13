"""Strategy - 剪辑策略生成器 (Phase 2)."""

import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import List, Optional, Tuple, Union

from video_cut_skill.ai.analyzer import ContentAnalysis, ContentSegment

logger = logging.getLogger(__name__)


class EditStyle(Enum):
    """剪辑风格."""

    FAST_PACED = "fast_paced"  # 快节奏 (短视频)
    MODERATE = "moderate"  # 中等节奏
    SLOW = "slow"  # 慢节奏 (纪录片)
    TUTORIAL = "tutorial"  # 教程风格
    VLOG = "vlog"  # Vlog 风格


class LayoutType(Enum):
    """布局类型."""

    ORIGINAL = "original"  # 原始比例
    VERTICAL = "vertical"  # 竖屏 (9:16)
    SQUARE = "square"  # 方形 (1:1)
    WIDESCREEN = "widescreen"  # 宽屏 (16:9)


@dataclass
class ClipSpec:
    """片段剪辑规格."""

    # 时间范围
    start_time: float
    end_time: float

    # 布局
    layout: LayoutType = LayoutType.ORIGINAL

    # 裁剪区域 (x, y, width, height) - 相对于原始视频的坐标
    crop_region: Optional[Tuple[int, int, int, int]] = None

    # 缩放级别
    zoom_level: float = 1.0

    # 是否需要转场到下一个片段
    add_transition: bool = True
    transition_type: str = "fade"

    @property
    def duration(self) -> float:
        """片段时长."""
        return self.end_time - self.start_time


@dataclass
class TextOverlaySpec:
    """文字叠加规格."""

    text: str
    start_time: float
    end_time: float
    position: Tuple[int, int] = (960, 540)  # 默认居中
    style: str = "default"
    animation: str = "fade"


@dataclass
class EditingStrategy:
    """剪辑策略.

    完整的剪辑方案，包含所有剪辑决策.
    """

    # 目标信息
    target_duration: float
    target_aspect_ratio: Tuple[int, int] = (16, 9)
    target_style: EditStyle = EditStyle.MODERATE

    # 片段列表
    clips: List[ClipSpec] = field(default_factory=list)

    # 文字叠加
    text_overlays: List[TextOverlaySpec] = field(default_factory=list)

    # 转场效果
    transition_type: str = "fade"
    transition_duration: float = 0.3

    # 字幕设置
    add_subtitles: bool = True
    subtitle_style: str = "default"

    # 背景音乐
    background_music: Optional[str] = None
    music_volume: float = 0.3

    @property
    def total_duration(self) -> float:
        """策略总时长."""
        if not self.clips:
            return 0
        return sum(c.duration for c in self.clips)

    def validate(self) -> bool:
        """验证策略是否有效."""
        if not self.clips:
            return False
        if self.total_duration > self.target_duration * 1.2:  # 允许 20% 误差
            return False
        return True


@dataclass
class EditIntent:
    """编辑意图.

    用户对剪辑的需求描述.
    """

    # 目标时长 (秒)
    target_duration: Optional[float] = None

    # 目标平台
    platform: str = "general"  # tiktok, youtube, xiaohongshu, etc.

    # 风格偏好
    style: EditStyle = EditStyle.MODERATE

    # 布局要求
    layout: LayoutType = LayoutType.ORIGINAL

    # 关键词 (用于内容筛选)
    keywords: List[str] = field(default_factory=list)

    # 自然语言描述
    description: str = ""

    # 是否添加字幕
    add_subtitles: bool = True

    # 是否添加背景音乐
    add_music: bool = False


class StrategyGenerator:
    """剪辑策略生成器.

    根据内容分析结果生成剪辑策略.

    Example:
        >>> generator = StrategyGenerator()
        >>> intent = EditIntent(
        ...     target_duration=60,
        ...     style=EditStyle.FAST_PACED,
        ...     platform="tiktok"
        ... )
        >>> strategy = generator.generate(analysis, intent)
        >>> print(f"Generated {len(strategy.clips)} clips")
    """

    # 平台预设
    PLATFORM_PRESETS = {
        "tiktok": {
            "aspect_ratio": (9, 16),
            "max_duration": 60,
            "style": EditStyle.FAST_PACED,
        },
        "youtube": {
            "aspect_ratio": (16, 9),
            "max_duration": None,
            "style": EditStyle.MODERATE,
        },
        "xiaohongshu": {
            "aspect_ratio": (3, 4),
            "max_duration": 300,
            "style": EditStyle.VLOG,
        },
        "instagram": {
            "aspect_ratio": (4, 5),
            "max_duration": 60,
            "style": EditStyle.MODERATE,
        },
    }

    def __init__(self):
        """初始化策略生成器."""
        pass

    def generate(
        self,
        analysis: ContentAnalysis,
        intent: EditIntent,
    ) -> EditingStrategy:
        """生成剪辑策略.

        Args:
            analysis: 内容分析结果
            intent: 编辑意图

        Returns:
            剪辑策略
        """
        logger.info("Generating editing strategy...")

        # 1. 应用平台预设
        intent = self._apply_platform_preset(intent)

        # 2. 确定目标时长
        target_duration = intent.target_duration or analysis.duration

        # 3. 选择精彩片段
        selected_segments = self._select_segments(analysis, target_duration, intent)

        # 4. 生成片段规格
        clips = self._generate_clips(selected_segments, intent)

        # 5. 生成文字叠加
        text_overlays = self._generate_text_overlays(clips, intent)

        # 6. 构建策略
        platform_preset = self.PLATFORM_PRESETS.get(intent.platform, {})
        aspect_ratio = platform_preset.get("aspect_ratio", (16, 9)) if isinstance(platform_preset, dict) else (16, 9)
        strategy = EditingStrategy(
            target_duration=target_duration,
            target_aspect_ratio=aspect_ratio,
            target_style=intent.style,
            clips=clips,
            text_overlays=text_overlays,
            add_subtitles=intent.add_subtitles,
        )

        logger.info(f"Strategy generated: {len(strategy.clips)} clips, " f"{strategy.total_duration:.1f}s total")

        return strategy

    def _apply_platform_preset(self, intent: EditIntent) -> EditIntent:
        """应用平台预设.

        Args:
            intent: 原始意图

        Returns:
            更新后的意图
        """
        preset = self.PLATFORM_PRESETS.get(intent.platform.lower())
        if not preset or not isinstance(preset, dict):
            return intent

        # 更新参数
        max_duration = preset.get("max_duration")
        if intent.target_duration is None and max_duration:
            intent.target_duration = min(max_duration, 60)  # 默认 60 秒

        style = preset.get("style")
        if style:
            intent.style = style

        return intent

    def _select_segments(
        self,
        analysis: ContentAnalysis,
        target_duration: float,
        intent: EditIntent,
    ) -> List[ContentSegment]:
        """选择要使用的片段.

        Args:
            analysis: 内容分析
            target_duration: 目标时长
            intent: 编辑意图

        Returns:
            选中的片段列表
        """
        if not analysis.segments:
            return []

        # 从精彩片段候选开始
        candidates = analysis.highlight_candidates.copy()

        # 如果没有候选，使用所有片段
        if not candidates:
            candidates = analysis.segments.copy()

        # 根据关键词筛选
        if intent.keywords:
            keyword_segments = []
            for keyword in intent.keywords:
                keyword_segments.extend(analysis.search_by_keyword(keyword))
            if keyword_segments:
                candidates = keyword_segments

        # 根据风格调整选择策略
        if intent.style == EditStyle.FAST_PACED:
            # 快节奏：选择更多短片段
            candidates = sorted(candidates, key=lambda s: s.importance_score, reverse=True)
            # 限制每个片段的最大时长
            candidates = [c for c in candidates if c.duration <= 5.0]

        elif intent.style == EditStyle.SLOW:
            # 慢节奏：选择较少的长片段
            candidates = sorted(candidates, key=lambda s: s.duration, reverse=True)

        # 累积选择直到达到目标时长
        selected = []
        total_duration: float = 0.0

        for segment in candidates:
            if total_duration >= target_duration:
                break
            selected.append(segment)
            total_duration += segment.duration

        # 按时间排序
        selected.sort(key=lambda s: s.start_time)

        return selected

    def _generate_clips(
        self,
        segments: List[ContentSegment],
        intent: EditIntent,
    ) -> List[ClipSpec]:
        """生成片段规格.

        Args:
            segments: 选中的内容片段
            intent: 编辑意图

        Returns:
            片段规格列表
        """
        clips = []

        for i, segment in enumerate(segments):
            # 确定布局
            layout = intent.layout

            # 计算裁剪区域
            crop_region = None
            if layout == LayoutType.VERTICAL:
                # 竖屏：从中心裁剪
                crop_region = (420, 0, 1080, 1080)  # 假设 1920x1080 输入

            # 创建片段规格
            clip = ClipSpec(
                start_time=segment.start_time,
                end_time=segment.end_time,
                layout=layout,
                crop_region=crop_region,
                add_transition=(i > 0),  # 第一个片段不需要转场
                transition_type="fade",
            )
            clips.append(clip)

        return clips

    def _generate_text_overlays(
        self,
        clips: List[ClipSpec],
        intent: EditIntent,
    ) -> List[TextOverlaySpec]:
        """生成文字叠加规格.

        Args:
            clips: 片段列表
            intent: 编辑意图

        Returns:
            文字叠加规格列表
        """
        overlays = []

        # 简化版本：在第一个片段添加标题
        if clips and intent.description:
            overlay = TextOverlaySpec(
                text=intent.description[:50],  # 限制长度
                start_time=clips[0].start_time,
                end_time=clips[0].start_time + 3.0,
                position=(960, 200),  # 顶部居中
                style="title",
                animation="slide_down",
            )
            overlays.append(overlay)

        return overlays

    def generate_timeline_preview(
        self,
        strategy: EditingStrategy,
        output_path: Union[str, Path],
    ) -> Path:
        """生成时间线预览图.

        Args:
            strategy: 剪辑策略
            output_path: 输出路径

        Returns:
            预览图路径
        """
        # TODO: 实现时间线可视化
        return Path(output_path)
