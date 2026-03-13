"""Easing Functions - 缓动函数库.

提供各种缓动效果用于动画过渡.
参考: https://easings.net/
"""

import math
from enum import Enum
from typing import Callable, Union


class EasingType(Enum):
    """缓动类型枚举."""

    # Linear
    LINEAR = "linear"

    # Quad
    EASE_IN_QUAD = "ease_in_quad"
    EASE_OUT_QUAD = "ease_out_quad"
    EASE_IN_OUT_QUAD = "ease_in_out_quad"

    # Cubic
    EASE_IN_CUBIC = "ease_in_cubic"
    EASE_OUT_CUBIC = "ease_out_cubic"
    EASE_IN_OUT_CUBIC = "ease_in_out_cubic"

    # Quart
    EASE_IN_QUART = "ease_in_quart"
    EASE_OUT_QUART = "ease_out_quart"
    EASE_IN_OUT_QUART = "ease_in_out_quart"

    # Quint
    EASE_IN_QUINT = "ease_in_quint"
    EASE_OUT_QUINT = "ease_out_quint"
    EASE_IN_OUT_QUINT = "ease_in_out_quint"

    # Sine
    EASE_IN_SINE = "ease_in_sine"
    EASE_OUT_SINE = "ease_out_sine"
    EASE_IN_OUT_SINE = "ease_in_out_sine"

    # Expo
    EASE_IN_EXPO = "ease_in_expo"
    EASE_OUT_EXPO = "ease_out_expo"
    EASE_IN_OUT_EXPO = "ease_in_out_expo"

    # Circ
    EASE_IN_CIRC = "ease_in_circ"
    EASE_OUT_CIRC = "ease_out_circ"
    EASE_IN_OUT_CIRC = "ease_in_out_circ"

    # Back
    EASE_IN_BACK = "ease_in_back"
    EASE_OUT_BACK = "ease_out_back"
    EASE_IN_OUT_BACK = "ease_in_out_back"

    # Elastic
    EASE_IN_ELASTIC = "ease_in_elastic"
    EASE_OUT_ELASTIC = "ease_out_elastic"
    EASE_IN_OUT_ELASTIC = "ease_in_out_elastic"

    # Bounce
    EASE_IN_BOUNCE = "ease_in_bounce"
    EASE_OUT_BOUNCE = "ease_out_bounce"
    EASE_IN_OUT_BOUNCE = "ease_in_out_bounce"


# 默认 Back 效果的回弹系数
DEFAULT_BACK_OVERSHOOT = 1.70158


def linear(t: float) -> float:
    """线性缓动."""
    return t


def ease_in_quad(t: float) -> float:
    """Quad Ease In."""
    return t * t


def ease_out_quad(t: float) -> float:
    """Quad Ease Out."""
    return 1 - (1 - t) * (1 - t)


def ease_in_out_quad(t: float) -> float:
    """Quad Ease In-Out."""
    return 2 * t * t if t < 0.5 else 1 - math.pow(-2 * t + 2, 2) / 2


def ease_in_cubic(t: float) -> float:
    """Cubic Ease In."""
    return t * t * t


def ease_out_cubic(t: float) -> float:
    """Cubic Ease Out."""
    return 1 - math.pow(1 - t, 3)


def ease_in_out_cubic(t: float) -> float:
    """Cubic Ease In-Out."""
    return 4 * t * t * t if t < 0.5 else 1 - math.pow(-2 * t + 2, 3) / 2


def ease_in_quart(t: float) -> float:
    """Quart Ease In."""
    return t * t * t * t


def ease_out_quart(t: float) -> float:
    """Quart Ease Out."""
    return 1 - math.pow(1 - t, 4)


def ease_in_out_quart(t: float) -> float:
    """Quart Ease In-Out."""
    return 8 * t * t * t * t if t < 0.5 else 1 - math.pow(-2 * t + 2, 4) / 2


def ease_in_quint(t: float) -> float:
    """Quint Ease In."""
    return t * t * t * t * t


def ease_out_quint(t: float) -> float:
    """Quint Ease Out."""
    return 1 - math.pow(1 - t, 5)


def ease_in_out_quint(t: float) -> float:
    """Quint Ease In-Out."""
    return 16 * t * t * t * t * t if t < 0.5 else 1 - math.pow(-2 * t + 2, 5) / 2


def ease_in_sine(t: float) -> float:
    """Sine Ease In."""
    return 1 - math.cos(t * math.pi / 2)


def ease_out_sine(t: float) -> float:
    """Sine Ease Out."""
    return math.sin(t * math.pi / 2)


def ease_in_out_sine(t: float) -> float:
    """Sine Ease In-Out."""
    return -(math.cos(math.pi * t) - 1) / 2


def ease_in_expo(t: float) -> float:
    """Expo Ease In."""
    return 0 if t == 0 else math.pow(2, 10 * (t - 1))


def ease_out_expo(t: float) -> float:
    """Expo Ease Out."""
    return 1 if t == 1 else 1 - math.pow(2, -10 * t)


def ease_in_out_expo(t: float) -> float:
    """Expo Ease In-Out."""
    if t == 0:
        return 0
    if t == 1:
        return 1
    return math.pow(2, 20 * t - 10) / 2 if t < 0.5 else (2 - math.pow(2, -20 * t + 10)) / 2


def ease_in_circ(t: float) -> float:
    """Circ Ease In."""
    return 1 - math.sqrt(1 - math.pow(t, 2))


def ease_out_circ(t: float) -> float:
    """Circ Ease Out."""
    return math.sqrt(1 - math.pow(t - 1, 2))


def ease_in_out_circ(t: float) -> float:
    """Circ Ease In-Out."""
    return (1 - math.sqrt(1 - math.pow(2 * t, 2))) / 2 if t < 0.5 else (math.sqrt(1 - math.pow(-2 * t + 2, 2)) + 1) / 2


def ease_in_back(t: float, overshoot: float = DEFAULT_BACK_OVERSHOOT) -> float:
    """Back Ease In."""
    return t * t * ((overshoot + 1) * t - overshoot)


def ease_out_back(t: float, overshoot: float = DEFAULT_BACK_OVERSHOOT) -> float:
    """Back Ease Out."""
    return 1 + (t - 1) * (t - 1) * ((overshoot + 1) * (t - 1) + overshoot)


def ease_in_out_back(t: float, overshoot: float = DEFAULT_BACK_OVERSHOOT) -> float:
    """Back Ease In-Out."""
    if t < 0.5:
        return (math.pow(2 * t, 2) * ((overshoot + 1) * 2 * t - overshoot)) / 2
    else:
        return (math.pow(2 * t - 2, 2) * ((overshoot + 1) * (t * 2 - 2) + overshoot) + 2) / 2


def ease_in_elastic(t: float) -> float:
    """Elastic Ease In."""
    if t == 0:
        return 0
    if t == 1:
        return 1
    return -math.pow(2, 10 * t - 10) * math.sin((t * 10 - 10.75) * (2 * math.pi) / 3)


def ease_out_elastic(t: float) -> float:
    """Elastic Ease Out."""
    if t == 0:
        return 0
    if t == 1:
        return 1
    return math.pow(2, -10 * t) * math.sin((t * 10 - 0.75) * (2 * math.pi) / 3) + 1


def ease_in_out_elastic(t: float) -> float:
    """Elastic Ease In-Out."""
    if t == 0:
        return 0
    if t == 1:
        return 1
    if t < 0.5:
        return -(math.pow(2, 20 * t - 10) * math.sin((20 * t - 11.125) * (2 * math.pi) / 4.5)) / 2
    return (math.pow(2, -20 * t + 10) * math.sin((20 * t - 11.125) * (2 * math.pi) / 4.5)) / 2 + 1


def ease_out_bounce(t: float) -> float:
    """Bounce Ease Out."""
    n1 = 7.5625
    d1 = 2.75

    if t < 1 / d1:
        return n1 * t * t
    elif t < 2 / d1:
        t -= 1.5 / d1
        return n1 * t * t + 0.75
    elif t < 2.5 / d1:
        t -= 2.25 / d1
        return n1 * t * t + 0.9375
    else:
        t -= 2.625 / d1
        return n1 * t * t + 0.984375


def ease_in_bounce(t: float) -> float:
    """Bounce Ease In."""
    return 1 - ease_out_bounce(1 - t)


def ease_in_out_bounce(t: float) -> float:
    """Bounce Ease In-Out."""
    if t < 0.5:
        return (1 - ease_out_bounce(1 - 2 * t)) / 2
    return (1 + ease_out_bounce(2 * t - 1)) / 2


# 缓动函数映射表
_EASING_FUNCTIONS = {
    EasingType.LINEAR: linear,
    EasingType.EASE_IN_QUAD: ease_in_quad,
    EasingType.EASE_OUT_QUAD: ease_out_quad,
    EasingType.EASE_IN_OUT_QUAD: ease_in_out_quad,
    EasingType.EASE_IN_CUBIC: ease_in_cubic,
    EasingType.EASE_OUT_CUBIC: ease_out_cubic,
    EasingType.EASE_IN_OUT_CUBIC: ease_in_out_cubic,
    EasingType.EASE_IN_QUART: ease_in_quart,
    EasingType.EASE_OUT_QUART: ease_out_quart,
    EasingType.EASE_IN_OUT_QUART: ease_in_out_quart,
    EasingType.EASE_IN_QUINT: ease_in_quint,
    EasingType.EASE_OUT_QUINT: ease_out_quint,
    EasingType.EASE_IN_OUT_QUINT: ease_in_out_quint,
    EasingType.EASE_IN_SINE: ease_in_sine,
    EasingType.EASE_OUT_SINE: ease_out_sine,
    EasingType.EASE_IN_OUT_SINE: ease_in_out_sine,
    EasingType.EASE_IN_EXPO: ease_in_expo,
    EasingType.EASE_OUT_EXPO: ease_out_expo,
    EasingType.EASE_IN_OUT_EXPO: ease_in_out_expo,
    EasingType.EASE_IN_CIRC: ease_in_circ,
    EasingType.EASE_OUT_CIRC: ease_out_circ,
    EasingType.EASE_IN_OUT_CIRC: ease_in_out_circ,
    EasingType.EASE_IN_BACK: ease_in_back,
    EasingType.EASE_OUT_BACK: ease_out_back,
    EasingType.EASE_IN_OUT_BACK: ease_in_out_back,
    EasingType.EASE_IN_ELASTIC: ease_in_elastic,
    EasingType.EASE_OUT_ELASTIC: ease_out_elastic,
    EasingType.EASE_IN_OUT_ELASTIC: ease_in_out_elastic,
    EasingType.EASE_IN_BOUNCE: ease_in_bounce,
    EasingType.EASE_OUT_BOUNCE: ease_out_bounce,
    EasingType.EASE_IN_OUT_BOUNCE: ease_in_out_bounce,
}


class EasingFunction:
    """缓动函数封装类.

    提供统一的缓动函数接口，支持通过类型或自定义函数创建.

    Example:
        >>> # 使用预设类型
        >>> easing = EasingFunction(EasingType.EASE_OUT_QUAD)
        >>> value = easing.apply(0.5)  # 获取 50% 进度的缓动值

        >>> # 使用自定义函数
        >>> custom = EasingFunction(lambda t: t ** 3)
        >>> value = custom.apply(0.5)
    """

    def __init__(
        self,
        easing: Union[EasingType, Callable[[float], float]],
    ):
        """初始化缓动函数.

        Args:
            easing: 缓动类型或自定义函数
        """
        if isinstance(easing, EasingType):
            self._type = easing
            self._func = _EASING_FUNCTIONS.get(easing, linear)
        elif callable(easing):
            self._type = EasingType.LINEAR
            self._func = easing
        else:
            raise ValueError(f"Invalid easing: {easing}")

    def apply(self, t: float) -> float:
        """应用缓动函数.

        Args:
            t: 输入进度 [0, 1]

        Returns:
            缓动后的值
        """
        # 确保输入在 [0, 1] 范围内
        t = max(0.0, min(1.0, t))
        result: float = self._func(t)  # type: ignore[operator]
        return result

    def apply_range(
        self,
        start: float,
        end: float,
        t: float,
    ) -> float:
        """在指定范围内应用缓动.

        Args:
            start: 起始值
            end: 结束值
            t: 进度 [0, 1]

        Returns:
            缓动后的值
        """
        eased = self.apply(t)
        return start + (end - start) * eased

    @property
    def easing_type(self) -> EasingType:
        """获取缓动类型."""
        return self._type

    @classmethod
    def get_available_types(cls) -> list:
        """获取所有可用的缓动类型."""
        return list(EasingType)

    def __call__(self, t: float) -> float:
        """使实例可直接调用."""
        return self.apply(t)

    def __repr__(self) -> str:
        return f"EasingFunction({self._type.value})"
