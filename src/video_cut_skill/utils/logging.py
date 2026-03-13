"""Structured logging utilities - 结构化日志工具."""

import json
import logging
import sys
from datetime import datetime
from typing import Any, Dict, Optional


class JSONFormatter(logging.Formatter):
    """JSON 格式日志格式化器."""

    def format(self, record: logging.LogRecord) -> str:
        """将日志记录格式化为 JSON."""
        log_data: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # 添加额外字段
        if hasattr(record, "operation"):
            log_data["operation"] = record.operation
        if hasattr(record, "video_path"):
            log_data["video_path"] = str(record.video_path)
        if hasattr(record, "duration"):
            log_data["duration"] = record.duration
        if hasattr(record, "progress"):
            log_data["progress"] = record.progress

        # 添加异常信息
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # 添加自定义字段
        for key, value in record.__dict__.items():
            if key not in {
                "name",
                "msg",
                "args",
                "levelname",
                "levelno",
                "pathname",
                "filename",
                "module",
                "exc_info",
                "exc_text",
                "stack_info",
                "lineno",
                "funcName",
                "created",
                "msecs",
                "relativeCreated",
                "thread",
                "threadName",
                "processName",
                "process",
                "message",
                "asctime",
                "operation",
                "video_path",
                "duration",
                "progress",
            }:
                log_data[key] = value

        return json.dumps(log_data, ensure_ascii=False, default=str)


def setup_structured_logging(
    level: int = logging.INFO,
    use_json: bool = True,
    stream: Optional[Any] = None,
) -> None:
    """设置结构化日志.

    Args:
        level: 日志级别
        use_json: 是否使用 JSON 格式
        stream: 输出流，默认 sys.stdout
    """
    stream = stream or sys.stdout

    handler = logging.StreamHandler(stream)
    handler.setLevel(level)

    formatter: logging.Formatter
    if use_json:
        formatter = JSONFormatter()
    else:
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    handler.setFormatter(formatter)

    # 配置根日志器
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.addHandler(handler)

    # 清除现有处理器避免重复
    for h in root_logger.handlers[:-1]:
        root_logger.removeHandler(h)


class ProgressLogger:
    """进度日志记录器.

    用于记录长时间操作的进度.
    """

    def __init__(
        self,
        logger: logging.Logger,
        operation: str,
        total_steps: int,
        video_path: Optional[str] = None,
    ):
        """初始化进度记录器.

        Args:
            logger: 日志器实例
            operation: 操作名称
            total_steps: 总步骤数
            video_path: 视频路径（可选）
        """
        self.logger = logger
        self.operation = operation
        self.total_steps = total_steps
        self.current_step = 0
        self.video_path = video_path

    def update(self, step: Optional[int] = None, message: Optional[str] = None) -> None:
        """更新进度.

        Args:
            step: 当前步骤，None 则自动递增
            message: 进度消息
        """
        if step is not None:
            self.current_step = step
        else:
            self.current_step += 1

        progress = min(100, int(self.current_step / self.total_steps * 100))

        extra = {
            "operation": self.operation,
            "progress": progress,
        }

        if self.video_path:
            extra["video_path"] = self.video_path

        msg = message or f"{self.operation} progress: {progress}%"
        self.logger.info(msg, extra=extra)

    def complete(self, message: Optional[str] = None) -> None:
        """标记操作完成."""
        extra = {
            "operation": self.operation,
            "progress": 100,
        }

        if self.video_path:
            extra["video_path"] = self.video_path

        msg = message or f"{self.operation} completed"
        self.logger.info(msg, extra=extra)

    def error(self, error_msg: str) -> None:
        """记录错误."""
        extra = {
            "operation": self.operation,
            "progress": -1,
        }

        if self.video_path:
            extra["video_path"] = self.video_path

        self.logger.error(f"{self.operation} failed: {error_msg}", extra=extra)


def get_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """获取配置好的 logger.

    Args:
        name: logger 名称
        level: 日志级别

    Returns:
        logging.Logger: 配置好的 logger
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(level)
        formatter = JSONFormatter()
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger
