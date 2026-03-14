"""AutoEditor - 一键智能剪辑器 (统一版)."""

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from video_cut_skill.ai.scene_detector import SceneDetectionResult, SceneDetector
from video_cut_skill.ai.transcriber import Transcriber
from video_cut_skill.core.ffmpeg_wrapper import FFmpegWrapper
from video_cut_skill.core.smart_transcriber import ModelSize, SmartTranscriber


@dataclass
class EditConfig:
    """编辑配置."""

    target_duration: Optional[float] = None
    aspect_ratio: str = "original"
    add_subtitles: bool = True
    output_path: Optional[str] = None
    whisper_model: str = "base"  # tiny/base/small/medium/large/turbo/auto
    highlight_keywords: List[str] = field(default_factory=list)
    context_seconds: float = 2.0
    # use_smart_transcriber 已弃用，保留向后兼容
    use_smart_transcriber: Optional[bool] = None


@dataclass
class EditResult:
    """编辑结果."""

    output_path: Path
    transcript: Optional[Dict] = None
    scenes: Optional[SceneDetectionResult] = None
    duration: float = 0.0
    processing_time: float = 0.0
    error: Optional[str] = None


class AutoEditor:
    """一键智能视频剪辑器 (统一版).

    支持两种分析模式：
    - "audio" (默认): 音频分析模式 - 语音识别、动态模型选择
    - "visual": 视觉分析模式 - 场景检测、镜头分割

    Example:
        >>> # 音频分析模式（默认，适合访谈、教学、播客）
        >>> editor = AutoEditor(analysis_mode="audio")
        >>> result = editor.process_video(
        ...     video_path="input.mp4",
        ...     config=EditConfig(
        ...         target_duration=60,
        ...         aspect_ratio="9:16",
        ...         whisper_model="auto",
        ...     )
        ... )

        >>> # 视觉分析模式（适合电影、MV、场景化内容）
        >>> editor = AutoEditor(analysis_mode="visual")
        >>> result = editor.cut_by_scenes("input.mp4", "output_dir/")
    """

    def __init__(
        self,
        ffmpeg: Optional[FFmpegWrapper] = None,
        transcriber: Optional[Union[Transcriber, SmartTranscriber]] = None,
        scene_detector: Optional[SceneDetector] = None,
        analysis_mode: str = "audio",
        work_dir: Optional[Union[str, Path]] = None,
        # 向后兼容参数
        use_smart_transcriber: Optional[bool] = None,
    ):
        """初始化 AutoEditor.

        Args:
            ffmpeg: FFmpeg 封装实例
            transcriber: 语音识别器实例（音频分析模式自动初始化）
            scene_detector: 场景检测器实例（视觉分析模式自动初始化）
            analysis_mode: 分析模式 - "audio" 或 "visual"
            work_dir: 工作目录（用于临时文件）
            use_smart_transcriber: 已弃用，使用 analysis_mode 替代
        """
        # 向后兼容处理
        if use_smart_transcriber is not None:
            import warnings

            warnings.warn("use_smart_transcriber is deprecated, use analysis_mode='audio' or 'visual'", DeprecationWarning, stacklevel=2)
            analysis_mode = "audio" if use_smart_transcriber else "visual"

        if analysis_mode not in ("audio", "visual"):
            raise ValueError(f"analysis_mode must be 'audio' or 'visual', got {analysis_mode}")

        self.analysis_mode = analysis_mode
        self.ffmpeg = ffmpeg or FFmpegWrapper()
        self.work_dir = Path(work_dir) if work_dir else Path.cwd()
        self.work_dir.mkdir(parents=True, exist_ok=True)

        # 根据模式初始化组件
        self.transcriber: Optional[Union[Transcriber, SmartTranscriber]]
        self._smart_transcriber: Optional[SmartTranscriber] = None

        if analysis_mode == "audio":
            if transcriber:
                self.transcriber = transcriber
                if isinstance(transcriber, SmartTranscriber):
                    self._smart_transcriber = transcriber
            else:
                self.transcriber = SmartTranscriber()
                self._smart_transcriber = self.transcriber
            self.scene_detector: Optional[SceneDetector] = None
        else:  # visual mode
            self.transcriber = transcriber  # May be None, lazy loaded
            self.scene_detector = scene_detector or SceneDetector()

    def _check_audio(self, video_path: str) -> bool:
        """检查视频是否有音频流."""
        if self.analysis_mode == "audio" and self._smart_transcriber:
            return self._smart_transcriber.has_audio_stream(video_path)
        # 视觉分析模式：不进行音频检查，直接返回 True
        return True

    def _transcribe(
        self,
        video_path: str,
        config: EditConfig,
    ) -> tuple[bool, Optional[Dict], Optional[str]]:
        """执行语音识别.

        Returns:
            (success, transcript_dict, error_message)
        """
        if self.analysis_mode == "audio" and self._smart_transcriber:
            # 音频分析模式：动态选择模型
            duration = self._smart_transcriber.get_video_duration(video_path)
            if config.whisper_model == "auto":
                model = ModelSize.BASE if duration < 300 else ModelSize.TINY
            else:
                model = ModelSize(config.whisper_model)

            smart_result = self._smart_transcriber.transcribe(
                video_path,
                model=model,
                is_output=False,
            )

            if smart_result.error:
                return False, None, f"转录失败: {smart_result.error}"

            transcript_dict = {
                "text": smart_result.text,
                "segments": smart_result.segments,
                "language": smart_result.language,
                "model_used": smart_result.model_used,
            }
            return True, transcript_dict, None
        else:
            # 视觉分析模式：使用标准 Transcriber
            if self.transcriber is None:
                self.transcriber = Transcriber(model_size=config.whisper_model)

            # 确保是 Transcriber 类型
            transcriber = self.transcriber
            if not isinstance(transcriber, Transcriber):
                raise RuntimeError("视觉分析模式下应使用 Transcriber")

            basic_result = transcriber.transcribe(Path(video_path))
            transcript_dict = {
                "text": " ".join([s.text for s in basic_result.segments]),
                "segments": [{"start": s.start, "end": s.end, "text": s.text} for s in basic_result.segments],
                "language": basic_result.language,
                "model_used": config.whisper_model,
            }
            return True, transcript_dict, None

    def process_video(
        self,
        video_path: Union[str, Path],
        config: Optional[EditConfig] = None,
    ) -> EditResult:
        """处理视频 (统一流程).

        Args:
            video_path: 输入视频路径
            config: 编辑配置

        Returns:
            EditResult: 处理结果
        """
        config = config or EditConfig()
        video_path = Path(video_path)
        start_time = time.time()

        if not video_path.exists():
            return EditResult(
                output_path=video_path,
                error=f"视频文件不存在: {video_path}",
            )

        print(f"🎬 处理视频: {video_path}")
        print(f"   模式: {'音频分析' if self.analysis_mode == 'audio' else '视觉分析'}")

        # 1. 检查音频
        print("\n1️⃣  检查音频...")
        if not self._check_audio(str(video_path)):
            return EditResult(
                output_path=video_path,
                error="视频无音频轨道，无法处理",
            )
        print("   ✓ 音频正常")

        # 2. 获取视频信息
        print("\n2️⃣  获取视频信息...")
        try:
            info = self.ffmpeg.get_video_info(video_path)
            duration = info["duration"]
            print(f"   时长: {duration:.1f}s")
            print(f"   分辨率: {info['width']}x{info['height']}")
        except Exception as e:
            return EditResult(
                output_path=video_path,
                error=f"无法获取视频信息: {e}",
            )

        # 3. 语音识别
        transcript: Optional[Dict[str, Any]] = None
        if config.add_subtitles or config.highlight_keywords:
            print("\n3️⃣  语音识别...")
            success, transcript, error = self._transcribe(str(video_path), config)
            if not success or transcript is None:
                return EditResult(
                    output_path=video_path,
                    duration=duration,
                    error=error or "转录失败",
                )
            print("   ✓ 转录完成")
            print(f"     模型: {transcript.get('model_used', 'unknown')}")
            print(f"     片段: {len(transcript.get('segments', []))}")
            print(f"     语言: {transcript.get('language', 'unknown')}")

        # 4. 场景检测（仅视觉分析模式）
        scenes = None
        if self.analysis_mode == "visual" and self.scene_detector:
            print("\n4️⃣  场景检测...")
            scenes = self.scene_detector.detect(video_path)
            print(f"   发现 {scenes.scene_count} 个场景")

        # 5. 确定输出路径
        if config.output_path:
            output_path = Path(config.output_path)
        else:
            mode_suffix = "_audio" if self.analysis_mode == "audio" else "_visual"
            output_path = video_path.parent / f"{video_path.stem}{mode_suffix}{video_path.suffix}"

        # 6. 处理视频
        print("\n5️⃣  生成输出...")
        temp_path = self.work_dir / f"temp_{video_path.name}"

        # 6a. 如果指定了目标时长，进行剪辑
        if config.target_duration and config.target_duration < duration:
            print(f"   剪辑至 {config.target_duration}s...")
            self.ffmpeg.cut_clip(
                video_path,
                temp_path,
                start_time=0,
                end_time=config.target_duration,
            )
        else:
            # 复制原文件
            import shutil

            shutil.copy(video_path, temp_path)

        # 6b. 添加字幕（如果需要）
        if config.add_subtitles and transcript:
            print("   添加字幕...")
            srt_path = self._generate_subtitles(transcript)
            if srt_path:
                subtitled_path = self.work_dir / f"subtitled_{video_path.name}"
                self.ffmpeg.add_subtitle(temp_path, srt_path, subtitled_path)
                temp_path = subtitled_path

        # 6c. 移动到最终输出路径
        import shutil

        shutil.move(temp_path, output_path)

        # 7. 提取高光（如果需要）
        if config.highlight_keywords and transcript:
            print("\n6️⃣  提取高光片段...")
            highlights = self._extract_highlights(transcript, config.highlight_keywords)
            print(f"   找到 {len(highlights)} 个高光片段")

        processing_time = time.time() - start_time
        print(f"\n✅ 完成! 输出: {output_path}")
        print(f"   用时: {processing_time:.1f}s")

        return EditResult(
            output_path=output_path,
            transcript=transcript,
            scenes=scenes,
            duration=duration,
            processing_time=processing_time,
        )

    def cut_by_scenes(
        self,
        video_path: Union[str, Path],
        output_dir: Union[str, Path],
        min_scene_duration: float = 1.0,
    ) -> List[Path]:
        """按场景切割视频 (仅视觉分析模式).

        Args:
            video_path: 输入视频路径
            output_dir: 输出目录
            min_scene_duration: 最小场景时长

        Returns:
            切割后的视频路径列表

        Raises:
            RuntimeError: 如果在音频分析模式下调用
        """
        if self.analysis_mode == "audio":
            raise RuntimeError("cut_by_scenes 仅在视觉分析模式下可用 (analysis_mode='visual')")

        # 确保 scene_detector 已初始化（在视觉分析模式下应该已初始化）
        if self.scene_detector is None:
            raise RuntimeError("场景检测器未初始化")

        video_path = Path(video_path)
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        print(f"🎬 按场景切割视频: {video_path}")

        # 检测场景
        scenes = self.scene_detector.detect(
            video_path,
            min_scene_len=min_scene_duration,
        )

        print(f"发现 {scenes.scene_count} 个场景，开始切割...")

        # 切割视频
        output_files = self.scene_detector.split_video(
            video_path,
            scenes.scenes,
            output_dir,
            filename_template="scene_{:03d}.mp4",
        )

        print(f"✅ 切割为 {len(output_files)} 个片段")
        return output_files

    def extract_highlights(
        self,
        video_path: Union[str, Path],
        keywords: List[str],
        output_path: Optional[Union[str, Path]] = None,
        context_seconds: float = 2.0,
        whisper_model: str = "auto",
    ) -> Path:
        """提取关键词精彩片段.

        Args:
            video_path: 输入视频路径
            keywords: 关键词列表
            output_path: 输出路径
            context_seconds: 上下文时间（秒）
            whisper_model: Whisper模型 (tiny/base/small/medium/large/turbo/auto)

        Returns:
            输出视频路径
        """
        video_path = Path(video_path)

        print(f"🎬 提取高光片段: {video_path}")
        print(f"关键词: {keywords}")

        # 语音识别
        config = EditConfig(whisper_model=whisper_model)
        success, transcript, error = self._transcribe(str(video_path), config)

        if not success or not transcript:
            print(f"⚠️  转录失败: {error}")
            return video_path

        # 检测关键词
        highlights = self._extract_highlights(transcript, keywords, context_seconds)

        if not highlights:
            print("⚠️  未找到关键词")
            return video_path

        print(f"找到 {len(highlights)} 个匹配片段")

        # 剪辑片段
        clips = []
        for i, match in enumerate(highlights[:5], 1):  # 最多5个
            clip_path = self.work_dir / f"highlight_{i:03d}.mp4"
            self.ffmpeg.cut_clip(
                video_path,
                clip_path,
                start_time=match["start"],
                end_time=match["end"],
            )
            clips.append(clip_path)
            print(f"  片段{i}: {match['start']:.1f}s-{match['end']:.1f}s")

        # 确定输出路径
        if output_path:
            final_path = Path(output_path)
        else:
            final_path = video_path.parent / f"{video_path.stem}_highlights{video_path.suffix}"

        # 拼接片段
        if len(clips) > 1:
            clip_paths: List[Union[str, Path]] = [str(c) for c in clips]
            self.ffmpeg.concatenate_clips(clip_paths, final_path)
        else:
            import shutil

            shutil.copy(clips[0], final_path)

        print(f"✅ 高光视频: {final_path}")
        return final_path

    def _extract_highlights(
        self,
        transcript: Dict,
        keywords: List[str],
        context_seconds: float = 2.0,
    ) -> List[Dict]:
        """基于关键词提取高光片段."""
        highlights = []

        for seg in transcript.get("segments", []):
            text = seg.get("text", "")
            score = sum(1 for kw in keywords if kw.lower() in text.lower())
            if score > 0:
                # 添加上下文
                start = max(0, seg.get("start", 0) - context_seconds)
                end = seg.get("end", 0) + context_seconds
                highlights.append(
                    {
                        "start": start,
                        "end": end,
                        "text": text,
                        "score": score,
                    }
                )

        # 按得分排序，取前5
        highlights.sort(key=lambda x: x["score"], reverse=True)
        return highlights[:5]

    def _generate_subtitles(self, transcript: Dict) -> Optional[Path]:
        """生成SRT字幕文件."""
        srt_path = self.work_dir / "temp_subtitles.srt"

        try:
            with open(srt_path, "w", encoding="utf-8") as f:
                for i, seg in enumerate(transcript.get("segments", []), 1):
                    start = self._seconds_to_srt_time(seg.get("start", 0))
                    end = self._seconds_to_srt_time(seg.get("end", 0))
                    text = seg.get("text", "")
                    f.write(f"{i}\n")
                    f.write(f"{start} --> {end}\n")
                    f.write(f"{text}\n\n")
            return srt_path
        except Exception as e:
            print(f"⚠️  字幕生成失败: {e}")
            return None

    @staticmethod
    def _seconds_to_srt_time(seconds: float) -> str:
        """转换为SRT时间格式."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


# 便捷的调用接口
def process_video(
    video_path: str,
    analysis_mode: str = "audio",
    **kwargs,
) -> EditResult:
    """便捷函数：处理视频.

    Args:
        video_path: 视频路径
        analysis_mode: 分析模式 - "audio" 或 "visual"
        **kwargs: EditConfig 的其他参数

    Returns:
        EditResult: 处理结果
    """
    editor = AutoEditor(analysis_mode=analysis_mode)
    config = EditConfig(**kwargs)
    return editor.process_video(video_path, config)


def extract_highlights(
    video_path: str,
    keywords: List[str],
    analysis_mode: str = "audio",
    **kwargs,
) -> Path:
    """便捷函数：提取高光片段.

    Args:
        video_path: 视频路径
        keywords: 关键词列表
        analysis_mode: 分析模式 - "audio" 或 "visual"
        **kwargs: 其他参数

    Returns:
        Path: 输出视频路径
    """
    editor = AutoEditor(analysis_mode=analysis_mode)
    return editor.extract_highlights(video_path, keywords, **kwargs)
