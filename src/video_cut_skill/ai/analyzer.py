"""Content Analyzer - 内容分析器 (Phase 2)."""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from video_cut_skill.ai.scene_detector import SceneDetectionResult, SceneDetector
from video_cut_skill.ai.transcriber import Transcriber, TranscriptResult

logger = logging.getLogger(__name__)


@dataclass
class AudioFeatures:
    """音频特征."""

    # 音量统计
    mean_volume: float = 0.0
    max_volume: float = 0.0

    # 静音检测
    silent_segments: List[Tuple[float, float]] = field(default_factory=list)

    # 语速 (words per minute)
    speech_rate: float = 0.0

    # 音频指纹 (用于匹配)
    fingerprint: Optional[str] = None


@dataclass
class VisualFeatures:
    """视觉特征."""

    # 亮度统计
    mean_brightness: float = 0.0
    brightness_variance: float = 0.0

    # 运动强度
    motion_score: float = 0.0

    # 画面变化检测
    keyframe_times: List[float] = field(default_factory=list)

    # 颜色分布
    dominant_colors: List[str] = field(default_factory=list)


@dataclass
class ContentSegment:
    """内容片段.

    结合转录和场景的统一片段.
    """

    # 时间范围
    start_time: float
    end_time: float

    # 转录内容
    transcript: Optional[TranscriptResult] = None

    # 场景信息
    scene: Optional[SceneDetectionResult] = None

    # 特征
    audio_features: Optional[AudioFeatures] = None
    visual_features: Optional[VisualFeatures] = None

    # 重要性评分 (0-1)
    importance_score: float = 0.0

    @property
    def duration(self) -> float:
        """片段时长."""
        return self.end_time - self.start_time

    @property
    def text(self) -> str:
        """片段文本内容."""
        if self.transcript and self.transcript.segments:
            return " ".join([s.text for s in self.transcript.segments])
        return ""


@dataclass
class ContentAnalysis:
    """内容分析结果."""

    # 基本信息
    video_path: Path
    duration: float

    # 转录结果
    transcript: Optional[TranscriptResult] = None

    # 场景检测结果
    scenes: Optional[SceneDetectionResult] = None

    # 统一片段列表
    segments: List[ContentSegment] = field(default_factory=list)

    # 关键词
    keywords: List[str] = field(default_factory=list)

    # 精彩片段候选
    highlight_candidates: List[ContentSegment] = field(default_factory=list)

    # 音频特征
    audio_features: Optional[AudioFeatures] = None

    # 视觉特征
    visual_features: Optional[VisualFeatures] = None

    @property
    def highlights(self) -> List[ContentSegment]:
        """精彩片段列表 (highlight_candidates 的别名)."""
        return self.highlight_candidates

    def get_segment_at_time(self, time: float) -> Optional[ContentSegment]:
        """获取指定时间的内容片段."""
        for segment in self.segments:
            if segment.start_time <= time < segment.end_time:
                return segment
        return None

    def search_by_keyword(self, keyword: str) -> List[ContentSegment]:
        """搜索包含关键词的片段."""
        keyword_lower = keyword.lower()
        results = []
        for segment in self.segments:
            if keyword_lower in segment.text.lower():
                results.append(segment)
        return results


class ContentAnalyzer:
    """内容分析器.

    综合分析视频的语音、视觉和场景内容.

    Example:
        >>> analyzer = ContentAnalyzer()
        >>> analysis = analyzer.analyze("video.mp4")
        >>> print(f"Duration: {analysis.duration}")
        >>> print(f"Keywords: {analysis.keywords}")
        >>> # 搜索关键词
        >>> segments = analysis.search_by_keyword("important")
    """

    def __init__(
        self,
        transcriber: Optional[Transcriber] = None,
        scene_detector: Optional[SceneDetector] = None,
    ):
        """初始化分析器.

        Args:
            transcriber: 语音识别器
            scene_detector: 场景检测器
        """
        self.transcriber = transcriber or Transcriber(model_size="tiny")
        self.scene_detector = scene_detector or SceneDetector()

    def analyze(
        self,
        video_path: Union[str, Path],
        extract_audio_features: bool = True,
        extract_visual_features: bool = False,
    ) -> ContentAnalysis:
        """分析视频内容.

        Args:
            video_path: 视频路径
            extract_audio_features: 是否提取音频特征
            extract_visual_features: 是否提取视觉特征

        Returns:
            内容分析结果
        """
        video_path = Path(video_path)

        logger.info(f"Analyzing video: {video_path}")

        # 1. 语音识别
        logger.info("Transcribing audio...")
        transcript = self.transcriber.transcribe(video_path)

        # 2. 场景检测
        logger.info("Detecting scenes...")
        scenes = self.scene_detector.detect(video_path)

        # 3. 构建统一片段
        logger.info("Building content segments...")
        segments = self._build_segments(transcript, scenes)

        # 4. 提取关键词
        logger.info("Extracting keywords...")
        keywords = self._extract_keywords(transcript)

        # 5. 计算精彩片段候选
        logger.info("Finding highlight candidates...")
        highlights = self._find_highlights(segments)

        # 6. 提取音频特征
        audio_features = None
        if extract_audio_features:
            logger.info("Extracting audio features...")
            audio_features = self._extract_audio_features(video_path, transcript)

        # 7. 提取视觉特征
        visual_features = None
        if extract_visual_features:
            logger.info("Extracting visual features...")
            visual_features = self._extract_visual_features(video_path)

        # 获取视频时长
        from video_cut_skill.core.ffmpeg_wrapper import FFmpegWrapper

        ffmpeg = FFmpegWrapper()
        info = ffmpeg.get_video_info(video_path)
        duration = info.get("duration", 0)

        return ContentAnalysis(
            video_path=video_path,
            duration=duration,
            transcript=transcript,
            scenes=scenes,
            segments=segments,
            keywords=keywords,
            highlight_candidates=highlights,
            audio_features=audio_features,
            visual_features=visual_features,
        )

    def _build_segments(
        self,
        transcript: TranscriptResult,
        scenes: SceneDetectionResult,
    ) -> List[ContentSegment]:
        """构建统一的内容片段.

        将转录片段和场景片段对齐合并.

        Args:
            transcript: 转录结果
            scenes: 场景检测结果

        Returns:
            内容片段列表
        """
        segments = []

        # 简化版本：使用转录片段作为主要分割
        # TODO: 实现更复杂的对齐算法

        if transcript and transcript.segments:
            for seg in transcript.segments:
                # 计算重要性 (基于语速、关键词等)
                importance = self._calculate_importance(seg)

                content_seg = ContentSegment(
                    start_time=seg.start,
                    end_time=seg.end,
                    transcript=transcript,  # 简化：引用完整转录
                    importance_score=importance,
                )
                segments.append(content_seg)
        elif scenes and scenes.scenes:
            # 如果没有转录，使用场景
            for scene in scenes.scenes:
                content_seg = ContentSegment(
                    start_time=scene.start,
                    end_time=scene.end,
                    scene=scenes,
                    importance_score=0.5,  # 默认中等重要性
                )
                segments.append(content_seg)

        return segments

    def _calculate_importance(self, segment) -> float:
        """计算片段重要性.

        Args:
            segment: 转录片段

        Returns:
            重要性评分 (0-1)
        """
        # 简化版本：基于文本长度和语速
        # TODO: 实现更复杂的分析 (关键词、情感等)

        text_length = len(segment.text)
        duration = segment.end - segment.start

        if duration == 0:
            return 0.0

        # 语速 (words per second)
        words = len(segment.text.split())
        wps = words / duration

        # 综合评分
        score = min(1.0, (text_length / 100) * 0.3 + (wps / 3) * 0.7)

        return score

    def _extract_keywords(self, transcript: TranscriptResult) -> List[str]:
        """提取关键词.

        Args:
            transcript: 转录结果

        Returns:
            关键词列表
        """
        # 简化版本：提取高频词
        # TODO: 使用 TF-IDF 或更高级的关键词提取算法

        if not transcript or not transcript.segments:
            return []

        # 合并所有文本
        full_text = " ".join([s.text for s in transcript.segments])

        # 简单的词频统计 (移除停用词)
        stop_words = {
            "the",
            "a",
            "an",
            "is",
            "are",
            "was",
            "were",
            "be",
            "been",
            "being",
            "to",
            "of",
            "and",
            "in",
            "that",
            "have",
            "i",
            "it",
            "for",
            "not",
            "on",
            "with",
            "he",
            "as",
            "you",
            "do",
            "at",
            "this",
            "but",
            "his",
            "by",
            "from",
            "they",
            "we",
            "say",
            "her",
            "she",
            "or",
            "will",
            "my",
            "one",
            "all",
            "would",
            "there",
            "their",
            "what",
            "so",
            "up",
            "out",
            "if",
            "about",
            "who",
            "get",
            "which",
            "go",
            "me",
        }

        words = full_text.lower().split()
        word_freq: Dict[str, int] = {}

        for word in words:
            word = word.strip(".,!?;:\"'")
            if word and word not in stop_words and len(word) > 2:
                word_freq[word] = word_freq.get(word, 0) + 1

        # 返回频率最高的前 10 个词
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        return [word for word, freq in sorted_words[:10]]

    def _find_highlights(self, segments: List[ContentSegment]) -> List[ContentSegment]:
        """查找精彩片段候选.

        Args:
            segments: 内容片段列表

        Returns:
            精彩片段列表 (按重要性排序)
        """
        # 按重要性排序
        sorted_segments = sorted(segments, key=lambda s: s.importance_score, reverse=True)

        # 返回前 20%
        top_count = max(1, len(sorted_segments) // 5)
        return sorted_segments[:top_count]

    def _extract_audio_features(self, video_path: Path, transcript: Optional[TranscriptResult] = None) -> AudioFeatures:
        """提取音频特征.

        Args:
            video_path: 视频路径
            transcript: 转录结果（用于计算语速）

        Returns:
            音频特征
        """
        import re
        import subprocess

        try:
            # 使用 FFmpeg 分析音频音量
            # 1. 获取音频的音量统计信息
            cmd = [
                "ffmpeg",
                "-i",
                str(video_path),
                "-af",
                "volumedetect",
                "-vn",  # 禁用视频
                "-sn",  # 禁用字幕
                "-dn",  # 禁用数据流
                "-f",
                "null",
                "-",
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

            output = result.stderr  # FFmpeg 输出到 stderr

            mean_volume = 0.0
            max_volume = 0.0

            # 解析音量信息
            mean_match = re.search(r"mean_volume:\s+(-?\d+\.?\d*)\s+dB", output)
            max_match = re.search(r"max_volume:\s+(-?\d+\.?\d*)\s+dB", output)

            if mean_match:
                mean_volume = float(mean_match.group(1))
            if max_match:
                max_volume = float(max_match.group(1))

            # 2. 检测静音片段
            silent_segments = []
            try:
                silence_cmd = [
                    "ffmpeg",
                    "-i",
                    str(video_path),
                    "-af",
                    "silencedetect=noise=-50dB:d=0.5",  # -50dB 阈值，0.5秒以上
                    "-vn",
                    "-sn",
                    "-dn",
                    "-f",
                    "null",
                    "-",
                ]

                silence_result = subprocess.run(silence_cmd, capture_output=True, text=True, timeout=120)

                silence_output = silence_result.stderr

                # 解析静音开始和结束时间
                starts = re.findall(r"silence_start:\s+([\d\.]+)", silence_output)
                ends = re.findall(r"silence_end:\s+([\d\.]+)", silence_output)

                for start, end in zip(starts, ends):
                    silent_segments.append((float(start), float(end)))

            except Exception as e:
                logger.warning(f"Failed to detect silence: {e}")

            # 3. 计算语速 (基于转录结果)
            speech_rate = 0.0
            if transcript and transcript.segments:
                total_words = sum(len(seg.text.split()) for seg in transcript.segments)
                total_duration = sum(seg.end - seg.start for seg in transcript.segments)

                if total_duration > 0:
                    # words per minute
                    speech_rate = (total_words / total_duration) * 60

            return AudioFeatures(
                mean_volume=mean_volume,
                max_volume=max_volume,
                silent_segments=silent_segments,
                speech_rate=speech_rate,
            )

        except Exception as e:
            logger.warning(f"Failed to extract audio features: {e}")
            return AudioFeatures()

    def _extract_visual_features(self, video_path: Path) -> VisualFeatures:
        """提取视觉特征.

        Args:
            video_path: 视频路径

        Returns:
            视觉特征
        """
        # TODO: 实现视觉特征提取
        # 使用 OpenCV 分析视频帧

        return VisualFeatures()
