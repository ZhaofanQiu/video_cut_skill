"""Configuration management for video cut skill."""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


@dataclass
class ModelConfig:
    """Model provider configuration."""

    provider: str = "aliyun"
    api_key: Optional[str] = None

    # Aliyun specific
    # 可选模型:
    # - "paraformer-realtime-v2": Paraformer实时语音识别 (默认, 稳定)
    # - "qwen3-asr-flash-realtime": Qwen3-ASR-Flash实时版 (更高准确率, 推荐)
    # - "qwen3-asr-flash-realtime-2026-02-10": Qwen3-ASR-Flash (最新快照版)
    # - "qwen3-asr-flash-realtime-2025-10-27": Qwen3-ASR-Flash (快照版)
    transcribe_model: str = "qwen3-asr-flash-realtime"

    # 可选: 上下文提示，用于提升特定术语识别准确率 (仅Qwen3-ASR-Flash支持)
    # 例如: "小米汽车 雷军 新能源 智能网联"
    transcribe_context: Optional[str] = None

    llm_model: str = "qwen-max"
    language_hints: List[str] = field(default_factory=lambda: ["zh", "en"])

    def __post_init__(self):
        """Resolve API key from environment if not provided."""
        if not self.api_key:
            self.api_key = os.getenv("DASHSCOPE_API_KEY")


@dataclass
class CostControlConfig:
    """Cost control configuration."""

    # Confirmation thresholds
    max_video_duration_minutes: float = 30.0
    max_cost_yuan: float = 3.0

    # Auto downgrade
    auto_downgrade: bool = True
    when_no_api_key: bool = True
    when_cost_exceeds: float = 5.0

    # Cache settings
    cache_enabled: bool = True
    transcribe_ttl_hours: int = 168  # 7 days
    semantics_ttl_hours: int = 72  # 3 days
    max_cache_size_mb: int = 1024


@dataclass
class SessionConfig:
    """Session management configuration."""

    persistence_enabled: bool = True
    cache_dir: str = "~/.video_cut_skill"
    max_sessions: int = 50
    ttl_days: int = 7

    def get_cache_path(self) -> Path:
        """Get expanded cache directory path."""
        return Path(self.cache_dir).expanduser()


@dataclass
class EditingConfig:
    """Video editing default parameters."""

    remove_fillers: bool = True
    optimize_pauses: bool = True
    pause_threshold_seconds: float = 0.5

    # Aggregation parameters
    min_segment_duration: float = 3.0
    max_segment_duration: float = 30.0
    pause_boundary_threshold: float = 1.0

    # Output defaults
    default_aspect_ratio: str = "16:9"
    add_subtitles: bool = True


@dataclass
class VisualConfig:
    """Visual transcription configuration."""

    enabled: bool = False
    scene_detector: str = "content"
    min_scene_duration: float = 1.0
    describe_keyframes: bool = False


@dataclass
class Config:
    """Main configuration class."""

    model: ModelConfig = field(default_factory=ModelConfig)
    cost_control: CostControlConfig = field(default_factory=CostControlConfig)
    session: SessionConfig = field(default_factory=SessionConfig)
    editing: EditingConfig = field(default_factory=EditingConfig)
    visual: VisualConfig = field(default_factory=VisualConfig)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Config":
        """Create configuration from dictionary."""
        return cls(
            model=ModelConfig(**data.get("model", {})),
            cost_control=CostControlConfig(**data.get("cost_control", {})),
            session=SessionConfig(**data.get("session", {})),
            editing=EditingConfig(**data.get("editing", {})),
            visual=VisualConfig(**data.get("visual", {})),
        )

    @classmethod
    def from_yaml(cls, path: Optional[str] = None) -> "Config":
        """Load configuration from YAML file.

        Args:
            path: Path to YAML file. If None, searches in default locations.

        Returns:
            Config instance
        """
        if path:
            config_path = Path(path)
        else:
            config_path = cls._find_config_file()

        if config_path and config_path.exists():
            with open(config_path, encoding="utf-8") as f:
                data = yaml.safe_load(f)
            return cls.from_dict(data)

        # Return default config
        return cls()

    @classmethod
    def _find_config_file(cls) -> Optional[Path]:
        """Find configuration file in default locations."""
        # Priority order
        locations = [
            os.getenv("VIDEO_CUT_CONFIG_PATH"),
            "./video_cut_skill.yaml",
            "./config.yaml",
            str(Path.home() / ".video_cut_skill" / "config.yaml"),
        ]

        for loc in locations:
            if loc:
                path = Path(loc).expanduser()
                if path.exists():
                    return path

        return None

    def validate(self) -> None:
        """Validate configuration."""
        if self.model.provider == "aliyun" and not self.model.api_key:
            # 改为警告而不是错误，支持本地 Whisper 模式
            import warnings

            warnings.warn(
                "阿里云API Key未配置。LLM功能将不可用，" "但本地Whisper转录仍可正常使用。" "请设置环境变量 DASHSCOPE_API_KEY 或在配置文件中指定。",
                UserWarning,
                stacklevel=2,
            )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "model": {
                "provider": self.model.provider,
                "api_key": "***" if self.model.api_key else None,
                "transcribe_model": self.model.transcribe_model,
                "llm_model": self.model.llm_model,
                "language_hints": self.model.language_hints,
            },
            "cost_control": {
                "max_video_duration_minutes": self.cost_control.max_video_duration_minutes,
                "max_cost_yuan": self.cost_control.max_cost_yuan,
                "cache_enabled": self.cost_control.cache_enabled,
            },
            "session": {
                "persistence_enabled": self.session.persistence_enabled,
                "cache_dir": self.session.cache_dir,
            },
        }


# Global config instance
_config: Optional[Config] = None


def load_config(path: Optional[str] = None) -> Config:
    """Load global configuration.

    Args:
        path: Optional path to config file

    Returns:
        Config instance
    """
    global _config
    if _config is None or path:
        _config = Config.from_yaml(path)
        _config.validate()
    return _config


def get_config() -> Config:
    """Get current global configuration."""
    global _config
    if _config is None:
        return load_config()
    return _config


def reset_config() -> None:
    """Reset global configuration (for testing)."""
    global _config
    _config = None
