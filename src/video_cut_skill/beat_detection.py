"""Beat detection and smart beat-matching for video editing.

提供音乐节拍检测、自动卡点剪辑功能。
"""

import asyncio
import json
import tempfile
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np

# 尝试导入 librosa，如果没有则使用备选方案
try:
    import librosa
    LIBROSA_AVAILABLE = True
except ImportError:
    LIBROSA_AVAILABLE = False
    warnings.warn("librosa not available, beat detection will be limited")

try:
    import madmom
    MADMOM_AVAILABLE = True
except ImportError:
    MADMOM_AVAILABLE = False

from video_cut_skill.core.ffmpeg_wrapper import FFmpegWrapper


@dataclass
class BeatInfo:
    """节拍信息.
    
    Attributes:
        time: 节拍时间（秒）
        strength: 节拍强度 (0.0 ~ 1.0)
        is_downbeat: 是否重拍
        bpm: 该节拍处的BPM
    """
    time: float
    strength: float = 1.0
    is_downbeat: bool = False
    bpm: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "time": self.time,
            "strength": self.strength,
            "is_downbeat": self.is_downbeat,
            "bpm": self.bpm
        }


@dataclass
class BeatDetectionResult:
    """节拍检测结果.
    
    Attributes:
        bpm: 整体BPM
        beats: 所有节拍列表
        downbeats: 重拍列表
        duration: 音频时长
        method: 检测方法
    """
    bpm: float
    beats: List[BeatInfo]
    downbeats: List[BeatInfo]
    duration: float
    method: str
    
    @property
    def beat_count(self) -> int:
        """总节拍数."""
        return len(self.beats)
    
    @property
    def downbeat_count(self) -> int:
        """重拍数."""
        return len(self.downbeats)
    
    def get_beats_in_range(self, start: float, end: float) -> List[BeatInfo]:
        """获取时间范围内的节拍."""
        return [b for b in self.beats if start <= b.time <= end]
    
    def get_nearest_beat(self, time: float) -> Optional[BeatInfo]:
        """获取最近的节拍."""
        if not self.beats:
            return None
        return min(self.beats, key=lambda b: abs(b.time - time))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "bpm": self.bpm,
            "beat_count": self.beat_count,
            "downbeat_count": self.downbeat_count,
            "duration": self.duration,
            "method": self.method,
            "beats": [b.to_dict() for b in self.beats[:100]],  # 限制数量
        }


@dataclass
class CutPoint:
    """剪辑点信息.
    
    Attributes:
        time: 剪辑时间点
        beat: 对应的节拍（如果有）
        confidence: 置信度 (0.0 ~ 1.0)
        reason: 选择原因
    """
    time: float
    beat: Optional[BeatInfo] = None
    confidence: float = 1.0
    reason: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "time": self.time,
            "beat": self.beat.to_dict() if self.beat else None,
            "confidence": self.confidence,
            "reason": self.reason
        }


@dataclass
class BeatMatchingResult:
    """卡点剪辑结果.
    
    Attributes:
        cut_points: 剪辑点列表
        target_duration: 目标时长
        actual_duration: 实际时长
        beat_sync_rate: 节拍同步率
    """
    cut_points: List[CutPoint]
    target_duration: float
    actual_duration: float
    beat_sync_rate: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "cut_points": [cp.to_dict() for cp in self.cut_points],
            "target_duration": self.target_duration,
            "actual_duration": self.actual_duration,
            "beat_sync_rate": self.beat_sync_rate,
            "cut_point_count": len(self.cut_points)
        }


class BeatDetector:
    """节拍检测器.
    
    检测音乐节拍，支持多种检测方法。
    
    Example:
        >>> detector = BeatDetector(method="librosa")
        >>> result = detector.detect("music.mp3")
        >>>
        >>> print(f"BPM: {result.bpm}")
        >>> print(f"Beats: {result.beat_count}")
        >>>
        >>> # 获取剪辑点
        >>> cuts = detector.generate_cuts(
        ...     target_duration=30,
        ...     align_to_beat=True
        ... )
    """
    
    def __init__(
        self,
        method: str = "auto",
        bpm_range: Tuple[int, int] = (60, 180),
        min_beat_strength: float = 0.3,
    ):
        """初始化节拍检测器.
        
        Args:
            method: 检测方法 ("librosa", "madmom", "auto")
            bpm_range: BPM范围
            min_beat_strength: 最小节拍强度
        """
        self.method = self._resolve_method(method)
        self.bpm_range = bpm_range
        self.min_beat_strength = min_beat_strength
        self._last_result: Optional[BeatDetectionResult] = None
    
    def detect(self, audio_path: Union[str, Path]) -> BeatDetectionResult:
        """检测音频节拍.
        
        Args:
            audio_path: 音频文件路径
            
        Returns:
            节拍检测结果
            
        Raises:
            FileNotFoundError: 如果音频文件不存在
            ValueError: 如果检测失败
        """
        audio_path = Path(audio_path)
        
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
        if self.method == "librosa":
            return self._detect_with_librosa(audio_path)
        elif self.method == "madmom":
            return self._detect_with_madmom(audio_path)
        else:
            return self._detect_basic(audio_path)
    
    def generate_cuts(
        self,
        audio_path: Optional[Union[str, Path]] = None,
        target_duration: float = 30.0,
        align_to_beat: bool = True,
        prefer_downbeat: bool = True,
        min_segment_duration: float = 2.0,
        max_segment_duration: float = 10.0,
        beat_result: Optional[BeatDetectionResult] = None,
    ) -> BeatMatchingResult:
        """生成卡点剪辑方案.
        
        Args:
            audio_path: 音频路径（如果未提供 beat_result）
            target_duration: 目标视频时长
            align_to_beat: 是否对齐到节拍
            prefer_downbeat: 是否优先选择重拍
            min_segment_duration: 最小片段时长
            max_segment_duration: 最大片段时长
            beat_result: 预计算的节拍结果
            
        Returns:
            卡点剪辑结果
        """
        # 获取节拍结果
        if beat_result is None:
            if audio_path is None:
                raise ValueError("Must provide audio_path or beat_result")
            beat_result = self.detect(audio_path)
        
        self._last_result = beat_result
        
        if not beat_result.beats:
            # 没有检测到节拍，使用均匀分布
            return self._generate_uniform_cuts(
                target_duration,
                beat_result.duration,
                min_segment_duration,
                max_segment_duration
            )
        
        if not align_to_beat:
            return self._generate_uniform_cuts(
                target_duration,
                beat_result.duration,
                min_segment_duration,
                max_segment_duration
            )
        
        # 基于节拍生成剪辑点
        cut_points = []
        
        # 选择剪辑点
        beats_to_use = beat_result.downbeats if prefer_downbeat and beat_result.downbeats else beat_result.beats
        
        # 过滤节拍
        filtered_beats = [
            b for b in beats_to_use
            if b.strength >= self.min_beat_strength
        ]
        
        if not filtered_beats:
            filtered_beats = beats_to_use
        
        # 计算需要的剪辑点数量
        num_cuts = int(target_duration / ((min_segment_duration + max_segment_duration) / 2))
        num_cuts = max(3, min(num_cuts, len(filtered_beats)))
        
        # 均匀选择剪辑点
        if len(filtered_beats) <= num_cuts:
            selected_beats = filtered_beats
        else:
            # 均匀采样
            indices = np.linspace(0, len(filtered_beats) - 1, num_cuts, dtype=int)
            selected_beats = [filtered_beats[i] for i in indices]
        
        for beat in selected_beats:
            cut_points.append(CutPoint(
                time=beat.time,
                beat=beat,
                confidence=beat.strength,
                reason="downbeat" if beat.is_downbeat else "beat"
            ))
        
        # 计算实际时长
        actual_duration = sum(
            cut_points[i+1].time - cut_points[i].time
            for i in range(len(cut_points) - 1)
        )
        
        # 计算节拍同步率
        beat_sync_rate = len([cp for cp in cut_points if cp.beat is not None]) / len(cut_points) if cut_points else 0
        
        return BeatMatchingResult(
            cut_points=cut_points,
            target_duration=target_duration,
            actual_duration=actual_duration,
            beat_sync_rate=beat_sync_rate
        )
    
    def get_tempo_changes(self, window_size: float = 10.0) -> List[Dict[str, Any]]:
        """获取BPM变化点.
        
        Args:
            window_size: 分析窗口大小（秒）
            
        Returns:
            BPM变化点列表
        """
        if self._last_result is None:
            raise ValueError("No beat detection result available. Call detect() first.")
        
        result = self._last_result
        changes = []
        
        if not result.beats:
            return changes
        
        # 计算每个时间点的局部BPM
        beats = result.beats
        for i, beat in enumerate(beats):
            window_start = beat.time
            window_end = beat.time + window_size
            
            # 找到窗口内的节拍
            window_beats = [b for b in beats if window_start <= b.time < window_end]
            
            if len(window_beats) >= 2:
                local_bpm = 60 * (len(window_beats) - 1) / (window_beats[-1].time - window_beats[0].time)
                
                if changes and abs(local_bpm - changes[-1]["bpm"]) > 5:
                    changes.append({
                        "time": beat.time,
                        "bpm": local_bpm,
                        "change": local_bpm - changes[-1]["bpm"]
                    })
                elif not changes:
                    changes.append({
                        "time": beat.time,
                        "bpm": local_bpm,
                        "change": 0
                    })
        
        return changes
    
    def sync_video_to_beats(
        self,
        video_segments: List[Tuple[float, float]],
        beat_result: Optional[BeatDetectionResult] = None,
        audio_path: Optional[Union[str, Path]] = None,
    ) -> List[Tuple[float, float]]:
        """将视频片段对齐到节拍.
        
        Args:
            video_segments: 视频片段列表 [(start, end), ...]
            beat_result: 节拍结果
            audio_path: 音频路径（如果未提供 beat_result）
            
        Returns:
            对齐后的片段列表
        """
        if beat_result is None:
            if audio_path is None:
                raise ValueError("Must provide audio_path or beat_result")
            beat_result = self.detect(audio_path)
        
        if not beat_result.beats:
            return video_segments
        
        aligned_segments = []
        
        for start, end in video_segments:
            # 找到最近的节拍点
            nearest_start = beat_result.get_nearest_beat(start)
            nearest_end = beat_result.get_nearest_beat(end)
            
            if nearest_start and nearest_end:
                # 对齐到节拍
                aligned_start = nearest_start.time
                aligned_end = nearest_end.time
                
                # 确保合理的时长
                min_duration = 1.0
                if aligned_end - aligned_start >= min_duration:
                    aligned_segments.append((aligned_start, aligned_end))
                else:
                    aligned_segments.append((start, end))
            else:
                aligned_segments.append((start, end))
        
        return aligned_segments
    
    def _resolve_method(self, method: str) -> str:
        """解析检测方法."""
        if method == "auto":
            if LIBROSA_AVAILABLE:
                return "librosa"
            elif MADMOM_AVAILABLE:
                return "madmom"
            else:
                return "basic"
        return method
    
    def _detect_with_librosa(self, audio_path: Path) -> BeatDetectionResult:
        """使用 librosa 检测节拍."""
        # 加载音频
        y, sr = librosa.load(str(audio_path), sr=None)
        
        # 计算时长
        duration = librosa.get_duration(y=y, sr=sr)
        
        # 估计BPM
        tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
        bpm = float(tempo) if isinstance(tempo, (int, float, np.number)) else float(tempo[0])
        
        # 转换节拍帧到时间
        beat_times = librosa.frames_to_time(beat_frames, sr=sr)
        
        # 检测重拍（使用 onset strength）
        onset_env = librosa.onset.onset_strength(y=y, sr=sr)
        
        # 创建 BeatInfo 列表
        beats = []
        for i, time in enumerate(beat_times):
            # 计算节拍强度
            frame_idx = librosa.time_to_frames(time, sr=sr)
            if frame_idx < len(onset_env):
                strength = float(onset_env[frame_idx]) / np.max(onset_env)
            else:
                strength = 0.5
            
            # 假设每4拍一个重拍
            is_downbeat = (i % 4 == 0)
            
            beats.append(BeatInfo(
                time=float(time),
                strength=strength,
                is_downbeat=is_downbeat,
                bpm=bpm
            ))
        
        # 提取重拍
        downbeats = [b for b in beats if b.is_downbeat]
        
        return BeatDetectionResult(
            bpm=bpm,
            beats=beats,
            downbeats=downbeats,
            duration=duration,
            method="librosa"
        )
    
    def _detect_with_madmom(self, audio_path: Path) -> BeatDetectionResult:
        """使用 madmom 检测节拍."""
        # madmom 实现
        # 注意：madmom 的 API 可能需要根据实际版本调整
        
        proc = madmom.features.beats.DBNBeatTrackingProcessor(
            fps=100,
            min_bpm=self.bpm_range[0],
            max_bpm=self.bpm_range[1]
        )
        act = madmom.features.beats.RNNBeatProcessor()(str(audio_path))
        beat_times = proc(act)
        
        # 计算BPM
        if len(beat_times) >= 2:
            bpm = 60 * (len(beat_times) - 1) / (beat_times[-1] - beat_times[0])
        else:
            bpm = 120.0
        
        # 获取音频时长
        from video_cut_skill.core.ffmpeg_wrapper import FFmpegWrapper
        wrapper = FFmpegWrapper()
        info = wrapper.get_video_info(str(audio_path))
        duration = info.get("duration", 0)
        
        # 创建 BeatInfo
        beats = []
        for i, time in enumerate(beat_times):
            is_downbeat = (i % 4 == 0)
            beats.append(BeatInfo(
                time=float(time),
                strength=1.0,
                is_downbeat=is_downbeat,
                bpm=bpm
            ))
        
        downbeats = [b for b in beats if b.is_downbeat]
        
        return BeatDetectionResult(
            bpm=bpm,
            beats=beats,
            downbeats=downbeats,
            duration=duration,
            method="madmom"
        )
    
    def _detect_basic(self, audio_path: Path) -> BeatDetectionResult:
        """基础节拍检测（不使用外部库）."""
        # 使用 ffmpeg 提取音频信息
        wrapper = FFmpegWrapper()
        info = wrapper.get_video_info(str(audio_path))
        duration = info.get("duration", 0)
        
        # 估算BPM（基于音频能量）
        # 这里使用简单的启发式方法
        estimated_bpm = 120.0  # 默认值
        
        # 生成均匀的"节拍"
        beat_interval = 60.0 / estimated_bpm
        num_beats = int(duration / beat_interval)
        
        beats = []
        for i in range(num_beats):
            time = i * beat_interval
            is_downbeat = (i % 4 == 0)
            beats.append(BeatInfo(
                time=time,
                strength=0.5,
                is_downbeat=is_downbeat,
                bpm=estimated_bpm
            ))
        
        downbeats = [b for b in beats if b.is_downbeat]
        
        return BeatDetectionResult(
            bpm=estimated_bpm,
            beats=beats,
            downbeats=downbeats,
            duration=duration,
            method="basic"
        )
    
    def _generate_uniform_cuts(
        self,
        target_duration: float,
        audio_duration: float,
        min_segment: float,
        max_segment: float
    ) -> BeatMatchingResult:
        """生成均匀分布的剪辑点（无节拍时回退）."""
        cut_points = []
        
        # 计算片段数量
        avg_segment = (min_segment + max_segment) / 2
        num_segments = max(3, int(target_duration / avg_segment))
        
        # 均匀分布
        segment_duration = min(audio_duration / num_segments, max_segment)
        segment_duration = max(segment_duration, min_segment)
        
        for i in range(num_segments + 1):
            time = i * segment_duration
            if time <= audio_duration:
                cut_points.append(CutPoint(
                    time=time,
                    beat=None,
                    confidence=0.5,
                    reason="uniform"
                ))
        
        actual_duration = sum(
            cut_points[i+1].time - cut_points[i].time
            for i in range(len(cut_points) - 1)
        )
        
        return BeatMatchingResult(
            cut_points=cut_points,
            target_duration=target_duration,
            actual_duration=actual_duration,
            beat_sync_rate=0.0
        )


class BeatSyncEditor:
    """节拍同步编辑器.
    
    将节拍检测集成到视频编辑流程中。
    
    Example:
        >>> editor = BeatSyncEditor()
        >>>
        >>> # 分析音频
        >>> editor.load_audio("background_music.mp3")
        >>>
        >>> # 生成卡点视频
        >>> editor.create_beat_synced_video(
        ...     video_path="input.mp4",
        ...     output_path="output.mp4",
        ...     target_duration=30
        ... )
    """
    
    def __init__(self, detector: Optional[BeatDetector] = None):
        """初始化节拍同步编辑器.
        
        Args:
            detector: 节拍检测器实例
        """
        self.detector = detector or BeatDetector()
        self.beat_result: Optional[BeatDetectionResult] = None
        self.audio_path: Optional[Path] = None
    
    def load_audio(self, audio_path: Union[str, Path]) -> BeatDetectionResult:
        """加载并分析音频.
        
        Args:
            audio_path: 音频文件路径
            
        Returns:
            节拍检测结果
        """
        self.audio_path = Path(audio_path)
        self.beat_result = self.detector.detect(self.audio_path)
        return self.beat_result
    
    def create_beat_cut_strategy(
        self,
        target_duration: float = 30.0,
        cut_on_downbeat: bool = True,
        min_clip_duration: float = 2.0,
        max_clip_duration: float = 5.0,
    ) -> BeatMatchingResult:
        """创建基于节拍的剪辑策略.
        
        Args:
            target_duration: 目标视频时长
            cut_on_downbeat: 是否只在重拍处剪辑
            min_clip_duration: 最小片段时长
            max_clip_duration: 最大片段时长
            
        Returns:
            卡点剪辑结果
        """
        if self.beat_result is None:
            raise ValueError("No audio loaded. Call load_audio() first.")
        
        return self.detector.generate_cuts(
            beat_result=self.beat_result,
            target_duration=target_duration,
            align_to_beat=True,
            prefer_downbeat=cut_on_downbeat,
            min_segment_duration=min_clip_duration,
            max_segment_duration=max_clip_duration,
        )
    
    def suggest_b_roll_insertion_points(
        self,
        min_interval: float = 5.0
    ) -> List[Dict[str, Any]]:
        """建议 B-roll 插入点.
        
        在节拍的弱拍位置建议插入 B-roll。
        
        Args:
            min_interval: 最小间隔（秒）
            
        Returns:
            插入点列表
        """
        if self.beat_result is None:
            raise ValueError("No audio loaded. Call load_audio() first.")
        
        suggestions = []
        last_time = 0
        
        for beat in self.beat_result.beats:
            # 跳过重拍和强拍
            if beat.is_downbeat or beat.strength > 0.7:
                continue
            
            # 检查间隔
            if beat.time - last_time >= min_interval:
                suggestions.append({
                    "time": beat.time,
                    "duration": 2.0,  # 建议插入2秒B-roll
                    "beat_strength": beat.strength,
                    "reason": "weak_beat_b_roll_slot"
                })
                last_time = beat.time
        
        return suggestions
    
    def get_beat_markers_for_export(self) -> List[Dict[str, Any]]:
        """获取用于导出的节拍标记.
        
        生成可以在视频编辑软件中导入的标记数据。
        
        Returns:
            标记列表
        """
        if self.beat_result is None:
            raise ValueError("No audio loaded. Call load_audio() first.")
        
        markers = []
        
        for beat in self.beat_result.beats:
            markers.append({
                "time": beat.time,
                "type": "downbeat" if beat.is_downbeat else "beat",
                "strength": beat.strength,
                "label": "D" if beat.is_downbeat else "B"
            })
        
        return markers
    
    def export_to_json(self, output_path: Union[str, Path]) -> None:
        """导出节拍数据到 JSON.
        
        Args:
            output_path: 输出文件路径
        """
        if self.beat_result is None:
            raise ValueError("No audio loaded. Call load_audio() first.")
        
        data = self.beat_result.to_dict()
        data["markers"] = self.get_beat_markers_for_export()
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)


# 便捷函数

def detect_beats(audio_path: Union[str, Path], method: str = "auto") -> BeatDetectionResult:
    """便捷函数：检测音频节拍.
    
    Args:
        audio_path: 音频文件路径
        method: 检测方法
        
    Returns:
        节拍检测结果
    """
    detector = BeatDetector(method=method)
    return detector.detect(audio_path)


def generate_beat_cuts(
    audio_path: Union[str, Path],
    target_duration: float = 30.0,
    prefer_downbeat: bool = True
) -> BeatMatchingResult:
    """便捷函数：生成卡点剪辑方案.
    
    Args:
        audio_path: 音频文件路径
        target_duration: 目标时长
        prefer_downbeat: 是否优先重拍
        
    Returns:
        卡点剪辑结果
    """
    detector = BeatDetector()
    return detector.generate_cuts(
        audio_path=audio_path,
        target_duration=target_duration,
        align_to_beat=True,
        prefer_downbeat=prefer_downbeat
    )
