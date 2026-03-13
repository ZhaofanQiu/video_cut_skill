"""Transcriber module for speech recognition using Whisper."""

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import whisper

from video_cut_skill.core.ffmpeg_wrapper import FFmpegWrapper

logger = logging.getLogger(__name__)


@dataclass
class TranscriptSegment:
    """转录片段."""

    start: float
    end: float
    text: str
    words: Optional[List[Dict[str, Any]]] = None

    @property
    def duration(self) -> float:
        """片段时长."""
        return self.end - self.start


@dataclass
class TranscriptResult:
    """转录结果."""

    text: str
    segments: List[TranscriptSegment]
    language: str
    duration: float

    def get_segment_at_time(self, time: float) -> Optional[TranscriptSegment]:
        """获取指定时间点的片段."""
        for seg in self.segments:
            if seg.start <= time <= seg.end:
                return seg
        return None

    def search_text(self, keyword: str) -> List[TranscriptSegment]:
        """搜索关键词."""
        keyword_lower = keyword.lower()
        return [seg for seg in self.segments if keyword_lower in seg.text.lower()]


class Transcriber:
    """语音识别器.

    基于 OpenAI Whisper 实现.
    """

    MODEL_SIZES = {
        "tiny": {"params": "39M", "speed": "~10x", "memory": "~1GB"},
        "base": {"params": "74M", "speed": "~7x", "memory": "~1GB"},
        "small": {"params": "244M", "speed": "~4x", "memory": "~2GB"},
        "medium": {"params": "769M", "speed": "~2x", "memory": "~5GB"},
        "large": {"params": "1550M", "speed": "1x", "memory": "~10GB"},
        "turbo": {"params": "809M", "speed": "~8x", "memory": "~6GB"},
    }

    def __init__(
        self,
        model_size: str = "base",
        device: Optional[str] = None,
        download_root: Optional[str] = None,
    ):
        """初始化语音识别器.

        Args:
            model_size: 模型大小 (tiny/base/small/medium/large/turbo)
            device: 计算设备 (cuda/cpu)，None 则自动选择
            download_root: 模型下载目录
        """
        if model_size not in self.MODEL_SIZES:
            raise ValueError(
                f"Invalid model size: {model_size}. "
                f"Choose from: {list(self.MODEL_SIZES.keys())}"
            )

        self.model_size = model_size
        self.device = device or ("cuda" if whisper.torch.cuda.is_available() else "cpu")

        logger.info(f"Loading Whisper model: {model_size} on {self.device}")

        try:
            self.model = whisper.load_model(
                model_size,
                device=self.device,
                download_root=download_root,
            )
        except Exception as e:
            logger.error(f"Failed to load Whisper model: {e}")
            raise

        self.ffmpeg = FFmpegWrapper()
        logger.info(f"Transcriber initialized with {model_size} model")

    def transcribe(
        self,
        video_path: Union[str, Path],
        language: Optional[str] = None,
        word_timestamps: bool = True,
        task: str = "transcribe",  # transcribe or translate
    ) -> TranscriptResult:
        """转录音视频.

        Args:
            video_path: 音视频文件路径
            language: 语言代码 (如 'zh', 'en')，None 则自动检测
            word_timestamps: 是否生成单词级时间戳
            task: 任务类型 (transcribe-转录, translate-翻译为英文)

        Returns:
            TranscriptResult: 转录结果
        """
        video_path = str(video_path)

        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")

        logger.info(f"Transcribing: {video_path}")

        try:
            result = self.model.transcribe(
                video_path,
                language=language,
                task=task,
                word_timestamps=word_timestamps,
                verbose=False,
            )

            # 解析结果
            segments = []
            for seg_data in result.get("segments", []):
                words = seg_data.get("words")
                if words:
                    words = [
                        {"word": w["word"], "start": w["start"], "end": w["end"]}
                        for w in words
                    ]

                segments.append(
                    TranscriptSegment(
                        start=seg_data["start"],
                        end=seg_data["end"],
                        text=seg_data["text"].strip(),
                        words=words,
                    )
                )

            transcript = TranscriptResult(
                text=result["text"].strip(),
                segments=segments,
                language=result.get("language", "unknown"),
                duration=segments[-1].end if segments else 0,
            )

            logger.info(
                f"Transcription complete: {len(segments)} segments, "
                f"language: {transcript.language}"
            )
            return transcript

        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            raise

    def export_srt(
        self,
        transcript: TranscriptResult,
        output_path: Union[str, Path],
        max_line_length: int = 40,
        max_lines: int = 2,
    ) -> Path:
        """导出 SRT 字幕文件.

        Args:
            transcript: 转录结果
            output_path: 输出路径
            max_line_length: 每行最大字符数
            max_lines: 最大行数

        Returns:
            输出文件路径
        """
        output_path = Path(output_path)

        def format_time(seconds: float) -> str:
            """格式化为 SRT 时间格式."""
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            secs = int(seconds % 60)
            millis = int((seconds % 1) * 1000)
            return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

        def split_text(text: str, max_length: int, max_lines: int) -> List[str]:
            """将文本分割为多行."""
            words = text.split()
            lines = []
            current_line = ""

            for word in words:
                if len(current_line) + len(word) + 1 <= max_length:
                    current_line = f"{current_line} {word}".strip()
                else:
                    if current_line:
                        lines.append(current_line)
                    current_line = word
                    if len(lines) >= max_lines - 1:
                        break

            if current_line and len(lines) < max_lines:
                lines.append(current_line)

            # 如果还有剩余词，添加省略号
            if len(lines) >= max_lines and current_line != lines[-1]:
                lines[-1] = lines[-1].rstrip(".") + "..."

            return lines

        with open(output_path, "w", encoding="utf-8") as f:
            for i, seg in enumerate(transcript.segments, 1):
                lines = split_text(seg.text, max_line_length, max_lines)
                text = "\n".join(lines)

                f.write(f"{i}\n")
                f.write(f"{format_time(seg.start)} --> {format_time(seg.end)}\n")
                f.write(f"{text}\n\n")

        logger.info(f"SRT subtitle exported to: {output_path}")
        return output_path

    def export_ass(
        self,
        transcript: TranscriptResult,
        output_path: Union[str, Path],
        style: Optional[Dict[str, Any]] = None,
    ) -> Path:
        """导出 ASS 字幕文件（支持高级样式）.

        Args:
            transcript: 转录结果
            output_path: 输出路径
            style: 样式配置

        Returns:
            输出文件路径
        """
        output_path = Path(output_path)

        # 默认样式
        default_style = {
            "font": "Arial",
            "fontsize": 24,
            "color": "\u0026H00FFFFFF",  # 白色
            "outline": 2,
            "outline_color": "\u0026H00000000",  # 黑色描边
            "alignment": 2,  # 底部居中
        }
        style = {**default_style, **(style or {})}

        def format_time_ass(seconds: float) -> str:
            """格式化为 ASS 时间格式."""
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            secs = int(seconds % 60)
            centis = int((seconds % 1) * 100)
            return f"{hours}:{minutes:02d}:{secs:02d}.{centis:02d}"

        with open(output_path, "w", encoding="utf-8") as f:
            # 写入头部
            f.write("[Script Info]\n")
            f.write("Title: Auto-generated Subtitles\n")
            f.write("ScriptType: v4.00+\n")
            f.write("PlayResX: 1920\n")
            f.write("PlayResY: 1080\n")
            f.write("\n")

            # 写入样式
            f.write("[V4+ Styles]\n")
            f.write("Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n")
            f.write(
                f"Style: Default,{style['font']},{style['fontsize']},{style['color']},\u0026H000000FF,{style['outline_color']},\u0026H00000000,0,0,0,0,100,100,0,0,1,{style['outline']},0,{style['alignment']},10,10,10,1\n"
            )
            f.write("\n")

            # 写入事件
            f.write("[Events]\n")
            f.write("Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")

            for seg in transcript.segments:
                start = format_time_ass(seg.start)
                end = format_time_ass(seg.end)
                text = seg.text.replace("\n", "\\N")
                f.write(f"Dialogue: 0,{start},{end},Default,,0,0,0,,{text}\n")

        logger.info(f"ASS subtitle exported to: {output_path}")
        return output_path

    def detect_keywords(
        self,
        transcript: TranscriptResult,
        keywords: List[str],
        context_seconds: float = 2.0,
    ) -> List[Dict[str, Any]]:
        """检测关键词出现位置.

        Args:
            transcript: 转录结果
            keywords: 关键词列表
            context_seconds: 上下文时间（秒）

        Returns:
            关键词出现信息列表
        """
        results = []

        for keyword in keywords:
            matches = transcript.search_text(keyword)
            for match in matches:
                results.append({
                    "keyword": keyword,
                    "start": max(0, match.start - context_seconds),
                    "end": match.end + context_seconds,
                    "text": match.text,
                    "segment": match,
                })

        # 按时间排序
        results.sort(key=lambda x: x["start"])
        return results
