"""Agent interaction models."""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Literal
from enum import Enum


class AgentActionType(Enum):
    """Types of agent actions."""

    CONFIRM = "confirm"
    MODIFY = "modify"
    PREVIEW = "preview"
    RETRY = "retry"
    CANCEL = "cancel"


@dataclass
class AgentAction:
    """Executable action for agent.

    Attributes:
        action_type: Type of action
        description: Human-readable description
        parameters: Action parameters
    """

    action_type: AgentActionType
    description: str
    parameters: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentResponse:
    """Standard response for agent interaction.

    This format is designed to be consumed by any agent framework
    (OpenClaw, LangChain, etc.).

    Attributes:
        state: Current processing state
        message: Natural language message for user
        data: Structured data for agent consumption
        available_actions: List of available actions
        cost_info: Cost transparency information
    """

    state: Literal["analyzing", "awaiting_confirm", "editing", "completed", "error", "ready"]
    message: str
    data: Dict[str, Any] = field(default_factory=dict)
    available_actions: List[AgentAction] = field(default_factory=list)
    cost_info: Optional[Dict[str, float]] = None

    @classmethod
    def waiting_transcription(cls) -> "AgentResponse":
        """Response while waiting for transcription."""
        return cls(
            state="analyzing",
            message="正在分析视频内容，请稍候...",
            data={"progress": "transcribing"},
        )

    @classmethod
    def analyzing_content(cls) -> "AgentResponse":
        """Response while analyzing content."""
        return cls(
            state="analyzing",
            message="正在理解视频内容...",
            data={"progress": "analyzing"},
        )

    @classmethod
    def ready_for_edit(
        cls,
        segment_count: int,
        duration: float,
        topics: List[str],
        segments_preview: Optional[List[Dict]] = None,
    ) -> "AgentResponse":
        """Response when video is ready for editing."""
        topics_str = ", ".join(topics[:3]) if topics else "未识别"
        message = (
            f"分析完成。视频共{segment_count}个片段，"
            f"时长{duration:.1f}秒，"
            f"识别主题：{topics_str}。\n\n"
            f"请告诉我您希望如何剪辑？"
        )

        return cls(
            state="ready",
            message=message,
            data={
                "segment_count": segment_count,
                "duration": duration,
                "segments_preview": segments_preview or [],
                "topics": topics,
            },
            available_actions=[
                AgentAction(AgentActionType.MODIFY, "指定剪辑要求"),
                AgentAction(AgentActionType.PREVIEW, "查看完整摘要"),
            ],
        )

    @classmethod
    def awaiting_confirmation(
        cls,
        strategy_description: str,
        target_duration: Optional[float],
        keep_count: int,
        cost: float,
    ) -> "AgentResponse":
        """Response awaiting user confirmation."""
        duration_str = f"{target_duration:.0f}秒" if target_duration else "自动"
        message = (
            f"建议剪辑策略：{strategy_description}\n"
            f"预计输出时长：{duration_str}\n"
            f"保留片段数：{keep_count}\n"
            f"预估成本：￥{cost:.2f}\n\n"
            f"是否确认执行？"
        )

        return cls(
            state="awaiting_confirm",
            message=message,
            data={
                "strategy": {
                    "description": strategy_description,
                    "target_duration": target_duration,
                    "keep_count": keep_count,
                },
                "estimated_cost": cost,
            },
            available_actions=[
                AgentAction(AgentActionType.CONFIRM, "确认并执行"),
                AgentAction(AgentActionType.MODIFY, "调整策略"),
                AgentAction(AgentActionType.CANCEL, "取消"),
            ],
            cost_info={"estimated_yuan": cost},
        )

    @classmethod
    def editing_in_progress(cls, progress: float = 0.0) -> "AgentResponse":
        """Response while editing is in progress."""
        return cls(
            state="editing",
            message=f"正在剪辑视频... {progress:.0%}",
            data={"progress": progress},
        )

    @classmethod
    def completed(
        cls,
        output_path: str,
        output_duration: Optional[float] = None,
    ) -> "AgentResponse":
        """Response when editing is completed."""
        duration_str = f"，时长{output_duration:.1f}秒" if output_duration else ""
        message = f"剪辑完成！输出文件：{output_path}{duration_str}"

        return cls(
            state="completed",
            message=message,
            data={
                "output_path": output_path,
                "duration": output_duration,
            },
            available_actions=[
                AgentAction(AgentActionType.MODIFY, "继续调整"),
            ],
        )

    @classmethod
    def error(cls, message: str, details: Optional[str] = None) -> "AgentResponse":
        """Response for error state."""
        full_message = message
        if details:
            full_message += f"\n详情：{details}"

        return cls(
            state="error",
            message=full_message,
            data={"error": message, "details": details},
            available_actions=[
                AgentAction(AgentActionType.RETRY, "重试"),
                AgentAction(AgentActionType.CANCEL, "取消"),
            ],
        )
