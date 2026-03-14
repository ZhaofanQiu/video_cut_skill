"""Tests for logging utilities."""

import json
import logging
from io import StringIO
from unittest.mock import MagicMock

import pytest

from video_cut_skill.utils.logging import (
    JSONFormatter,
    ProgressLogger,
    get_logger,
    setup_structured_logging,
)


class TestJSONFormatter:
    """JSONFormatter tests."""

    def test_basic_formatting(self):
        """Test basic log record formatting."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        formatted = formatter.format(record)
        data = json.loads(formatted)

        assert data["level"] == "INFO"
        assert data["logger"] == "test.logger"
        assert data["message"] == "Test message"
        assert "timestamp" in data

    def test_custom_fields(self):
        """Test formatting with custom fields."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Processing video",
            args=(),
            exc_info=None,
        )
        record.operation = "transcribe"
        record.video_path = "/path/to/video.mp4"
        record.duration = 120.5
        record.progress = 50

        formatted = formatter.format(record)
        data = json.loads(formatted)

        assert data["operation"] == "transcribe"
        assert data["video_path"] == "/path/to/video.mp4"
        assert data["duration"] == 120.5
        assert data["progress"] == 50

    def test_exception_formatting(self):
        """Test formatting with exception."""
        formatter = JSONFormatter()

        try:
            raise ValueError("Test error")
        except ValueError:
            import sys

            record = logging.LogRecord(
                name="test.logger",
                level=logging.ERROR,
                pathname="test.py",
                lineno=1,
                msg="Error occurred",
                args=(),
                exc_info=sys.exc_info(),
            )

        formatted = formatter.format(record)
        data = json.loads(formatted)

        assert data["level"] == "ERROR"
        assert "exception" in data
        assert "ValueError" in data["exception"]
        assert "Test error" in data["exception"]

    def test_arbitrary_custom_fields(self):
        """Test formatting with arbitrary custom fields."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test",
            args=(),
            exc_info=None,
        )
        record.custom_field = "custom_value"
        record.another_field = 123

        formatted = formatter.format(record)
        data = json.loads(formatted)

        assert data["custom_field"] == "custom_value"
        assert data["another_field"] == 123

    def test_unicode_message(self):
        """Test formatting with unicode message."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="中文测试消息 🎬",
            args=(),
            exc_info=None,
        )

        formatted = formatter.format(record)
        data = json.loads(formatted)

        assert data["message"] == "中文测试消息 🎬"


class TestSetupStructuredLogging:
    """setup_structured_logging tests."""

    def test_setup_json_logging(self):
        """Test setting up JSON logging."""
        stream = StringIO()
        setup_structured_logging(level=logging.INFO, use_json=True, stream=stream)

        logger = logging.getLogger("test_json")
        logger.info("Test message")

        output = stream.getvalue()
        data = json.loads(output.strip())

        assert data["message"] == "Test message"
        assert data["level"] == "INFO"

    def test_setup_plain_logging(self):
        """Test setting up plain text logging."""
        stream = StringIO()
        setup_structured_logging(level=logging.INFO, use_json=False, stream=stream)

        logger = logging.getLogger("test_plain")
        logger.info("Test message")

        output = stream.getvalue()
        assert "Test message" in output
        assert "INFO" in output

    def test_setup_different_levels(self):
        """Test setting up with different log levels."""
        stream = StringIO()
        setup_structured_logging(level=logging.WARNING, use_json=True, stream=stream)

        logger = logging.getLogger("test_level")
        logger.debug("Debug message")  # Should not appear
        logger.info("Info message")  # Should not appear
        logger.warning("Warning message")  # Should appear

        output = stream.getvalue()
        assert "Debug message" not in output
        assert "Info message" not in output
        assert "Warning message" in output


class TestProgressLogger:
    """ProgressLogger tests."""

    @pytest.fixture
    def mock_logger(self):
        """Mock logger for testing."""
        return MagicMock(spec=logging.Logger)

    def test_initialization(self, mock_logger):
        """Test ProgressLogger initialization."""
        progress = ProgressLogger(
            logger=mock_logger,
            operation="transcribe",
            total_steps=100,
            video_path="/path/to/video.mp4",
        )

        assert progress.logger == mock_logger
        assert progress.operation == "transcribe"
        assert progress.total_steps == 100
        assert progress.current_step == 0
        assert progress.video_path == "/path/to/video.mp4"

    def test_update_progress(self, mock_logger):
        """Test progress update."""
        progress = ProgressLogger(
            logger=mock_logger,
            operation="transcribe",
            total_steps=100,
        )

        progress.update(step=50)

        assert progress.current_step == 50
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        assert call_args[1]["extra"]["operation"] == "transcribe"
        assert call_args[1]["extra"]["progress"] == 50

    def test_update_auto_increment(self, mock_logger):
        """Test progress auto-increment."""
        progress = ProgressLogger(
            logger=mock_logger,
            operation="transcribe",
            total_steps=100,
        )

        progress.update()  # Step 1
        progress.update()  # Step 2
        progress.update()  # Step 3

        assert progress.current_step == 3
        assert mock_logger.info.call_count == 3

    def test_update_progress_capped_at_100(self, mock_logger):
        """Test progress is capped at 100%."""
        progress = ProgressLogger(
            logger=mock_logger,
            operation="transcribe",
            total_steps=10,
        )

        progress.update(step=20)  # Would be 200%

        call_args = mock_logger.info.call_args
        assert call_args[1]["extra"]["progress"] == 100

    def test_update_with_custom_message(self, mock_logger):
        """Test update with custom message."""
        progress = ProgressLogger(
            logger=mock_logger,
            operation="transcribe",
            total_steps=100,
        )

        progress.update(step=50, message="Halfway done")

        call_args = mock_logger.info.call_args
        assert "Halfway done" in call_args[0][0]

    def test_complete(self, mock_logger):
        """Test complete method."""
        progress = ProgressLogger(
            logger=mock_logger,
            operation="transcribe",
            total_steps=100,
            video_path="/path/to/video.mp4",
        )

        progress.complete()

        call_args = mock_logger.info.call_args
        assert call_args[1]["extra"]["progress"] == 100
        assert call_args[1]["extra"]["video_path"] == "/path/to/video.mp4"
        assert "completed" in call_args[0][0]

    def test_complete_with_custom_message(self, mock_logger):
        """Test complete with custom message."""
        progress = ProgressLogger(
            logger=mock_logger,
            operation="transcribe",
            total_steps=100,
        )

        progress.complete(message="All done!")

        call_args = mock_logger.info.call_args
        assert "All done!" in call_args[0][0]

    def test_error(self, mock_logger):
        """Test error method."""
        progress = ProgressLogger(
            logger=mock_logger,
            operation="transcribe",
            total_steps=100,
            video_path="/path/to/video.mp4",
        )

        progress.error("Connection failed")

        call_args = mock_logger.error.call_args
        assert call_args[1]["extra"]["progress"] == -1
        assert call_args[1]["extra"]["video_path"] == "/path/to/video.mp4"
        assert "Connection failed" in call_args[0][0]


class TestGetLogger:
    """get_logger tests."""

    def test_get_logger_creates_logger(self):
        """Test that get_logger creates a logger."""
        logger = get_logger("test_module")

        assert isinstance(logger, logging.Logger)
        assert logger.name == "test_module"
        assert logger.level == logging.INFO

    def test_get_logger_with_custom_level(self):
        """Test get_logger with custom level."""
        logger = get_logger("test_module_debug", level=logging.DEBUG)

        assert logger.level == logging.DEBUG

    def test_get_logger_adds_handler(self):
        """Test that get_logger adds a handler."""
        logger = get_logger("test_handler")

        assert len(logger.handlers) > 0
        handler = logger.handlers[0]
        assert isinstance(handler, logging.StreamHandler)
        assert isinstance(handler.formatter, JSONFormatter)

    def test_get_logger_does_not_duplicate_handlers(self):
        """Test that get_logger doesn't add duplicate handlers."""
        logger1 = get_logger("test_no_dup")
        handler_count = len(logger1.handlers)

        logger2 = get_logger("test_no_dup")
        assert len(logger2.handlers) == handler_count
