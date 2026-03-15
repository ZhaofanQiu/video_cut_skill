"""Video Cut Skill - Exceptions."""


class VideoCutSkillError(Exception):
    """Base exception for video cut skill."""

    pass


class TranscriptionError(VideoCutSkillError):
    """Raised when transcription fails."""

    pass


class LLMError(VideoCutSkillError):
    """Raised when LLM call fails."""

    pass


class CostLimitError(VideoCutSkillError):
    """Raised when cost limit is exceeded."""

    pass


class SessionNotFoundError(VideoCutSkillError):
    """Raised when session is not found."""

    pass


class ConfigurationError(VideoCutSkillError):
    """Raised when configuration is invalid."""

    pass


class CacheError(VideoCutSkillError):
    """Raised when cache operation fails."""

    pass


class StrategyGenerationError(VideoCutSkillError):
    """Raised when strategy generation fails."""

    pass
