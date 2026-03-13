"""AutoEditor - 一键智能剪辑器 (Phase 1 简化版)."""

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Union

from video_cut_skill.ai.scene_detector import SceneDetectionResult, SceneDetector
from video_cut_skill.ai.transcriber import Transcriber, TranscriptResult
from video_cut_skill.core.ffmpeg_wrapper import FFmpegWrapper


@dataclass
class EditConfig:
    """编辑配置."""
    target_duration: Optional[float] = None
    aspect_ratio: str = "original"
    add_subtitles: bool = True
    output_path: Optional[str] = None
    whisper_model: str = "base"  # tiny/base/small/medium/large/turbo


@dataclass
class EditResult:
    """编辑结果."""
    output_path: Path
    transcript: Optional[TranscriptResult] = None
    scenes: Optional[SceneDetectionResult] = None


class AutoEditor:
    """一键智能视频剪辑器 (Phase 1).

    当前功能：
    - 视频剪辑和拼接
    - 语音识别和字幕生成
    - 场景检测和分割

    Example:
        >>> editor = AutoEditor()
        >>> result = editor.process_video(
        ...     video_path="input.mp4",
        ...     config=EditConfig(
        ...         target_duration=60,
        ...         aspect_ratio="9:16",
        ...     )
        ... )
    """

    def __init__(
        self,
        ffmpeg: Optional[FFmpegWrapper] = None,
        transcriber: Optional[Transcriber] = None,
        scene_detector: Optional[SceneDetector] = None,
    ):
        """初始化 AutoEditor.

        Args:
            ffmpeg: FFmpeg 封装实例
            transcriber: 语音识别器实例
            scene_detector: 场景检测器实例
        """
        self.ffmpeg = ffmpeg or FFmpegWrapper()
        self.transcriber = transcriber
        self.scene_detector = scene_detector or SceneDetector()

    def process_video(
        self,
        video_path: Union[str, Path],
        config: EditConfig,
    ) -> EditResult:
        """处理视频.

        Args:
            video_path: 输入视频路径
            config: 编辑配置

        Returns:
            EditResult: 处理结果
        """
        video_path = Path(video_path)
        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")

        print(f"🎬 Processing video: {video_path}")

        # 1. 获取视频信息
        print("\n1️⃣  Getting video info...")
        info = self.ffmpeg.get_video_info(video_path)
        print(f"   Duration: {info['duration']:.1f}s")
        print(f"   Resolution: {info['width']}x{info['height']}")

        # 2. 语音识别（如果启用）
        transcript = None
        if config.add_subtitles:
            print("\n2️⃣  Transcribing audio...")
            if self.transcriber is None:
                self.transcriber = Transcriber(model_size=config.whisper_model)
            transcript = self.transcriber.transcribe(video_path)
            print(f"   Language: {transcript.language}")
            print(f"   Segments: {len(transcript.segments)}")

        # 3. 场景检测
        print("\n3️⃣  Detecting scenes...")
        scenes = self.scene_detector.detect(video_path)
        print(f"   Found {scenes.scene_count} scenes")

        # 4. 生成输出路径
        if config.output_path:
            output_path = Path(config.output_path)
        else:
            output_path = video_path.parent / f"{video_path.stem}_processed{video_path.suffix}"

        # 5. 如果指定了目标时长，进行剪辑
        if config.target_duration and config.target_duration < info['duration']:
            print(f"\n4️⃣  Cutting to {config.target_duration}s...")
            self.ffmpeg.cut_clip(
                video_path,
                output_path,
                start_time=0,
                end_time=config.target_duration,
            )
        else:
            # 复制原文件
            import shutil
            shutil.copy(video_path, output_path)

        # 6. 添加字幕（如果有）
        if transcript and config.add_subtitles:
            print("\n5️⃣  Adding subtitles...")
            srt_path = output_path.parent / f"{output_path.stem}.srt"
            self.transcriber.export_srt(transcript, srt_path)

            # 烧录字幕到视频
            subtitled_path = output_path.parent / f"{output_path.stem}_subtitled{output_path.suffix}"
            self.ffmpeg.add_subtitle(output_path, srt_path, subtitled_path)
            output_path = subtitled_path

        print(f"\n✅ Done! Output: {output_path}")

        return EditResult(
            output_path=output_path,
            transcript=transcript,
            scenes=scenes,
        )

    def cut_by_scenes(
        self,
        video_path: Union[str, Path],
        output_dir: Union[str, Path],
        min_scene_duration: float = 1.0,
    ) -> List[Path]:
        """按场景切割视频.

        Args:
            video_path: 输入视频路径
            output_dir: 输出目录
            min_scene_duration: 最小场景时长

        Returns:
            切割后的视频路径列表
        """
        video_path = Path(video_path)
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        print(f"🎬 Cutting video by scenes: {video_path}")

        # 检测场景
        scenes = self.scene_detector.detect(
            video_path,
            min_scene_len=min_scene_duration,
        )

        print(f"Found {scenes.scene_count} scenes, cutting...")

        # 切割视频
        output_files = self.scene_detector.split_video(
            video_path,
            scenes.scenes,
            output_dir,
            filename_template="scene_{:03d}.mp4",
        )

        print(f"✅ Cut into {len(output_files)} clips")
        return output_files

    def extract_highlights(
        self,
        video_path: Union[str, Path],
        keywords: List[str],
        output_path: Union[str, Path],
        context_seconds: float = 2.0,
        whisper_model: str = "base",
    ) -> Path:
        """提取关键词精彩片段.

        Args:
            video_path: 输入视频路径
            keywords: 关键词列表
            output_path: 输出路径
            context_seconds: 上下文时间（秒）
            whisper_model: Whisper模型 (tiny/base/small/medium/large/turbo)

        Returns:
            输出视频路径
        """
        video_path = Path(video_path)

        print(f"🎬 Extracting highlights from: {video_path}")
        print(f"Keywords: {keywords}")

        # 语音识别
        if self.transcriber is None:
            self.transcriber = Transcriber(model_size=whisper_model)

        transcript = self.transcriber.transcribe(video_path)

        # 检测关键词
        matches = self.transcriber.detect_keywords(
            transcript,
            keywords,
            context_seconds=context_seconds,
        )

        if not matches:
            print("⚠️  No keywords found")
            return video_path

        print(f"Found {len(matches)} keyword matches")

        # 剪辑片段
        clips = []
        temp_dir = Path("/tmp/video_cut_skill")
        temp_dir.mkdir(exist_ok=True)

        for i, match in enumerate(matches):
            clip_path = temp_dir / f"highlight_{i:03d}.mp4"
            self.ffmpeg.cut_clip(
                video_path,
                clip_path,
                start_time=match["start"],
                end_time=match["end"],
            )
            clips.append(clip_path)

        # 拼接片段
        if len(clips) > 1:
            self.ffmpeg.concatenate_clips(clips, output_path)
        else:
            import shutil
            shutil.copy(clips[0], output_path)

        print(f"✅ Highlights saved: {output_path}")
        return Path(output_path)
