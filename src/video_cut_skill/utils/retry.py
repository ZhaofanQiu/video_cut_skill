"""Retry utilities with exponential backoff - 带指数退避的重试工具."""

import functools
import logging
import random
import time
from typing import Any, Callable, Optional, Tuple, Type

logger = logging.getLogger(__name__)


class RetryError(Exception):
    """重试耗尽错误."""

    def __init__(self, message: str, last_exception: Optional[Exception] = None):
        """初始化重试错误.

        Args:
            message: 错误消息
            last_exception: 最后一次异常
        """
        super().__init__(message)
        self.last_exception = last_exception


def retry_with_backoff(
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    on_retry: Optional[Callable[[Exception, int, float], None]] = None,
) -> Callable:
    """重试装饰器，带指数退避.

    Args:
        max_attempts: 最大重试次数
        initial_delay: 初始延迟（秒）
        max_delay: 最大延迟（秒）
        exponential_base: 指数基数
        jitter: 是否添加随机抖动
        exceptions: 需要重试的异常类型
        on_retry: 重试时的回调函数 (exception, attempt, delay)

    Returns:
        装饰器函数
    """

    def decorator(func: Callable) -> Callable:
        """创建重试包装器.

        Args:
            func: 需要重试的函数

        Returns:
            包装后的函数
        """

        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            """包装函数，执行重试逻辑.

            Args:
                *args: 原函数的位置参数
                **kwargs: 原函数的关键字参数

            Returns:
                原函数的返回值

            Raises:
                RetryError: 所有重试尝试失败后抛出
            """
            last_exception = None

            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e

                    if attempt == max_attempts:
                        logger.error(f"{func.__name__} failed after {max_attempts} attempts: {e}")
                        raise RetryError(
                            f"Operation failed after {max_attempts} attempts",
                            last_exception=e,
                        ) from e

                    # 计算延迟
                    delay = min(
                        initial_delay * (exponential_base ** (attempt - 1)),
                        max_delay,
                    )

                    if jitter:
                        delay *= 0.5 + random.random()  # 添加 0.5x-1.5x 的抖动

                    logger.warning(f"{func.__name__} failed (attempt {attempt}/{max_attempts}): {e}. " f"Retrying in {delay:.1f}s...")

                    if on_retry:
                        on_retry(e, attempt, delay)

                    time.sleep(delay)

            # 不应该到达这里
            raise RetryError("Unexpected end of retry loop", last_exception=last_exception)

        return wrapper

    return decorator


class RetryableOperation:
    """可重试操作类.

    用于需要手动控制重试逻辑的场景.
    """

    def __init__(
        self,
        operation: Callable,
        max_attempts: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        exceptions: Tuple[Type[Exception], ...] = (Exception,),
    ):
        """初始化.

        Args:
            operation: 要执行的操作
            max_attempts: 最大重试次数
            initial_delay: 初始延迟
            max_delay: 最大延迟
            exceptions: 需要重试的异常类型
        """
        self.operation = operation
        self.max_attempts = max_attempts
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.exceptions = exceptions
        self.attempt_count = 0

    def execute(self, *args, **kwargs) -> Any:
        """执行操作，带重试逻辑."""
        last_exception = None

        for attempt in range(1, self.max_attempts + 1):
            self.attempt_count = attempt
            try:
                return self.operation(*args, **kwargs)
            except self.exceptions as e:
                last_exception = e

                if attempt == self.max_attempts:
                    raise RetryError(
                        f"Operation failed after {self.max_attempts} attempts",
                        last_exception=e,
                    ) from e

                delay = min(
                    self.initial_delay * (2 ** (attempt - 1)),
                    self.max_delay,
                )

                logger.warning(f"Operation failed (attempt {attempt}/{self.max_attempts}): {e}. " f"Retrying in {delay:.1f}s...")
                time.sleep(delay)

        raise RetryError("Unexpected end of retry loop", last_exception=last_exception)


# 常用的重试配置
NETWORK_RETRY = functools.partial(
    retry_with_backoff,
    max_attempts=5,
    initial_delay=1.0,
    max_delay=30.0,
    exceptions=(ConnectionError, TimeoutError, OSError),
)

DOWNLOAD_RETRY = functools.partial(
    retry_with_backoff,
    max_attempts=3,
    initial_delay=2.0,
    max_delay=60.0,
    exceptions=(ConnectionError, TimeoutError, IOError),
)

API_RETRY = functools.partial(
    retry_with_backoff,
    max_attempts=3,
    initial_delay=1.0,
    max_delay=10.0,
    exceptions=(ConnectionError, TimeoutError),
)
