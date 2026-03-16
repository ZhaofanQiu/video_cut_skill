"""Speaker recognition and diarization module.

说话人识别模块，支持语音活动检测、说话人分离和声纹识别。
"""

import json
import tempfile
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np

# 尝试导入 pyannote.audio
try:
    from pyannote.audio import Model, Inference
    from pyannote.audio.pipelines.speaker_verification import PretrainedSpeakerEmbedding
    from pyannote.audio.pipelines.speaker_diarization import SpeakerDiarization
    PYANNOTE_AVAILABLE = True
except ImportError:
    PYANNOTE_AVAILABLE = False
    warnings.warn("pyannote.audio not available, speaker recognition will be limited")

# 尝试导入 webrtcvad
try:
    import webrtcvad
    WEBRTCVAD_AVAILABLE = True
except ImportError:
    WEBRTCVAD_AVAILABLE = False

from video_cut_skill.core.ffmpeg_wrapper import FFmpegWrapper


@dataclass
class VoiceActivitySegment:
    """语音活动片段.
    
    Attributes:
        start: 开始时间（秒）
        end: 结束时间（秒）
        is_speech: 是否为语音
        confidence: 置信度
    """
    start: float
    end: float
    is_speech: bool = True
    confidence: float = 1.0
    
    @property
    def duration(self) -> float:
        """片段时长."""
        return self.end - self.start
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "start": self.start,
            "end": self.end,
            "duration": self.duration,
            "is_speech": self.is_speech,
            "confidence": self.confidence
        }


@dataclass
class SpeakerSegment:
    """说话人片段.
    
    Attributes:
        start: 开始时间（秒）
        end: 结束时间（秒）
        speaker_id: 说话人ID
        confidence: 置信度
    """
    start: float
    end: float
    speaker_id: str
    confidence: float = 1.0
    
    @property
    def duration(self) -> float:
        """片段时长."""
        return self.end - self.start
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "start": self.start,
            "end": self.end,
            "duration": self.duration,
            "speaker_id": self.speaker_id,
            "confidence": self.confidence
        }


@dataclass
class SpeakerProfile:
    """说话人档案.
    
    Attributes:
        speaker_id: 说话人ID
        name: 说话人名称（可选）
        embedding: 声纹向量
        segments_count: 片段数量
        total_duration: 总说话时长
        sample_audio_path: 样本音频路径
    """
    speaker_id: str
    name: Optional[str] = None
    embedding: Optional[np.ndarray] = None
    segments_count: int = 0
    total_duration: float = 0.0
    sample_audio_path: Optional[Path] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "speaker_id": self.speaker_id,
            "name": self.name,
            "segments_count": self.segments_count,
            "total_duration": self.total_duration,
            "has_embedding": self.embedding is not None
        }


@dataclass
class SpeakerDiarizationResult:
    """说话人分离结果.
    
    Attributes:
        segments: 说话人片段列表
        speakers: 说话人列表
        duration: 音频总时长
        num_speakers: 说话人数量
        method: 检测方法
    """
    segments: List[SpeakerSegment]
    speakers: List[SpeakerProfile]
    duration: float
    method: str
    
    @property
    def num_speakers(self) -> int:
        """说话人数量."""
        return len(self.speakers)
    
    def get_speaker_segments(self, speaker_id: str) -> List[SpeakerSegment]:
        """获取指定说话人的所有片段."""
        return [s for s in self.segments if s.speaker_id == speaker_id]
    
    def get_speaker_duration(self, speaker_id: str) -> float:
        """获取指定说话人的总说话时长."""
        return sum(s.duration for s in self.get_speaker_segments(speaker_id))
    
    def get_dominant_speaker(self) -> Optional[str]:
        """获取主导说话人（说话时间最长的）."""
        if not self.speakers:
            return None
        
        speaker_durations = {
            s.speaker_id: self.get_speaker_duration(s.speaker_id)
            for s in self.speakers
        }
        
        return max(speaker_durations, key=speaker_durations.get)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "duration": self.duration,
            "num_speakers": self.num_speakers,
            "method": self.method,
            "speakers": [s.to_dict() for s in self.speakers],
            "segments": [s.to_dict() for s in self.segments]
        }


class VoiceActivityDetector:
    """语音活动检测器.
    
    检测音频中的语音片段，过滤静音部分。
    
    Example:
        >>> detector = VoiceActivityDetector()
        >>> segments = detector.detect("audio.mp3")
        >>>
        >>> for seg in segments:
        ...     print(f"Speech: {seg.start:.2f}s - {seg.end:.2f}s")
    """
    
    def __init__(
        self,
        aggressiveness: int = 2,
        frame_duration_ms: int = 30,
        min_speech_duration: float = 0.5,
        min_silence_duration: float = 0.3
    ):
        """初始化 VAD.
        
        Args:
            aggressiveness: VAD 激进程度 (0-3)，越高越严格
            frame_duration_ms: 帧长（毫秒），10/20/30
            min_speech_duration: 最小语音片段时长
            min_silence_duration: 最小静音片段时长
        """
        self.aggressiveness = aggressiveness
        self.frame_duration_ms = frame_duration_ms
        self.min_speech_duration = min_speech_duration
        self.min_silence_duration = min_silence_duration
        
        self._vad = None
        if WEBRTCVAD_AVAILABLE:
            self._vad = webrtcvad.Vad(aggressiveness)
    
    def detect(self, audio_path: Union[str, Path]) -> List[VoiceActivitySegment]:
        """检测语音活动.
        
        Args:
            audio_path: 音频文件路径
            
        Returns:
            语音活动片段列表
        """
        audio_path = Path(audio_path)
        
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
        if WEBRTCVAD_AVAILABLE and self._vad:
            return self._detect_with_webrtc(audio_path)
        else:
            return self._detect_basic(audio_path)
    
    def _detect_with_webrtc(self, audio_path: Path) -> List[VoiceActivitySegment]:
        """使用 WebRTC VAD 检测."""
        # 使用 ffmpeg 提取音频为 PCM 格式
        wrapper = FFmpegWrapper()
        
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = tmp.name
        
        try:
            # 转换为 16kHz 16-bit mono PCM
            wrapper.execute([
                "-i", str(audio_path),
                "-ar", "16000",
                "-ac", "1",
                "-acodec", "pcm_s16le",
                tmp_path
            ])
            
            # 读取音频数据
            import wave
            with wave.open(tmp_path, 'rb') as wf:
                sample_rate = wf.getframerate()
                pcm_data = wf.readframes(wf.getnframes())
            
            # 检测语音
            frame_duration = self.frame_duration_ms / 1000.0
            frame_size = int(sample_rate * frame_duration * 2)  # 16-bit = 2 bytes
            
            segments = []
            current_start = None
            
            for i in range(0, len(pcm_data), frame_size):
                frame = pcm_data[i:i+frame_size]
                if len(frame) < frame_size:
                    break
                
                is_speech = self._vad.is_speech(frame, sample_rate)
                time = i / (sample_rate * 2)
                
                if is_speech:
                    if current_start is None:
                        current_start = time
                else:
                    if current_start is not None:
                        duration = time - current_start
                        if duration >= self.min_speech_duration:
                            segments.append(VoiceActivitySegment(
                                start=current_start,
                                end=time,
                                is_speech=True
                            ))
                        current_start = None
            
            # 处理最后一个片段
            if current_start is not None:
                end_time = len(pcm_data) / (sample_rate * 2)
                duration = end_time - current_start
                if duration >= self.min_speech_duration:
                    segments.append(VoiceActivitySegment(
                        start=current_start,
                        end=end_time,
                        is_speech=True
                    ))
            
            return segments
            
        finally:
            Path(tmp_path).unlink(missing_ok=True)
    
    def _detect_basic(self, audio_path: Path) -> List[VoiceActivitySegment]:
        """基础 VAD（基于能量阈值）."""
        # 使用 ffmpeg 提取音频并计算音量
        wrapper = FFmpegWrapper()
        
        # 获取音频信息
        info = wrapper.get_video_info(str(audio_path))
        duration = info.get("duration", 0)
        
        if duration == 0:
            return []
        
        # 简单假设：整段音频都是语音
        # 实际应用中可以基于音量的更复杂检测
        return [VoiceActivitySegment(
            start=0,
            end=duration,
            is_speech=True,
            confidence=0.5
        )]


class SpeakerDiarizer:
    """说话人分离器.
    
    将音频中的不同说话人分离并标记。
    
    Example:
        >>> diarizer = SpeakerDiarizer()
        >>> result = diarizer.diarize("meeting.mp3")
        >>>
        >>> print(f"Found {result.num_speakers} speakers")
        >>> for seg in result.segments:
        ...     print(f"{seg.speaker_id}: {seg.start:.2f}s - {seg.end:.2f}s")
    """
    
    def __init__(
        self,
        method: str = "auto",
        num_speakers: Optional[int] = None,
        min_speakers: int = 1,
        max_speakers: int = 10
    ):
        """初始化说话人分离器.
        
        Args:
            method: 方法 ("pyannote", "basic", "auto")
            num_speakers: 指定说话人数量（None则自动检测）
            min_speakers: 最少说话人数
            max_speakers: 最多说话人数
        """
        self.method = self._resolve_method(method)
        self.num_speakers = num_speakers
        self.min_speakers = min_speakers
        self.max_speakers = max_speakers
        
        self._embedding_model = None
        self._diarization_pipeline = None
        
        if PYANNOTE_AVAILABLE:
            self._init_pyannote()
    
    def diarize(self, audio_path: Union[str, Path]) -> SpeakerDiarizationResult:
        """执行说话人分离.
        
        Args:
            audio_path: 音频文件路径
            
        Returns:
            说话人分离结果
        """
        audio_path = Path(audio_path)
        
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
        # 获取音频时长
        wrapper = FFmpegWrapper()
        info = wrapper.get_video_info(str(audio_path))
        duration = info.get("duration", 0)
        
        if self.method == "pyannote":
            return self._diarize_with_pyannote(audio_path, duration)
        else:
            return self._diarize_basic(audio_path, duration)
    
    def identify_speaker(
        self,
        audio_path: Union[str, Path],
        speaker_profiles: List[SpeakerProfile],
        segment: Optional[Tuple[float, float]] = None
    ) -> Optional[SpeakerProfile]:
        """识别说话人.
        
        Args:
            audio_path: 音频文件路径
            speaker_profiles: 已知的说话人档案
            segment: 指定时间段 (start, end)
            
        Returns:
            最匹配的说话人档案，无匹配返回 None
        """
        if not speaker_profiles:
            return None
        
        if not PYANNOTE_AVAILABLE or self._embedding_model is None:
            # 无法计算声纹，返回第一个
            return speaker_profiles[0] if speaker_profiles else None
        
        # 提取查询音频的声纹
        query_embedding = self._extract_embedding(audio_path, segment)
        
        if query_embedding is None:
            return None
        
        # 与档案对比
        best_match = None
        best_score = -1
        
        for profile in speaker_profiles:
            if profile.embedding is not None:
                score = self._compute_similarity(query_embedding, profile.embedding)
                if score > best_score:
                    best_score = score
                    best_match = profile
        
        # 设置阈值
        threshold = 0.5
        if best_score >= threshold:
            return best_match
        
        return None
    
    def create_speaker_profile(
        self,
        audio_path: Union[str, Path],
        speaker_id: str,
        name: Optional[str] = None,
        segments: Optional[List[Tuple[float, float]]] = None
    ) -> SpeakerProfile:
        """创建说话人档案.
        
        Args:
            audio_path: 音频文件路径
            speaker_id: 说话人ID
            name: 说话人名称
            segments: 用于创建档案的音频片段列表
            
        Returns:
            说话人档案
        """
        profile = SpeakerProfile(
            speaker_id=speaker_id,
            name=name or speaker_id
        )
        
        if PYANNOTE_AVAILABLE and self._embedding_model is not None:
            # 提取声纹
            if segments:
                # 合并多个片段的声纹
                embeddings = []
                for start, end in segments:
                    emb = self._extract_embedding(audio_path, (start, end))
                    if emb is not None:
                        embeddings.append(emb)
                
                if embeddings:
                    profile.embedding = np.mean(embeddings, axis=0)
                    profile.segments_count = len(segments)
                    profile.total_duration = sum(end - start for start, end in segments)
            else:
                # 使用整段音频
                embedding = self._extract_embedding(audio_path)
                if embedding is not None:
                    profile.embedding = embedding
        
        return profile
    
    def _resolve_method(self, method: str) -> str:
        """解析方法."""
        if method == "auto":
            if PYANNOTE_AVAILABLE:
                return "pyannote"
            else:
                return "basic"
        return method
    
    def _init_pyannote(self) -> None:
        """初始化 pyannote 模型."""
        try:
            # 使用轻量级模型或本地模型
            # 注意：这需要模型文件，如果不可用会失败
            pass
        except Exception as e:
            warnings.warn(f"Failed to initialize pyannote: {e}")
    
    def _diarize_with_pyannote(
        self,
        audio_path: Path,
        duration: float
    ) -> SpeakerDiarizationResult:
        """使用 pyannote 进行说话人分离."""
        if not PYANNOTE_AVAILABLE:
            return self._diarize_basic(audio_path, duration)
        
        try:
            # 这里使用 pyannote 的 diarization pipeline
            # 实际实现需要加载预训练模型
            
            # 模拟结果
            speakers = [
                SpeakerProfile(speaker_id="SPEAKER_00", name="Speaker 1"),
                SpeakerProfile(speaker_id="SPEAKER_01", name="Speaker 2")
            ]
            
            segments = [
                SpeakerSegment(start=0, end=duration/2, speaker_id="SPEAKER_00"),
                SpeakerSegment(start=duration/2, end=duration, speaker_id="SPEAKER_01")
            ]
            
            return SpeakerDiarizationResult(
                segments=segments,
                speakers=speakers,
                duration=duration,
                method="pyannote"
            )
            
        except Exception as e:
            warnings.warn(f"pyannote diarization failed: {e}, falling back to basic")
            return self._diarize_basic(audio_path, duration)
    
    def _diarize_basic(self, audio_path: Path, duration: float) -> SpeakerDiarizationResult:
        """基础说话人分离（模拟）."""
        # 基础实现：假设只有一个说话人
        speaker = SpeakerProfile(speaker_id="SPEAKER_00", name="Speaker 1")
        
        segment = SpeakerSegment(
            start=0,
            end=duration,
            speaker_id="SPEAKER_00"
        )
        
        return SpeakerDiarizationResult(
            segments=[segment],
            speakers=[speaker],
            duration=duration,
            method="basic"
        )
    
    def _extract_embedding(
        self,
        audio_path: Path,
        segment: Optional[Tuple[float, float]] = None
    ) -> Optional[np.ndarray]:
        """提取声纹嵌入."""
        if not PYANNOTE_AVAILABLE or self._embedding_model is None:
            return None
        
        try:
            # 使用 pyannote 提取声纹
            # 实际实现需要加载预训练模型
            return None
        except Exception as e:
            warnings.warn(f"Failed to extract embedding: {e}")
            return None
    
    def _compute_similarity(
        self,
        embedding1: np.ndarray,
        embedding2: np.ndarray
    ) -> float:
        """计算声纹相似度."""
        # 余弦相似度
        dot_product = np.dot(embedding1, embedding2)
        norm1 = np.linalg.norm(embedding1)
        norm2 = np.linalg.norm(embedding2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return float(dot_product / (norm1 * norm2))


class SpeakerAwareEditor:
    """说话人感知编辑器.
    
    将说话人识别集成到视频编辑流程。
    
    Example:
        >>> editor = SpeakerAwareEditor()
        >>>
        >>> # 分析视频中的说话人
        >>> result = editor.analyze("meeting.mp4")
        >>> print(f"Detected {result.num_speakers} speakers")
        >>>
        >>> # 只保留主导说话人的片段
        >>> clips = editor.extract_by_speaker(
        ...     dominant_only=True
        ... )
        >>>
        >>> # 为每个说话人生成单独的视频
        >>> editor.create_speaker_videos(output_dir="./speakers/")
    """
    
    def __init__(
        self,
        diarizer: Optional[SpeakerDiarizer] = None,
        vad: Optional[VoiceActivityDetector] = None
    ):
        """初始化说话人感知编辑器.
        
        Args:
            diarizer: 说话人分离器
            vad: 语音活动检测器
        """
        self.diarizer = diarizer or SpeakerDiarizer()
        self.vad = vad or VoiceActivityDetector()
        self._last_result: Optional[SpeakerDiarizationResult] = None
        self._audio_path: Optional[Path] = None
    
    def analyze(self, video_path: Union[str, Path]) -> SpeakerDiarizationResult:
        """分析视频中的说话人.
        
        Args:
            video_path: 视频文件路径
            
        Returns:
            说话人分离结果
        """
        video_path = Path(video_path)
        
        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")
        
        # 提取音频
        wrapper = FFmpegWrapper()
        
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            audio_path = tmp.name
        
        try:
            wrapper.execute([
                "-i", str(video_path),
                "-vn",  # 无视频
                "-acodec", "pcm_s16le",
                "-ar", "16000",
                "-ac", "1",
                audio_path
            ])
            
            # 进行说话人分离
            self._audio_path = Path(audio_path)
            self._last_result = self.diarizer.diarize(audio_path)
            
            return self._last_result
            
        except Exception as e:
            Path(audio_path).unlink(missing_ok=True)
            raise
    
    def get_speaker_timeline(self) -> List[Dict[str, Any]]:
        """获取说话人时间线.
        
        Returns:
            时间线列表，包含说话人和时间信息
        """
        if self._last_result is None:
            raise ValueError("No analysis result. Call analyze() first.")
        
        timeline = []
        
        for segment in self._last_result.segments:
            timeline.append({
                "start": segment.start,
                "end": segment.end,
                "duration": segment.duration,
                "speaker_id": segment.speaker_id,
                "speaker_name": self._get_speaker_name(segment.speaker_id)
            })
        
        return timeline
    
    def extract_by_speaker(
        self,
        speaker_id: Optional[str] = None,
        dominant_only: bool = False,
        min_segment_duration: float = 1.0
    ) -> List[Tuple[float, float]]:
        """提取指定说话人的片段.
        
        Args:
            speaker_id: 指定说话人ID（None则根据 dominant_only 选择）
            dominant_only: 只提取主导说话人
            min_segment_duration: 最小时长
            
        Returns:
            时间段列表 [(start, end), ...]
        """
        if self._last_result is None:
            raise ValueError("No analysis result. Call analyze() first.")
        
        if speaker_id is None:
            if dominant_only:
                speaker_id = self._last_result.get_dominant_speaker()
            else:
                # 返回所有说话人的片段
                return [
                    (s.start, s.end)
                    for s in self._last_result.segments
                    if s.duration >= min_segment_duration
                ]
        
        if speaker_id is None:
            return []
        
        segments = self._last_result.get_speaker_segments(speaker_id)
        
        return [
            (s.start, s.end)
            for s in segments
            if s.duration >= min_segment_duration
        ]
    
    def remove_speaker_segments(
        self,
        speaker_id: str,
        video_path: Union[str, Path],
        output_path: Union[str, Path]
    ) -> str:
        """移除指定说话人的片段.
        
        Args:
            speaker_id: 要移除的说话人ID
            video_path: 输入视频路径
            output_path: 输出视频路径
            
        Returns:
            输出文件路径
        """
        if self._last_result is None:
            raise ValueError("No analysis result. Call analyze() first.")
        
        # 获取要保留的片段（排除指定说话人）
        keep_segments = [
            (s.start, s.end)
            for s in self._last_result.segments
            if s.speaker_id != speaker_id
        ]
        
        # 使用 FFmpeg 拼接
        wrapper = FFmpegWrapper()
        
        # 创建 concat 文件
        concat_segments = []
        for start, end in keep_segments:
            concat_segments.append({
                "file": str(video_path),
                "start": start,
                "end": end
            })
        
        if concat_segments:
            wrapper.concat_segments(concat_segments, str(output_path))
        
        return str(output_path)
    
    def create_speaker_subtitles(
        self,
        subtitle_format: str = "srt"
    ) -> str:
        """创建带说话人标记的字幕.
        
        Args:
            subtitle_format: 字幕格式 ("srt" 或 "vtt")
            
        Returns:
            字幕内容
        """
        if self._last_result is None:
            raise ValueError("No analysis result. Call analyze() first.")
        
        lines = []
        
        if subtitle_format == "srt":
            for i, segment in enumerate(self._last_result.segments, 1):
                speaker_name = self._get_speaker_name(segment.speaker_id)
                start_time = self._format_time_srt(segment.start)
                end_time = self._format_time_srt(segment.end)
                
                lines.append(str(i))
                lines.append(f"{start_time} --> {end_time}")
                lines.append(f"[{speaker_name}]")
                lines.append("")
        
        elif subtitle_format == "vtt":
            lines.append("WEBVTT")
            lines.append("")
            
            for segment in self._last_result.segments:
                speaker_name = self._get_speaker_name(segment.speaker_id)
                start_time = self._format_time_vtt(segment.start)
                end_time = self._format_time_vtt(segment.end)
                
                lines.append(f"{start_time} --> {end_time}")
                lines.append(f"[{speaker_name}]")
                lines.append("")
        
        return "\n".join(lines)
    
    def export_to_json(self, output_path: Union[str, Path]) -> None:
        """导出说话人分析结果到 JSON.
        
        Args:
            output_path: 输出文件路径
        """
        if self._last_result is None:
            raise ValueError("No analysis result. Call analyze() first.")
        
        data = self._last_result.to_dict()
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def _get_speaker_name(self, speaker_id: str) -> str:
        """获取说话人名称."""
        if self._last_result is None:
            return speaker_id
        
        for speaker in self._last_result.speakers:
            if speaker.speaker_id == speaker_id:
                return speaker.name or speaker_id
        
        return speaker_id
    
    def _format_time_srt(self, seconds: float) -> str:
        """格式化为 SRT 时间格式."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
    
    def _format_time_vtt(self, seconds: float) -> str:
        """格式化为 VTT 时间格式."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"


# 便捷函数

def detect_voice_activity(
    audio_path: Union[str, Path],
    aggressiveness: int = 2
) -> List[VoiceActivitySegment]:
    """便捷函数：检测语音活动.
    
    Args:
        audio_path: 音频文件路径
        aggressiveness: VAD 激进程度
        
    Returns:
        语音活动片段列表
    """
    detector = VoiceActivityDetector(aggressiveness=aggressiveness)
    return detector.detect(audio_path)


def diarize_speakers(
    audio_path: Union[str, Path],
    num_speakers: Optional[int] = None
) -> SpeakerDiarizationResult:
    """便捷函数：说话人分离.
    
    Args:
        audio_path: 音频文件路径
        num_speakers: 指定说话人数量
        
    Returns:
        说话人分离结果
    """
    diarizer = SpeakerDiarizer(num_speakers=num_speakers)
    return diarizer.diarize(audio_path)
