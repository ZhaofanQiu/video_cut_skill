"""Tests for easing functions."""

import math

import pytest

from video_cut_skill.motion_graphics.animations.easing import (
    EasingFunction,
    EasingType,
    ease_in_back,
    ease_in_bounce,
    ease_in_circ,
    ease_in_cubic,
    ease_in_elastic,
    ease_in_expo,
    ease_in_out_back,
    ease_in_out_bounce,
    ease_in_out_circ,
    ease_in_out_cubic,
    ease_in_out_elastic,
    ease_in_out_expo,
    ease_in_out_quad,
    ease_in_out_quart,
    ease_in_out_quint,
    ease_in_out_sine,
    ease_in_quad,
    ease_in_quart,
    ease_in_quint,
    ease_in_sine,
    ease_out_back,
    ease_out_bounce,
    ease_out_circ,
    ease_out_cubic,
    ease_out_elastic,
    ease_out_expo,
    ease_out_quad,
    ease_out_quart,
    ease_out_quint,
    ease_out_sine,
    linear,
)


# Helper for float comparison
def assert_approx(a, b, tol=0.0001):
    """Assert two floats are approximately equal."""
    assert abs(a - b) < tol, f"Expected {b}, got {a}"


class TestEasingFunctionsBasic:
    """Basic easing function tests."""

    @pytest.mark.parametrize(
        "func",
        [
            linear,
            ease_in_quad,
            ease_out_quad,
            ease_in_out_quad,
            ease_in_cubic,
            ease_out_cubic,
            ease_in_out_cubic,
            ease_in_quart,
            ease_out_quart,
            ease_in_out_quart,
            ease_in_quint,
            ease_out_quint,
            ease_in_out_quint,
            ease_in_sine,
            ease_out_sine,
            ease_in_out_sine,
            ease_in_expo,
            ease_out_expo,
            ease_in_out_expo,
            ease_in_circ,
            ease_out_circ,
            ease_in_out_circ,
            ease_in_back,
            ease_out_back,
            ease_in_out_back,
            ease_in_elastic,
            ease_out_elastic,
            ease_in_out_elastic,
            ease_in_bounce,
            ease_out_bounce,
            ease_in_out_bounce,
        ],
    )
    def test_start_at_zero(self, func):
        """All easing functions should start at ~0."""
        result = func(0.0)
        assert_approx(result, 0.0, 0.001)

    @pytest.mark.parametrize(
        "func",
        [
            linear,
            ease_in_quad,
            ease_out_quad,
            ease_in_out_quad,
            ease_in_cubic,
            ease_out_cubic,
            ease_in_out_cubic,
            ease_in_quart,
            ease_out_quart,
            ease_in_out_quart,
            ease_in_quint,
            ease_out_quint,
            ease_in_out_quint,
            ease_in_sine,
            ease_out_sine,
            ease_in_out_sine,
            ease_in_expo,
            ease_out_expo,
            ease_in_out_expo,
            ease_in_circ,
            ease_out_circ,
            ease_in_out_circ,
            ease_in_back,
            ease_out_back,
            ease_in_out_back,
            ease_in_elastic,
            ease_out_elastic,
            ease_in_out_elastic,
            ease_in_bounce,
            ease_out_bounce,
            ease_in_out_bounce,
        ],
    )
    def test_end_at_one(self, func):
        """All easing functions should end at ~1."""
        result = func(1.0)
        assert_approx(result, 1.0, 0.001)


class TestLinear:
    """Linear easing tests."""

    def test_linear_values(self):
        """Linear should return input value."""
        assert linear(0.0) == 0.0
        assert linear(0.5) == 0.5
        assert linear(1.0) == 1.0
        assert linear(0.25) == 0.25


class TestQuadEasing:
    """Quad easing tests."""

    def test_ease_in_quad(self):
        """Test ease_in_quad."""
        assert ease_in_quad(0.0) == 0.0
        assert ease_in_quad(0.5) == 0.25
        assert ease_in_quad(1.0) == 1.0

    def test_ease_out_quad(self):
        """Test ease_out_quad."""
        assert ease_out_quad(0.0) == 0.0
        assert_approx(ease_out_quad(0.5), 0.75)
        assert ease_out_quad(1.0) == 1.0

    def test_ease_in_out_quad(self):
        """Test ease_in_out_quad."""
        assert ease_in_out_quad(0.0) == 0.0
        assert ease_in_out_quad(0.5) == 0.5
        assert ease_in_out_quad(1.0) == 1.0


class TestCubicEasing:
    """Cubic easing tests."""

    def test_ease_in_cubic(self):
        """Test ease_in_cubic."""
        assert ease_in_cubic(0.0) == 0.0
        assert ease_in_cubic(0.5) == 0.125
        assert ease_in_cubic(1.0) == 1.0

    def test_ease_out_cubic(self):
        """Test ease_out_cubic."""
        assert ease_out_cubic(0.0) == 0.0
        assert_approx(ease_out_cubic(0.5), 0.875)
        assert ease_out_cubic(1.0) == 1.0

    def test_ease_in_out_cubic(self):
        """Test ease_in_out_cubic."""
        assert ease_in_out_cubic(0.0) == 0.0
        assert_approx(ease_in_out_cubic(0.5), 0.5)
        assert ease_in_out_cubic(1.0) == 1.0


class TestSineEasing:
    """Sine easing tests."""

    def test_ease_in_sine(self):
        """Test ease_in_sine."""
        assert_approx(ease_in_sine(0.0), 0.0)
        assert_approx(ease_in_sine(1.0), 1.0)
        # At t=0.5, should be around 0.293
        assert 0.29 < ease_in_sine(0.5) < 0.30

    def test_ease_out_sine(self):
        """Test ease_out_sine."""
        assert_approx(ease_out_sine(0.0), 0.0)
        assert_approx(ease_out_sine(1.0), 1.0)
        # At t=0.5, should be around 0.707
        assert 0.70 < ease_out_sine(0.5) < 0.71

    def test_ease_in_out_sine(self):
        """Test ease_in_out_sine."""
        assert_approx(ease_in_out_sine(0.0), 0.0)
        assert_approx(ease_in_out_sine(0.5), 0.5, 0.001)
        assert_approx(ease_in_out_sine(1.0), 1.0)


class TestExpoEasing:
    """Expo easing tests."""

    def test_ease_in_expo(self):
        """Test ease_in_expo."""
        assert_approx(ease_in_expo(0.0), 0.0)
        assert_approx(ease_in_expo(1.0), 1.0)
        # Very small value at t=0.1
        assert 0 < ease_in_expo(0.1) < 0.01

    def test_ease_out_expo(self):
        """Test ease_out_expo."""
        assert_approx(ease_out_expo(0.0), 0.0)
        assert_approx(ease_out_expo(1.0), 1.0)
        # Very close to 1 at t=0.9
        assert 0.99 < ease_out_expo(0.9) < 1.0


class TestBackEasing:
    """Back easing tests - these overshoot."""

    def test_ease_in_back(self):
        """Test ease_in_back - starts negative."""
        assert_approx(ease_in_back(0.0), 0.0)
        assert_approx(ease_in_back(1.0), 1.0)
        # Should overshoot at start
        assert ease_in_back(0.1) < 0

    def test_ease_out_back(self):
        """Test ease_out_back - overshoots at end."""
        assert_approx(ease_out_back(0.0), 0.0)
        assert_approx(ease_out_back(1.0), 1.0)
        # Should overshoot past 1
        assert ease_out_back(0.9) > 1.0


class TestElasticEasing:
    """Elastic easing tests - these oscillate."""

    def test_ease_out_elastic(self):
        """Test ease_out_elastic - oscillates at start."""
        assert_approx(ease_out_elastic(0.0), 0.0)
        assert_approx(ease_out_elastic(1.0), 1.0)
        # Oscillates around 0 at start
        assert ease_out_elastic(0.1) != 0

    def test_ease_in_elastic(self):
        """Test ease_in_elastic - oscillates at end."""
        assert_approx(ease_in_elastic(0.0), 0.0)
        assert_approx(ease_in_elastic(1.0), 1.0)


class TestBounceEasing:
    """Bounce easing tests - these bounce."""

    def test_ease_out_bounce(self):
        """Test ease_out_bounce - bounces at end."""
        assert_approx(ease_out_bounce(0.0), 0.0)
        assert_approx(ease_out_bounce(1.0), 1.0)

    def test_ease_in_bounce(self):
        """Test ease_in_bounce - bounces at start."""
        assert_approx(ease_in_bounce(0.0), 0.0)
        assert_approx(ease_in_bounce(1.0), 1.0)


class TestEasingFunctionClass:
    """EasingFunction class tests."""

    def test_initialization_with_enum(self):
        """Test initialization with EasingType enum."""
        easing = EasingFunction(EasingType.LINEAR)
        assert easing.easing_type == EasingType.LINEAR

    def test_initialization_with_callable(self):
        """Test initialization with custom callable."""

        def custom_func(t):
            return t**2

        easing = EasingFunction(custom_func)
        assert easing.easing_type == EasingType.LINEAR
        assert easing.apply(0.5) == 0.25

    def test_initialization_invalid(self):
        """Test initialization with invalid type raises error."""
        with pytest.raises(ValueError, match="Invalid easing"):
            EasingFunction("invalid_string")

    def test_apply_linear(self):
        """Test apply with linear easing."""
        easing = EasingFunction(EasingType.LINEAR)
        assert easing.apply(0.0) == 0.0
        assert easing.apply(0.5) == 0.5
        assert easing.apply(1.0) == 1.0

    def test_apply_quad(self):
        """Test apply with quad easing."""
        easing = EasingFunction(EasingType.EASE_IN_QUAD)
        assert easing.apply(0.0) == 0.0
        assert easing.apply(0.5) == 0.25
        assert easing.apply(1.0) == 1.0

    def test_apply_clamps_input(self):
        """Test apply clamps input to [0, 1]."""
        easing = EasingFunction(EasingType.LINEAR)
        assert easing.apply(-0.5) == 0.0  # Clamped to 0
        assert easing.apply(1.5) == 1.0  # Clamped to 1

    def test_all_easing_types(self):
        """Test all easing types are supported."""
        for easing_type in EasingType:
            easing = EasingFunction(easing_type)
            result = easing.apply(0.5)
            assert isinstance(result, float)
            assert not math.isnan(result)

    def test_callable(self):
        """Test EasingFunction is callable."""
        easing = EasingFunction(EasingType.LINEAR)
        assert easing(0.5) == 0.5
        assert easing(0.25) == 0.25

    def test_apply_range(self):
        """Test apply_range method."""
        easing = EasingFunction(EasingType.LINEAR)
        result = easing.apply_range(0, 100, 0.5)
        assert result == 50.0

        result = easing.apply_range(10, 20, 0.5)
        assert result == 15.0

    def test_get_available_types(self):
        """Test get_available_types class method."""
        types = EasingFunction.get_available_types()
        assert isinstance(types, list)
        assert len(types) > 0
        assert all(isinstance(t, EasingType) for t in types)


class TestEdgeCases:
    """Edge case tests."""

    def test_values_outside_range(self):
        """Test behavior with values outside [0, 1]."""
        # Raw functions work outside [0, 1]
        result = linear(-0.5)
        assert result == -0.5

        result = linear(1.5)
        assert result == 1.5

    def test_midpoint_symmetry_in_out(self):
        """Test that in-out functions are symmetric at midpoint."""
        # For in-out functions, f(0.5) should be ~0.5
        assert_approx(ease_in_out_quad(0.5), 0.5)
        assert_approx(ease_in_out_cubic(0.5), 0.5, 0.001)
