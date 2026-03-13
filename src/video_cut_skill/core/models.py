"""Core data models."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Clip:
    """视频片段."""

    source_path: str
    start_time: float
    end_time: float
    track: int = 0
    effects: List["Effect"] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.start_time < 0:
            raise ValueError("start_time must be non-negative")
        if self.end_time <= self.start_time:
            raise ValueError("end_time must be greater than start_time")

    @property
    def duration(self) -> float:
        """片段时长."""
        return self.end_time - self.start_time


@dataclass
class Track:
    """时间线轨道."""

    name: str
    track_type: str  # "video" | "audio" | "overlay"
    clips: List[Clip] = field(default_factory=list)
    index: int = 0

    def add_clip(self, clip: Clip) -> None:
        """添加片段到轨道."""
        self.clips.append(clip)

    def remove_clip(self, clip: Clip) -> None:
        """从轨道移除片段."""
        self.clips.remove(clip)


@dataclass
class Timeline:
    """编辑时间线."""

    tracks: List[Track] = field(default_factory=list)
    duration: float = 0.0
    resolution: tuple = (1920, 1080)
    fps: float = 30.0

    def add_track(self, track: Track) -> None:
        """添加轨道."""
        track.index = len(self.tracks)
        self.tracks.append(track)

    def get_track(self, index: int) -> Optional[Track]:
        """获取指定索引的轨道."""
        if 0 <= index < len(self.tracks):
            return self.tracks[index]
        return None


@dataclass
class Project:
    """编辑项目."""

    name: str = "Untitled"
    timeline: Timeline = field(default_factory=Timeline)
    metadata: Dict[str, Any] = field(default_factory=dict)
    assets: List[str] = field(default_factory=list)

    def add_asset(self, path: str) -> None:
        """添加素材."""
        self.assets.append(path)

    def save(self, path: str) -> None:
        """保存项目."""
        # TODO: 实现项目序列化
        pass

    @classmethod
    def load(cls, path: str) -> "Project":
        """加载项目."""
        # TODO: 实现项目反序列化
        return cls()


@dataclass
class Effect:
    """视频效果基类."""

    name: str
    params: Dict[str, Any] = field(default_factory=dict)
    start_time: float = 0.0
    end_time: float = 0.0
