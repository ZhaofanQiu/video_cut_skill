"""Tests for shape element module."""

from video_cut_skill.motion_graphics.elements.shape import (
    ShapeElement,
    ShapeStyle,
    ShapeType,
)


class TestShapeType:
    """ShapeType enum tests."""

    def test_shape_type_values(self):
        """Test ShapeType enum values."""
        assert ShapeType.RECTANGLE.value == "rectangle"
        assert ShapeType.CIRCLE.value == "circle"
        assert ShapeType.ELLIPSE.value == "ellipse"
        assert ShapeType.LINE.value == "line"
        assert ShapeType.POLYGON.value == "polygon"


class TestShapeStyle:
    """ShapeStyle dataclass tests."""

    def test_default_values(self):
        """Test default style values."""
        style = ShapeStyle()
        assert style.fill_color == "#FFFFFF"
        assert style.fill_opacity == 1.0
        assert style.stroke_color is None
        assert style.stroke_width == 0
        assert style.stroke_opacity == 1.0
        assert style.corner_radius == 0

    def test_custom_values(self):
        """Test custom style values."""
        style = ShapeStyle(
            fill_color="#FF0000",
            fill_opacity=0.5,
            stroke_color="#000000",
            stroke_width=5,
            stroke_opacity=0.8,
            corner_radius=10,
        )
        assert style.fill_color == "#FF0000"
        assert style.fill_opacity == 0.5
        assert style.stroke_color == "#000000"
        assert style.stroke_width == 5
        assert style.stroke_opacity == 0.8
        assert style.corner_radius == 10

    def test_no_fill(self):
        """Test style with no fill."""
        style = ShapeStyle(fill_color=None)
        assert style.fill_color is None


class TestShapeElement:
    """ShapeElement dataclass tests."""

    def test_rectangle_creation(self):
        """Test creating rectangle."""
        rect = ShapeElement.rectangle(
            x=100,
            y=200,
            width=300,
            height=400,
        )
        assert rect.shape_type == ShapeType.RECTANGLE
        assert rect.params == {"x": 100, "y": 200, "width": 300, "height": 400}
        assert rect.style is not None

    def test_circle_creation(self):
        """Test creating circle."""
        circle = ShapeElement.circle(
            cx=500,
            cy=600,
            radius=100,
        )
        assert circle.shape_type == ShapeType.CIRCLE
        assert circle.params == {"cx": 500, "cy": 600, "radius": 100}

    def test_ellipse_creation(self):
        """Test creating ellipse."""
        ellipse = ShapeElement.ellipse(
            cx=400,
            cy=300,
            rx=150,
            ry=100,
        )
        assert ellipse.shape_type == ShapeType.ELLIPSE
        assert ellipse.params == {"cx": 400, "cy": 300, "rx": 150, "ry": 100}

    def test_line_creation(self):
        """Test creating line."""
        line = ShapeElement.line(
            x1=0,
            y1=0,
            x2=100,
            y2=100,
            stroke_width=3,
            stroke_color="#FF0000",
        )
        assert line.shape_type == ShapeType.LINE
        assert line.params == {"x1": 0, "y1": 0, "x2": 100, "y2": 100}
        assert line.style.stroke_color == "#FF0000"
        assert line.style.stroke_width == 3

    def test_custom_style(self):
        """Test shape with custom style."""
        style = ShapeStyle(
            fill_color="#00FF00",
            stroke_color="#0000FF",
            stroke_width=2,
        )
        rect = ShapeElement.rectangle(
            x=0,
            y=0,
            width=100,
            height=100,
            style=style,
        )
        assert rect.style == style

    def test_custom_time_range(self):
        """Test shape with custom time range."""
        rect = ShapeElement.rectangle(
            x=0,
            y=0,
            width=100,
            height=100,
            start_time=2.0,
            end_time=8.0,
        )
        assert rect.start_time == 2.0
        assert rect.end_time == 8.0

    def test_duration_property(self):
        """Test duration property."""
        rect = ShapeElement.rectangle(
            x=0,
            y=0,
            width=100,
            height=100,
            start_time=1.0,
            end_time=6.0,
        )
        assert rect.duration == 5.0

    def test_is_visible_at(self):
        """Test is_visible_at method."""
        rect = ShapeElement.rectangle(
            x=0,
            y=0,
            width=100,
            height=100,
            start_time=1.0,
            end_time=5.0,
        )
        assert rect.is_visible_at(2.0) is True
        assert rect.is_visible_at(4.9) is True
        assert rect.is_visible_at(0.5) is False
        assert rect.is_visible_at(5.0) is False
        assert rect.is_visible_at(6.0) is False

    def test_is_visible_at_boundary(self):
        """Test is_visible_at at boundary."""
        rect = ShapeElement.rectangle(
            x=0,
            y=0,
            width=100,
            height=100,
            start_time=1.0,
            end_time=5.0,
        )
        assert rect.is_visible_at(1.0) is True  # At start


class TestShapeElementToSVG:
    """ShapeElement to_svg method tests."""

    def test_rectangle_to_svg(self):
        """Test rectangle SVG conversion."""
        rect = ShapeElement.rectangle(
            x=100,
            y=200,
            width=300,
            height=400,
        )
        svg = rect.to_svg()
        assert "<rect" in svg
        assert 'x="100"' in svg
        assert 'y="200"' in svg
        assert 'width="300"' in svg
        assert 'height="400"' in svg
        assert 'rx="0"' in svg

    def test_rectangle_to_svg_with_corner_radius(self):
        """Test rectangle with corner radius."""
        style = ShapeStyle(corner_radius=10)
        rect = ShapeElement.rectangle(
            x=0,
            y=0,
            width=100,
            height=100,
            style=style,
        )
        svg = rect.to_svg()
        assert 'rx="10"' in svg

    def test_circle_to_svg(self):
        """Test circle SVG conversion."""
        circle = ShapeElement.circle(
            cx=500,
            cy=600,
            radius=100,
        )
        svg = circle.to_svg()
        assert "<circle" in svg
        assert 'cx="500"' in svg
        assert 'cy="600"' in svg
        assert 'r="100"' in svg

    def test_ellipse_to_svg(self):
        """Test ellipse SVG conversion."""
        ellipse = ShapeElement.ellipse(
            cx=400,
            cy=300,
            rx=150,
            ry=100,
        )
        svg = ellipse.to_svg()
        assert "<ellipse" in svg
        assert 'cx="400"' in svg
        assert 'cy="300"' in svg
        assert 'rx="150"' in svg
        assert 'ry="100"' in svg

    def test_line_to_svg(self):
        """Test line SVG conversion."""
        line = ShapeElement.line(
            x1=0,
            y1=0,
            x2=100,
            y2=100,
        )
        svg = line.to_svg()
        assert "<line" in svg
        assert 'x1="0"' in svg
        assert 'y1="0"' in svg
        assert 'x2="100"' in svg
        assert 'y2="100"' in svg

    def test_svg_with_fill(self):
        """Test SVG with fill color."""
        style = ShapeStyle(fill_color="#FF0000", fill_opacity=0.5)
        rect = ShapeElement.rectangle(
            x=0,
            y=0,
            width=100,
            height=100,
            style=style,
        )
        svg = rect.to_svg()
        assert "fill:#FF0000" in svg
        assert "fill-opacity:0.5" in svg

    def test_svg_with_stroke(self):
        """Test SVG with stroke."""
        style = ShapeStyle(
            stroke_color="#0000FF",
            stroke_width=5,
            stroke_opacity=0.8,
        )
        rect = ShapeElement.rectangle(
            x=0,
            y=0,
            width=100,
            height=100,
            style=style,
        )
        svg = rect.to_svg()
        assert "stroke:#0000FF" in svg
        assert "stroke-width:5" in svg
        assert "stroke-opacity:0.8" in svg

    def test_svg_with_fill_and_stroke(self):
        """Test SVG with both fill and stroke."""
        style = ShapeStyle(
            fill_color="#00FF00",
            fill_opacity=1.0,
            stroke_color="#000000",
            stroke_width=2,
            stroke_opacity=1.0,
        )
        rect = ShapeElement.rectangle(
            x=0,
            y=0,
            width=100,
            height=100,
            style=style,
        )
        svg = rect.to_svg()
        assert "fill:#00FF00" in svg
        assert "stroke:#000000" in svg

    def test_svg_no_fill(self):
        """Test SVG with no fill."""
        style = ShapeStyle(fill_color=None)
        rect = ShapeElement.rectangle(
            x=0,
            y=0,
            width=100,
            height=100,
            style=style,
        )
        svg = rect.to_svg()
        assert "fill:none" in svg

    def test_svg_no_stroke(self):
        """Test SVG with no stroke (stroke_width=0)."""
        style = ShapeStyle(stroke_width=0)
        rect = ShapeElement.rectangle(
            x=0,
            y=0,
            width=100,
            height=100,
            style=style,
        )
        svg = rect.to_svg()
        # Should not include stroke properties when width is 0
        assert "stroke-width" not in svg


class TestShapeElementRepr:
    """ShapeElement __repr__ tests."""

    def test_repr(self):
        """Test __repr__ method."""
        rect = ShapeElement.rectangle(x=0, y=0, width=100, height=100)
        assert repr(rect) == "ShapeElement(rectangle)"

    def test_repr_circle(self):
        """Test __repr__ for circle."""
        circle = ShapeElement.circle(cx=0, cy=0, radius=50)
        assert repr(circle) == "ShapeElement(circle)"


class TestShapeElementEdgeCases:
    """ShapeElement edge case tests."""

    def test_zero_size_rectangle(self):
        """Test rectangle with zero size."""
        rect = ShapeElement.rectangle(x=0, y=0, width=0, height=0)
        assert rect.params["width"] == 0
        assert rect.params["height"] == 0

    def test_negative_time_range(self):
        """Test shape with negative time range."""
        rect = ShapeElement.rectangle(
            x=0,
            y=0,
            width=100,
            height=100,
            start_time=5.0,
            end_time=2.0,
        )
        assert rect.duration == -3.0

    def test_style_post_init(self):
        """Test that style is initialized in __post_init__."""
        element = ShapeElement(
            shape_type=ShapeType.RECTANGLE,
            params={"x": 0, "y": 0, "width": 100, "height": 100},
        )
        assert element.style is not None
        assert isinstance(element.style, ShapeStyle)
