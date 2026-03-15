"""Cost control and guardian for managing API expenses."""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from video_cut_skill.config import get_config


@dataclass
class CostCheckResult:
    """Result of cost check.

    Attributes:
        requires_confirmation: Whether user confirmation is needed
        warning_message: Warning message for user
        estimated_cost: Estimated cost in yuan
        suggestions: Cost optimization suggestions
    """

    requires_confirmation: bool
    warning_message: str = ""
    estimated_cost: float = 0.0
    suggestions: List[str] = None

    def __post_init__(self):
        if self.suggestions is None:
            self.suggestions = []


class CostGuardian:
    """Monitors and controls API costs.

    Provides cost estimation, threshold checking, and optimization suggestions.
    """

    # Cost rates (yuan per unit)
    TRANSCRIBE_RATE_PER_SECOND = 0.000012 * 7.2  # ~0.000086 yuan/sec (paraformer-v2)
    LLM_RATE_PER_1K_TOKENS = 0.006  # qwen-max: 0.006 yuan/1k tokens
    SUMMARY_TOKENS_PER_SEGMENT = 200  # Estimated tokens for segment summary

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize cost guardian.

        Args:
            config: Optional configuration override
        """
        if config:
            self._config = config
        else:
            global_config = get_config()
            self._config = {
                "max_video_duration_minutes": global_config.cost_control.max_video_duration_minutes,
                "max_cost_yuan": global_config.cost_control.max_cost_yuan,
                "auto_downgrade": global_config.cost_control.auto_downgrade,
            }

    def check_analyze(
        self,
        video_path: str,
        duration_seconds: float,
    ) -> CostCheckResult:
        """Check cost for video analysis (transcription).

        Args:
            video_path: Path to video file
            duration_seconds: Video duration in seconds

        Returns:
            CostCheckResult
        """
        warnings = []
        requires_confirm = False

        # Check duration threshold
        duration_minutes = duration_seconds / 60
        max_duration = self._config["max_video_duration_minutes"]

        if duration_minutes > max_duration:
            warnings.append(f"视频时长{duration_minutes:.1f}分钟超过阈值{max_duration}分钟，" f"转录可能消耗较多积分。")
            requires_confirm = True

        # Estimate transcription cost
        transcribe_cost = duration_seconds * self.TRANSCRIBE_RATE_PER_SECOND

        # Add semantic analysis cost estimate
        # Assume 1 segment per 10 seconds on average
        estimated_segments = max(1, int(duration_seconds / 10))
        summary_cost = estimated_segments / 10 * 500 * self.LLM_RATE_PER_1K_TOKENS / 1000  # Batch processing: 10 segments per call, ~500 tokens each

        total_cost = transcribe_cost + summary_cost

        # Check cost threshold
        max_cost = self._config["max_cost_yuan"]
        if total_cost > max_cost:
            warnings.append(f"预估分析成本 ￥{total_cost:.2f} 超过阈值 ￥{max_cost:.2f}")
            requires_confirm = True

        # Build warning message
        message = ""
        if warnings:
            message = "\n".join(warnings)
            message += "\n\n预估成本明细："
            message += f"\n- 语音转录：￥{transcribe_cost:.2f}"
            message += f"\n- 语义分析：￥{summary_cost:.2f}"
            message += f"\n- 总计：￥{total_cost:.2f}"

        # Suggestions
        suggestions = []
        if duration_minutes > max_duration:
            suggestions.append("建议：如果视频包含多段落，可以先提取音频片段再分析")
        if total_cost > max_cost:
            suggestions.append("建议：可以先试听关键部分，或降低语义分析深度")

        return CostCheckResult(
            requires_confirmation=requires_confirm,
            warning_message=message,
            estimated_cost=total_cost,
            suggestions=suggestions,
        )

    def check_edit(
        self,
        strategy: Dict[str, Any],
        estimated_segments: int = 0,
    ) -> CostCheckResult:
        """Check cost for editing operation.

        Args:
            strategy: Edit strategy
            estimated_segments: Estimated number of segments to process

        Returns:
            CostCheckResult
        """
        warnings = []
        requires_confirm = False

        # Strategy generation already done (cost incurred)
        # Main cost here is rendering (local, no API cost)
        total_cost = 0.0

        # If we need to re-analyze with LLM for refinement
        if estimated_segments > 50:
            warnings.append(f"段落数较多({estimated_segments})，后续调整可能产生额外成本")

        message = "\n".join(warnings) if warnings else ""

        return CostCheckResult(
            requires_confirmation=requires_confirm,
            warning_message=message,
            estimated_cost=total_cost,
            suggestions=[],
        )

    def estimate_summary_cost(
        self,
        segment_count: int,
        batch_size: int = 10,
    ) -> float:
        """Estimate cost for segment summarization.

        Args:
            segment_count: Number of segments
            batch_size: Segments per batch

        Returns:
            Estimated cost in yuan
        """
        batches = max(1, (segment_count + batch_size - 1) // batch_size)
        tokens_per_batch = batch_size * self.SUMMARY_TOKENS_PER_SEGMENT
        return batches * tokens_per_batch * self.LLM_RATE_PER_1K_TOKENS / 1000

    def estimate_intent_parse_cost(self) -> float:
        """Estimate cost for intent parsing.

        Returns:
            Estimated cost in yuan
        """
        # Intent parsing is typically ~500 tokens
        return 500 * self.LLM_RATE_PER_1K_TOKENS / 1000

    def get_optimization_suggestions(
        self,
        video_duration: float,
        segment_count: int,
    ) -> List[str]:
        """Get cost optimization suggestions.

        Args:
            video_duration: Video duration in seconds
            segment_count: Number of segments

        Returns:
            List of suggestion strings
        """
        suggestions = []

        if video_duration > 30 * 60:  # 30 minutes
            suggestions.append("视频较长，建议分段处理或只对关键片段进行深度分析")

        if segment_count > 50:
            suggestions.append("段落较多，建议使用批量处理或关键词过滤后再进行语义分析")

        suggestions.append("启用缓存可以避免重复分析相同视频")

        return suggestions
