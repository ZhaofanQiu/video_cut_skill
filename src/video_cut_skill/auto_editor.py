"""AutoEditor - 一键智能剪辑器 (统一版)."""

import tempfile
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
    # 指定要保留的段落（由InteractiveEditor使用）- 兼容旧版
    keep_segments: Optional[List[Dict[str, Any]]] = None
    # 精确时间范围模式 - 新版支持句子级剪辑
    time_ranges: Optional[List[Dict[str, float]]] = None
    # 外部传入的转录结果（如阿里云转录），避免重复转录
    transcription: Optional[Dict[str, Any]] = None


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
        # 使用临时目录作为默认工作目录，避免污染项目目录
        if work_dir:
            self.work_dir = Path(work_dir)
        else:
            self.work_dir = Path(tempfile.mkdtemp(prefix="video_cut_skill_"))
        self.work_dir.mkdir(parents=True, exist_ok=True)

        # 初始化阿里云客户端（用于LLM字幕优化）
        self._aliyun_client = None

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

    def _get_aliyun_client(self):
        """获取或创建阿里云客户端（懒加载）."""
        if self._aliyun_client is None:
            try:
                from video_cut_skill.clients.aliyun_client import AliyunClient
                self._aliyun_client = AliyunClient()
            except Exception as e:
                print(f"   ⚠️ 无法初始化阿里云客户端: {e}")
                return None
        return self._aliyun_client

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

        # 3. 语音识别 - 优先使用外部传入的转录结果
        transcript: Optional[Dict[str, Any]] = None
        if config.add_subtitles or config.highlight_keywords:
            if config.transcription:
                # 使用外部传入的转录结果（如阿里云转录）
                print("\n3️⃣  使用外部转录结果...")
                transcript = config.transcription
                print("   ✓ 使用阿里云转录结果")
                print(f"     片段: {len(transcript.get('segments', []))}")
            else:
                # 本地转录作为兜底方案
                print("\n3️⃣  语音识别（本地Whisper）...")
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

        # 6a. 根据保留段落或目标时长进行剪辑
        segment_time_offsets = []  # 记录每个片段在新视频中的时间偏移
        if config.time_ranges:
            # 根据精确时间范围剪辑（支持句子级）
            print(f"   根据精确时间范围剪辑，保留 {len(config.time_ranges)} 个片段...")
            segment_time_offsets = self._cut_by_time_ranges(video_path, temp_path, config.time_ranges)
        elif config.keep_segments:
            # 根据语义段落智能剪辑（兼容旧版）
            print(f"   根据语义段落剪辑，保留 {len(config.keep_segments)} 个片段...")
            segment_time_offsets = self._cut_by_segments(video_path, temp_path, config.keep_segments)
        elif config.target_duration and config.target_duration < duration:
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
            # 根据剪辑类型选择对应的字幕生成方法
            # 默认横屏16:9，每行20字；竖屏9:16，每行15字
            is_vertical = config.aspect_ratio == "9:16"
            max_chars = 15 if is_vertical else 20
            
            if config.time_ranges and segment_time_offsets:
                srt_path = self._generate_subtitles_for_segments(
                    transcript, 
                    segment_time_offsets,
                    max_chars_per_line=max_chars,
                    aspect_ratio=config.aspect_ratio,
                    use_llm=True,
                )
            elif config.keep_segments and segment_time_offsets:
                srt_path = self._generate_subtitles_for_segments(
                    transcript, 
                    segment_time_offsets,
                    max_chars_per_line=max_chars,
                    aspect_ratio=config.aspect_ratio,
                    use_llm=True,
                )
            else:
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
        context_seconds: float = 2.0,
        output_path: Optional[Union[str, Path]] = None,
    ) -> EditResult:
        """提取包含关键词的高光片段.

        Args:
            video_path: 输入视频路径
            keywords: 关键词列表
            context_seconds: 上下文秒数
            output_path: 可选的输出路径

        Returns:
            EditResult: 处理结果
        """
        video_path = Path(video_path)
        start_time = time.time()

        if not video_path.exists():
            return EditResult(
                output_path=video_path,
                error=f"视频文件不存在: {video_path}",
            )

        print(f"🎬 提取高光片段: {video_path}")
        print(f"   关键词: {', '.join(keywords)}")

        # 转录
        config = EditConfig(
            whisper_model="base",
            highlight_keywords=keywords,
            context_seconds=context_seconds,
        )

        success, transcript, error = self._transcribe(str(video_path), config)
        if not success or transcript is None:
            return EditResult(
                output_path=video_path,
                error=error or "转录失败",
            )

        # 提取高光
        highlights = self._extract_highlights(transcript, keywords, context_seconds)

        if not highlights:
            return EditResult(
                output_path=video_path,
                transcript=transcript,
                error="未找到包含关键词的片段",
            )

        # 合并重叠的片段
        merged = self._merge_overlapping_segments(highlights)

        # 生成输出路径
        if output_path is None:
            output_path = video_path.parent / f"{video_path.stem}_highlights{video_path.suffix}"
        else:
            output_path = Path(output_path)

        # 切割并合并高光片段
        if len(merged) == 1:
            self.ffmpeg.cut_clip(
                video_path,
                output_path,
                merged[0]["start"],
                merged[0]["end"],
            )
        else:
            # 合并多个片段
            clips = []
            for i, highlight in enumerate(merged):
                clip_path = self.work_dir / f"highlight_{i}.mp4"
                self.ffmpeg.cut_clip(
                    video_path,
                    clip_path,
                    highlight["start"],
                    highlight["end"],
                )
                clips.append(clip_path)

            self.ffmpeg.concatenate_clips([str(c) for c in clips], output_path)

        processing_time = time.time() - start_time
        print(f"\n✅ 完成! 输出: {output_path}")
        print(f"   找到 {len(merged)} 个高光片段")
        print(f"   用时: {processing_time:.1f}s")

        return EditResult(
            output_path=output_path,
            transcript=transcript,
            duration=sum(h["end"] - h["start"] for h in merged),
            processing_time=processing_time,
        )

    def _merge_overlapping_segments(
        self,
        segments: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """合并重叠的时间段."""
        if not segments:
            return []

        # 按开始时间排序
        sorted_segs = sorted(segments, key=lambda x: x["start"])
        merged = [sorted_segs[0].copy()]

        for current in sorted_segs[1:]:
            last = merged[-1]
            if current["start"] <= last["end"]:
                # 有重叠，合并
                last["end"] = max(last["end"], current["end"])
                last["text"] = f"{last['text']} {current['text']}"
            else:
                merged.append(current.copy())

        return merged

    def _cut_by_time_ranges(
        self,
        video_path: Path,
        output_path: Path,
        time_ranges: List[Dict[str, float]],
    ) -> List[Dict[str, Any]]:
        """根据精确时间范围剪辑视频.

        Args:
            video_path: 输入视频路径
            output_path: 输出路径
            time_ranges: 时间范围列表 [{"start": float, "end": float}, ...]

        Returns:
            时间偏移信息列表
        """
        if not time_ranges:
            # 没有片段，复制原文件
            import shutil
            shutil.copy(video_path, output_path)
            return []

        # 切割每个片段
        clips = []
        time_offsets = []
        current_time = 0.0

        for i, time_range in enumerate(time_ranges):
            original_start = time_range.get("start", 0)
            original_end = time_range.get("end", original_start)
            segment_duration = original_end - original_start

            if segment_duration < 0.3:  # 跳过太短的片段
                continue

            clip_path = self.work_dir / f"clip_{i}.mp4"
            self.ffmpeg.cut_clip(
                video_path,
                clip_path,
                original_start,
                original_end,
            )
            clips.append(clip_path)

            time_offsets.append({
                "original_start": original_start,
                "original_end": original_end,
                "new_start": current_time,
                "new_end": current_time + segment_duration,
            })
            
            print(f"     片段{i+1}: {original_start:.1f}s - {original_end:.1f}s (新位置: {current_time:.1f}s - {current_time + segment_duration:.1f}s)")
            
            current_time += segment_duration

        # 拼接片段
        if len(clips) > 1:
            clip_paths: List[Union[str, Path]] = [str(c) for c in clips]
            self.ffmpeg.concatenate_clips(clip_paths, output_path)
        elif len(clips) == 1:
            import shutil
            shutil.copy(clips[0], output_path)
        else:
            # 没有有效片段，复制原文件
            import shutil
            shutil.copy(video_path, output_path)
            return []
        
        return time_offsets

    def _cut_by_segments(
        self,
        video_path: Path,
        output_path: Path,
        segments: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """根据语义段落剪辑视频.

        Args:
            video_path: 输入视频路径
            output_path: 输出路径
            segments: 保留的段落列表

        Returns:
            时间偏移信息列表
        """
        if not segments:
            # 没有段落，复制原文件
            import shutil
            shutil.copy(video_path, output_path)
            return []

        # 切割每个段落
        clips = []
        time_offsets = []
        current_time = 0.0

        for i, seg in enumerate(segments):
            original_start = seg.get("start_time", 0)
            original_end = seg.get("end_time", original_start)
            segment_duration = original_end - original_start

            clip_path = self.work_dir / f"segment_{i}.mp4"
            self.ffmpeg.cut_clip(
                video_path,
                clip_path,
                original_start,
                original_end,
            )
            clips.append(clip_path)

            time_offsets.append({
                "original_start": original_start,
                "original_end": original_end,
                "new_start": current_time,
                "new_end": current_time + segment_duration,
            })
            
            print(f"     片段{i+1}: {original_start:.1f}s - {original_end:.1f}s (新位置: {current_time:.1f}s - {current_time + segment_duration:.1f}s)")
            
            current_time += segment_duration

        # 拼接片段
        if len(clips) > 1:
            clip_paths: List[Union[str, Path]] = [str(c) for c in clips]
            self.ffmpeg.concatenate_clips(clip_paths, output_path)
        elif len(clips) == 1:
            import shutil
            shutil.copy(clips[0], output_path)
        else:
            # 没有有效片段，复制原文件
            import shutil
            shutil.copy(video_path, output_path)
            return []
        
        return time_offsets

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

    def _generate_subtitles_for_segments(
        self,
        transcript: Dict,
        segment_time_offsets: List[Dict[str, Any]],
        max_chars_per_line: int = 20,
        aspect_ratio: str = "16:9",
        use_llm: bool = True,
    ) -> Optional[Path]:
        """根据剪辑后的段落生成调整过时间戳的SRT字幕文件.
        
        支持使用LLM智能断句，生成语义完整的字幕。
        
        Args:
            transcript: 原始转录结果
            segment_time_offsets: 时间偏移信息列表
            max_chars_per_line: 每行最大字数
            aspect_ratio: 视频比例，"16:9" 或 "9:16"
            use_llm: 是否使用LLM优化断句
            
        Returns:
            SRT字幕文件路径或None
        """
        srt_path = self.work_dir / "temp_subtitles_adjusted.srt"
        
        try:
            # 收集所有选中的词
            all_selected_words = []
            
            for seg in transcript.get("segments", []):
                seg_start = seg.get("start", 0)
                seg_end = seg.get("end", 0)
                words = seg.get("words", [])
                
                if not words:
                    continue
                
                # 检查这个句子是否与任何剪辑片段有重叠
                for offset in segment_time_offsets:
                    clip_start = offset["original_start"]
                    clip_end = offset["original_end"]
                    time_shift = offset["new_start"] - clip_start
                    
                    # 计算交集
                    intersect_start = max(seg_start, clip_start)
                    intersect_end = min(seg_end, clip_end)
                    
                    # 有有效交集
                    if intersect_start < intersect_end:
                        # 收集在交集范围内的词，并调整时间戳
                        for word in words:
                            word_start = word.get("begin_time", 0) / 1000.0
                            word_end = word.get("end_time", 0) / 1000.0
                            
                            # 检查这个词是否在交集内
                            if word_start < intersect_end and word_end > intersect_start:
                                # 调整时间戳到新视频时间轴
                                new_begin = int((max(word_start, intersect_start) + time_shift) * 1000)
                                new_end = int((min(word_end, intersect_end) + time_shift) * 1000)
                                
                                all_selected_words.append({
                                    "text": word.get("text", ""),
                                    "punctuation": word.get("punctuation", ""),
                                    "begin_time": new_begin,
                                    "end_time": new_end,
                                })
            
            if not all_selected_words:
                print(f"   ⚠️ 没有匹配到字幕词")
                return None
            
            # 按时间排序
            all_selected_words.sort(key=lambda x: x["begin_time"])
            
            # 使用LLM优化断句
            if use_llm:
                client = self._get_aliyun_client()
                if client:
                    try:
                        print(f"   使用LLM优化字幕断句（{len(all_selected_words)}个词）...")
                        subtitle_entries = client.optimize_subtitles(
                            all_selected_words,
                            max_chars_per_line=max_chars_per_line,
                            aspect_ratio=aspect_ratio,
                        )
                        print(f"   LLM优化完成，生成{len(subtitle_entries)}条字幕")
                    except Exception as e:
                        print(f"   ⚠️ LLM优化失败: {e}，使用回退方案")
                        subtitle_entries = self._fallback_subtitle_split(
                            all_selected_words, max_chars_per_line
                        )
                else:
                    print(f"   ⚠️ 阿里云客户端未初始化，使用回退方案")
                    subtitle_entries = self._fallback_subtitle_split(
                        all_selected_words, max_chars_per_line
                    )
            else:
                subtitle_entries = self._fallback_subtitle_split(
                    all_selected_words, max_chars_per_line
                )
            
            if not subtitle_entries:
                print(f"   ⚠️ 没有生成字幕条目")
                return None
            
            # 写入SRT文件
            with open(srt_path, "w", encoding="utf-8") as f:
                for i, entry in enumerate(subtitle_entries, 1):
                    start = self._seconds_to_srt_time(entry["start"])
                    end = self._seconds_to_srt_time(entry["end"])
                    f.write(f"{i}\n")
                    f.write(f"{start} --> {end}\n")
                    f.write(f"{entry['text']}\n\n")
            
            print(f"   字幕文件: {srt_path}")
            return srt_path
            
        except Exception as e:
            print(f"⚠️  字幕生成失败: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _fallback_subtitle_split(
        self,
        words: List[Dict[str, Any]],
        max_chars: int = 20,
    ) -> List[Dict[str, Any]]:
        """回退方案：简单按字数和标点合并词。"""
        import re
        
        subtitles = []
        current_text = ""
        current_start = None
        current_end = None
        
        for word in words:
            text = word.get("text", "")
            punct = word.get("punctuation", "")
            begin = word.get("begin_time", 0) / 1000.0
            end = word.get("end_time", 0) / 1000.0
            
            if current_start is None:
                current_start = begin
            
            # 检查加入这个词后是否超限
            candidate = current_text + text + punct
            
            # 如果超限且当前不为空，保存当前行
            if len(candidate) > max_chars and current_text:
                subtitles.append({
                    "text": current_text,
                    "start": current_start,
                    "end": current_end,
                })
                # 开始新行
                current_text = text + punct
                current_start = begin
                current_end = end
            else:
                current_text = candidate
                current_end = end
            
            # 如果遇到句末标点且当前行足够长，结束当前行
            if punct in "。？！" and len(current_text) >= max_chars * 0.5:
                subtitles.append({
                    "text": current_text,
                    "start": current_start,
                    "end": current_end,
                })
                current_text = ""
                current_start = None
                current_end = None
        
        # 添加最后一行
        if current_text:
            subtitles.append({
                "text": current_text,
                "start": current_start,
                "end": current_end,
            })
        
        return subtitles

    @staticmethod
    def _seconds_to_srt_time(seconds: float) -> str:
        """Convert seconds to SRT time format (HH:MM:SS,mmm)."""
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
