"""Session models for interactive video editing."""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum, auto


class SessionState(Enum):
    """Session state machine states."""

    CREATED = auto()
    TRANSCRIBING = auto()
    ANALYZING = auto()
    READY = auto()
    EDITING = auto()
    RENDERING = auto()
    COMPLETED = auto()
    ERROR = auto()


@dataclass
class EditIntent:
    """Structured editing intent parsed from user query.

    Attributes:
        intent_type: Type of editing operation
        description: Natural language description
        filter_conditions: List of filter conditions
        target_duration: Target duration in seconds (optional)
        style_preference: Style preference (compact/smooth/complete)
        llm_model: LLM model to use for selection (qwen3.5-plus or qwen3.5-flash)
    """

    intent_type: str = "SELECT"  # SELECT, REMOVE, ADJUST, ENHANCE
    description: str = ""
    filter_conditions: List[Dict[str, str]] = field(default_factory=list)
    target_duration: Optional[float] = None
    style_preference: str = "smooth"  # compact, smooth, complete
    llm_model: str = "qwen3.5-plus"  # qwen3.5-plus or qwen3.5-flash


@dataclass
class EditStrategy:
    """Video editing strategy.

    Attributes:
        strategy_id: Unique identifier
        description: Natural language description
        keep_segments: List of segment IDs to keep (legacy)
        time_ranges: List of precise time ranges to keep [{start, end}, ...]
        remove_segments: List of segment IDs to remove
        remove_fillers: Whether to remove filler words
        optimize_pauses: Whether to optimize pauses
        target_duration: Target duration in seconds
        aspect_ratio: Output aspect ratio
        add_subtitles: Whether to add subtitles
        created_at: Creation timestamp
    """

    strategy_id: str
    description: str

    # Selection logic - 支持两种模式
    keep_segments: List[str] = field(default_factory=list)  # 段落ID模式（legacy）
    time_ranges: List[Dict[str, float]] = field(default_factory=list)  # 精确时间范围模式
    remove_segments: List[str] = field(default_factory=list)

    # Refinement parameters
    remove_fillers: bool = True
    optimize_pauses: bool = True

    # Output parameters
    target_duration: Optional[float] = None
    aspect_ratio: str = "16:9"
    add_subtitles: bool = True

    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "strategy_id": self.strategy_id,
            "description": self.description,
            "keep_segments": self.keep_segments,
            "time_ranges": self.time_ranges,
            "remove_segments": self.remove_segments,
            "remove_fillers": self.remove_fillers,
            "optimize_pauses": self.optimize_pauses,
            "target_duration": self.target_duration,
            "aspect_ratio": self.aspect_ratio,
            "add_subtitles": self.add_subtitles,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class UserFeedback:
    """User feedback record.

    Attributes:
        feedback_id: Unique identifier
        feedback_text: Original feedback text
        interpreted_action: Parsed action
        timestamp: When the feedback was given
    """

    feedback_id: str
    feedback_text: str
    interpreted_action: str = ""
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "feedback_id": self.feedback_id,
            "feedback_text": self.feedback_text,
            "interpreted_action": self.interpreted_action,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class EditSession:
    """Complete editing session state supporting multi-round iteration.

    Attributes:
        session_id: Unique session identifier
        video_path: Path to video file
        video_hash: Hash for caching
        created_at: Session creation time
        last_activity: Last activity timestamp
        state: Current session state
        error_message: Error message if in ERROR state
        semantics: Video semantics data
        strategy_history: History of editing strategies
        feedback_history: History of user feedback
        current_strategy: Currently active strategy
        output_path: Path to output video
        preview_path: Path to preview video
    """

    # Basic info
    session_id: str
    video_path: str
    video_hash: str
    created_at: datetime
    last_activity: datetime = field(default_factory=datetime.now)

    # State
    state: SessionState = SessionState.CREATED
    error_message: Optional[str] = None

    # Core data (progressively built)
    semantics: Optional[Any] = None  # VideoSemantics, avoid circular import

    # Iteration history
    strategy_history: List[EditStrategy] = field(default_factory=list)
    feedback_history: List[UserFeedback] = field(default_factory=list)

    # Current strategy
    current_strategy: Optional[EditStrategy] = None

    # Output
    output_path: Optional[str] = None
    preview_path: Optional[str] = None

    def get_context_for_llm(self) -> Dict[str, Any]:
        """Generate context for LLM consumption."""
        from video_cut_skill.models.semantic import VideoSemantics

        context = {
            "video_path": self.video_path,
            "duration": None,
            "segment_count": 0,
            "current_strategy": {
                "description": None,
                "target_duration": None,
            },
            "strategy_count": len(self.strategy_history),
            "recent_feedback": [f.feedback_text for f in self.feedback_history[-3:]],
        }

        if self.semantics and isinstance(self.semantics, VideoSemantics):
            context["duration"] = self.semantics.duration
            context["segment_count"] = len(self.semantics.segments)

        if self.current_strategy:
            context["current_strategy"] = {
                "description": self.current_strategy.description,
                "target_duration": self.current_strategy.target_duration,
                "keep_count": len(self.current_strategy.keep_segments),
            }

        return context

    def add_strategy(self, strategy: EditStrategy) -> None:
        """Add a new strategy to history."""
        self.strategy_history.append(strategy)
        self.current_strategy = strategy
        self.last_activity = datetime.now()

    def add_feedback(self, feedback: UserFeedback) -> None:
        """Add user feedback."""
        self.feedback_history.append(feedback)
        self.last_activity = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        from video_cut_skill.models.semantic import VideoSemantics

        result = {
            "session_id": self.session_id,
            "video_path": self.video_path,
            "video_hash": self.video_hash,
            "created_at": self.created_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "state": self.state.name,
            "error_message": self.error_message,
            "strategy_history": [s.to_dict() for s in self.strategy_history],
            "feedback_history": [f.to_dict() for f in self.feedback_history],
            "current_strategy": self.current_strategy.to_dict() if self.current_strategy else None,
            "output_path": self.output_path,
            "preview_path": self.preview_path,
        }

        # Handle semantics serialization
        if self.semantics and isinstance(self.semantics, VideoSemantics):
            # Use a simple representation for now
            result["semantics"] = {
                "video_path": self.semantics.video_path,
                "video_hash": self.semantics.video_hash,
                "duration": self.semantics.duration,
                "segment_count": len(self.semantics.segments),
                "all_topics": self.semantics.all_topics,
                "all_keywords": self.semantics.all_keywords,
            }

        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EditSession":
        """Create from dictionary."""
        session = cls(
            session_id=data["session_id"],
            video_path=data["video_path"],
            video_hash=data["video_hash"],
            created_at=datetime.fromisoformat(data["created_at"]),
            last_activity=datetime.fromisoformat(data["last_activity"]),
            state=SessionState[data["state"]],
            error_message=data.get("error_message"),
            output_path=data.get("output_path"),
            preview_path=data.get("preview_path"),
        )

        # Restore strategy history
        for strat_data in data.get("strategy_history", []):
            session.strategy_history.append(EditStrategy(
                strategy_id=strat_data["strategy_id"],
                description=strat_data["description"],
                keep_segments=strat_data.get("keep_segments", []),
                remove_segments=strat_data.get("remove_segments", []),
                remove_fillers=strat_data.get("remove_fillers", True),
                optimize_pauses=strat_data.get("optimize_pauses", True),
                target_duration=strat_data.get("target_duration"),
                aspect_ratio=strat_data.get("aspect_ratio", "16:9"),
                add_subtitles=strat_data.get("add_subtitles", True),
                created_at=datetime.fromisoformat(strat_data["created_at"]),
            ))

        # Restore current strategy
        current_strat = data.get("current_strategy")
        if current_strat:
            session.current_strategy = EditStrategy(
                strategy_id=current_strat["strategy_id"],
                description=current_strat["description"],
                keep_segments=current_strat.get("keep_segments", []),
                remove_segments=current_strat.get("remove_segments", []),
                remove_fillers=current_strat.get("remove_fillers", True),
                optimize_pauses=current_strat.get("optimize_pauses", True),
                target_duration=current_strat.get("target_duration"),
                aspect_ratio=current_strat.get("aspect_ratio", "16:9"),
                add_subtitles=current_strat.get("add_subtitles", True),
                created_at=datetime.fromisoformat(current_strat["created_at"]),
            )

        return session
