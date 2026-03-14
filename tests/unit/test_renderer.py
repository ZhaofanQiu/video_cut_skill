"""Tests for motion graphics renderer."""

from unittest.mock import MagicMock, patch

import pytest

from video_cut_skill.motion_graphics.elements.shape import ShapeElement, ShapeStyle
from video_cut_skill.motion_graphics.elements.text import TextAnimation, TextElement, TextStyle
from video_cut_skill.motion_graphics.renderer import MGSpec, MotionGraphicsRenderer


class TestMGSpec:
    """MGSpec tests."""

    def test_default_initialization(self):
        """Test MGSpec with default values."""
        spec = MGSpec()

        assert spec.width == 1920
        assert spec.height == 1080
        assert spec.duration == 5.0
        assert spec.fps == 30
        assert spec.background_color is None
        assert spec.elements == []

    def test_custom_initialization(self):
        """Test MGSpec with custom values."""
        spec = MGSpec(
            width=1080,
            height=1920,
            duration=10.0,
            fps=60,
            background_color="#FFFFFF",
        )

        assert spec.width == 1080
        assert spec.height == 1920
        assert spec.duration == 10.0
        assert spec.fps == 60
        assert spec.background_color == "#FFFFFF"

    def test_with_elements(self):
        """Test MGSpec with elements."""
        text_element = TextElement(
            text="Hello",
            position=(100, 200),
            start_time=0,
            end_time=5,
        )

        spec = MGSpec(elements=[text_element])

        assert len(spec.elements) == 1
        assert spec.elements[0].text == "Hello"


class TestMotionGraphicsRenderer:
    """MotionGraphicsRenderer tests."""

    @pytest.fixture
    def temp_output(self, tmp_path):
        """Temporary output path."""
        return tmp_path / "output.mp4"

    @pytest.fixture
    def renderer(self):
        """Renderer instance."""
        return MotionGraphicsRenderer()

    @pytest.fixture
    def simple_spec(self):
        """Simple MGSpec for testing."""
        return MGSpec(
            width=320,
            height=240,
            duration=1.0,
            fps=10,
        )

    def test_initialization_default(self):
        """Test renderer initialization with default ffmpeg path."""
        renderer = MotionGraphicsRenderer()
        assert renderer.ffmpeg_path == "ffmpeg"

    def test_initialization_custom_ffmpeg(self):
        """Test renderer initialization with custom ffmpeg path."""
        renderer = MotionGraphicsRenderer(ffmpeg_path="/usr/bin/ffmpeg")
        assert renderer.ffmpeg_path == "/usr/bin/ffmpeg"

    @patch("subprocess.run")
    @patch("PIL.Image.Image.save")
    @patch("tempfile.TemporaryDirectory")
    def test_render_basic(
        self,
        mock_temp_dir,
        mock_save,
        mock_subprocess,
        renderer,
        simple_spec,
        temp_output,
    ):
        """Test basic render functionality."""
        # Mock temp directory
        mock_temp_dir.return_value.__enter__ = MagicMock(return_value="/tmp/test_frames")
        mock_temp_dir.return_value.__exit__ = MagicMock(return_value=False)

        # Mock subprocess for ffmpeg
        mock_subprocess.return_value = MagicMock(returncode=0)

        result = renderer.render(simple_spec, temp_output)

        assert result == temp_output
        mock_subprocess.assert_called_once()

    def test_generate_frames_creates_correct_number(self, renderer, simple_spec, tmp_path):
        """Test that _generate_frames creates correct number of frames."""
        frame_dir = tmp_path / "frames"
        frame_dir.mkdir()

        with patch("PIL.Image.Image.save") as mock_save:
            renderer._generate_frames(simple_spec, str(frame_dir))

            # Should generate duration * fps = 1.0 * 10 = 10 frames
            assert mock_save.call_count == 10

    def test_draw_text_element(self, renderer):
        """Test drawing text element."""
        from PIL import Image

        img = Image.new("RGB", (320, 240), "#000000")
        text_element = TextElement(
            text="Test",
            position=(100, 100),
            start_time=0,
            end_time=1,
            style=TextStyle(font_size=24, font_color="#FFFFFF"),
        )

        # Should not raise exception
        renderer._draw_element(img, text_element, 0.5)

    def test_draw_shape_element(self, renderer):
        """Test drawing shape element."""
        from PIL import Image

        img = Image.new("RGB", (320, 240), "#000000")
        shape_element = ShapeElement.rectangle(
            x=50,
            y=50,
            width=100,
            height=100,
            start_time=0,
            end_time=1,
        )

        # Should not raise exception
        renderer._draw_element(img, shape_element, 0.5)

    def test_is_visible_at_time(self, renderer, simple_spec, tmp_path):
        """Test element visibility at different times."""
        frame_dir = tmp_path / "frames"
        frame_dir.mkdir()

        # Create element visible only at specific time
        text_element = TextElement(
            text="Test",
            position=(100, 100),
            start_time=0.2,
            end_time=0.8,
        )

        assert text_element.is_visible_at(0.1) is False  # Before start
        assert text_element.is_visible_at(0.5) is True  # During
        assert text_element.is_visible_at(0.9) is False  # After end

    @patch("subprocess.run")
    def test_encode_video(self, mock_subprocess, renderer, tmp_path):
        """Test video encoding with ffmpeg."""
        mock_subprocess.return_value = MagicMock(returncode=0)

        frame_dir = tmp_path / "frames"
        frame_dir.mkdir()
        output_path = tmp_path / "output.mp4"

        # Create a dummy frame file
        (frame_dir / "frame_00000.png").write_text("dummy")

        renderer._encode_video(str(frame_dir), output_path, fps=30, duration=1.0)

        mock_subprocess.assert_called_once()
        cmd = mock_subprocess.call_args[0][0]
        assert "ffmpeg" in cmd
        assert "30" in cmd  # fps

    def test_render_with_text_element(self, renderer, temp_output):
        """Test render with text element included."""
        text_element = TextElement(
            text="Hello World",
            position=(100, 100),
            start_time=0,
            end_time=1,
            style=TextStyle(font_size=32, font_color="#FF0000"),
        )

        spec = MGSpec(
            width=640,
            height=480,
            duration=0.5,
            fps=10,
            elements=[text_element],
        )

        with patch("subprocess.run") as mock_subprocess:
            mock_subprocess.return_value = MagicMock(returncode=0)

            result = renderer.render(spec, temp_output)

            assert result == temp_output

    def test_render_with_shape_element(self, renderer, temp_output):
        """Test render with shape element included."""
        shape_element = ShapeElement.circle(
            cx=320,
            cy=240,
            radius=100,
            start_time=0,
            end_time=1,
            style=ShapeStyle(fill_color="#00FF00"),
        )

        spec = MGSpec(
            width=640,
            height=480,
            duration=0.5,
            fps=10,
            elements=[shape_element],
        )

        with patch("subprocess.run") as mock_subprocess:
            mock_subprocess.return_value = MagicMock(returncode=0)

            result = renderer.render(spec, temp_output)

            assert result == temp_output

    def test_render_multiple_elements(self, renderer, temp_output):
        """Test render with multiple elements."""
        text_element = TextElement(
            text="Title",
            position=(320, 100),
            start_time=0,
            end_time=2,
        )

        shape_element = ShapeElement.rectangle(
            x=100,
            y=200,
            width=200,
            height=100,
            start_time=0.5,
            end_time=1.5,
        )

        spec = MGSpec(
            width=640,
            height=480,
            duration=1.0,
            fps=10,
            elements=[text_element, shape_element],
        )

        with patch("subprocess.run") as mock_subprocess:
            mock_subprocess.return_value = MagicMock(returncode=0)

            result = renderer.render(spec, temp_output)

            assert result == temp_output

    def test_text_element_with_animation(self, renderer):
        """Test text element with entry animation."""
        from video_cut_skill.motion_graphics.elements.text import TextAnimationConfig

        text_element = TextElement(
            text="Animated",
            position=(200, 200),
            start_time=0,
            end_time=1,
            entry_animation=TextAnimationConfig(
                animation_type=TextAnimation.FADE,
                duration=0.5,
            ),
        )

        from PIL import Image

        img = Image.new("RGB", (320, 240), "#000000")

        # Should not raise exception
        renderer._draw_element(img, text_element, 0.3)
