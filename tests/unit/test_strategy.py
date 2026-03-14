"""Tests for strategy module."""

from pathlib import Path

import pytest

from video_cut_skill.ai.strategy import (
    ClipSpec,
    EditingStrategy,
    EditIntent,
    EditStyle,
    LayoutType,
    StrategyGenerator,
    TextOverlaySpec,
)


class TestEditStyle:
    """EditStyle enum tests."""

    def test_edit_style_values(self):
        """Test EditStyle enum values."""
        assert EditStyle.FAST_PACED.value == "fast_paced"
        assert EditStyle.MODERATE.value == "moderate"
        assert EditStyle.SLOW.value == "slow"
        assert EditStyle.TUTORIAL.value == "tutorial"
        assert EditStyle.VLOG.value == "vlog"


class TestLayoutType:
    """LayoutType enum tests."""

    def test_layout_type_values(self):
        """Test LayoutType enum values."""
        assert LayoutType.ORIGINAL.value == "original"
        assert LayoutType.VERTICAL.value == "vertical"
        assert LayoutType.SQUARE.value == "square"
        assert LayoutType.WIDESCREEN.value == "widescreen"


class TestClipSpec:
    """ClipSpec dataclass tests."""

    def test_clip_spec_creation(self):
        """Test creating ClipSpec."""
        clip = ClipSpec(start_time=0.0, end_time=10.0)
        assert clip.start_time == 0.0
        assert clip.end_time == 10.0
        assert clip.layout == LayoutType.ORIGINAL
        assert clip.zoom_level == 1.0
        assert clip.add_transition is True

    def test_duration_property(self):
        """Test duration property."""
        clip = ClipSpec(start_time=5.0, end_time=15.0)
        assert clip.duration == 10.0

    def test_clip_spec_with_custom_values(self):
        """Test ClipSpec with custom values."""
        clip = ClipSpec(
            start_time=0.0,
            end_time=5.0,
            layout=LayoutType.VERTICAL,
            crop_region=(100, 100, 800, 600),
            zoom_level=1.5,
            add_transition=False,
            transition_type="slide",
        )
        assert clip.layout == LayoutType.VERTICAL
        assert clip.crop_region == (100, 100, 800, 600)
        assert clip.zoom_level == 1.5
        assert clip.add_transition is False
        assert clip.transition_type == "slide"


class TestTextOverlaySpec:
    """TextOverlaySpec dataclass tests."""

    def test_text_overlay_creation(self):
        """Test creating TextOverlaySpec."""
        overlay = TextOverlaySpec(
            text="Hello",
            start_time=0.0,
            end_time=5.0,
        )
        assert overlay.text == "Hello"
        assert overlay.start_time == 0.0
        assert overlay.end_time == 5.0
        assert overlay.position == (960, 540)
        assert overlay.style == "default"
        assert overlay.animation == "fade"


class TestEditingStrategy:
    """EditingStrategy dataclass tests."""

    @pytest.fixture
    def sample_clips(self):
        """Create sample clips."""
        return [
            ClipSpec(start_time=0.0, end_time=5.0),
            ClipSpec(start_time=5.0, end_time=10.0),
        ]

    def test_strategy_creation(self, sample_clips):
        """Test creating EditingStrategy."""
        strategy = EditingStrategy(
            target_duration=60.0,
            clips=sample_clips,
        )
        assert strategy.target_duration == 60.0
        assert strategy.target_aspect_ratio == (16, 9)
        assert strategy.target_style == EditStyle.MODERATE
        assert len(strategy.clips) == 2

    def test_total_duration_property(self, sample_clips):
        """Test total_duration property."""
        strategy = EditingStrategy(
            target_duration=60.0,
            clips=sample_clips,
        )
        assert strategy.total_duration == 10.0

    def test_total_duration_empty_clips(self):
        """Test total_duration with empty clips."""
        strategy = EditingStrategy(target_duration=60.0, clips=[])
        assert strategy.total_duration == 0

    def test_validate_valid(self, sample_clips):
        """Test validate with valid strategy."""
        strategy = EditingStrategy(
            target_duration=60.0,
            clips=sample_clips,
        )
        assert strategy.validate() is True

    def test_validate_empty_clips(self):
        """Test validate with empty clips."""
        strategy = EditingStrategy(target_duration=60.0, clips=[])
        assert strategy.validate() is False

    def test_validate_duration_exceeded(self):
        """Test validate when duration exceeds target."""
        clips = [ClipSpec(start_time=0.0, end_time=100.0)]
        strategy = EditingStrategy(
            target_duration=60.0,
            clips=clips,
        )
        # 100 > 60 * 1.2 = 72, so should be invalid
        assert strategy.validate() is False


class TestEditIntent:
    """EditIntent dataclass tests."""

    def test_edit_intent_defaults(self):
        """Test EditIntent default values."""
        intent = EditIntent()
        assert intent.target_duration is None
        assert intent.platform == "general"
        assert intent.style == EditStyle.MODERATE
        assert intent.layout == LayoutType.ORIGINAL
        assert intent.keywords == []
        assert intent.description == ""
        assert intent.add_subtitles is True
        assert intent.add_music is False

    def test_edit_intent_custom_values(self):
        """Test EditIntent with custom values."""
        intent = EditIntent(
            target_duration=60.0,
            platform="tiktok",
            style=EditStyle.FAST_PACED,
            keywords=["python", "tutorial"],
            description="A Python tutorial video",
        )
        assert intent.target_duration == 60.0
        assert intent.platform == "tiktok"
        assert intent.style == EditStyle.FAST_PACED
        assert intent.keywords == ["python", "tutorial"]


class TestStrategyGenerator:
    """StrategyGenerator tests."""

    @pytest.fixture
    def generator(self):
        """Create StrategyGenerator instance."""
        return StrategyGenerator()

    @pytest.fixture
    def mock_analysis(self):
        """Create mock ContentAnalysis."""
        from video_cut_skill.ai.analyzer import ContentAnalysis, ContentSegment

        return ContentAnalysis(
            video_path=Path("/path/to/video.mp4"),
            duration=120.0,
            segments=[
                ContentSegment(start_time=0.0, end_time=10.0, importance_score=0.8),
                ContentSegment(start_time=10.0, end_time=25.0, importance_score=0.9),
                ContentSegment(start_time=25.0, end_time=40.0, importance_score=0.7),
            ],
            highlight_candidates=[
                ContentSegment(start_time=10.0, end_time=25.0, importance_score=0.9),
            ],
        )

    def test_initialization(self):
        """Test StrategyGenerator initialization."""
        generator = StrategyGenerator()
        assert generator.PLATFORM_PRESETS is not None
        assert "tiktok" in generator.PLATFORM_PRESETS
        assert "youtube" in generator.PLATFORM_PRESETS

    def test_platform_presets_structure(self, generator):
        """Test platform presets structure."""
        tiktok_preset = generator.PLATFORM_PRESETS["tiktok"]
        assert "aspect_ratio" in tiktok_preset
        assert "max_duration" in tiktok_preset
        assert "style" in tiktok_preset
        assert tiktok_preset["aspect_ratio"] == (9, 16)

    def test_apply_platform_preset_tiktok(self, generator):
        """Test applying TikTok preset."""
        intent = EditIntent(platform="tiktok")
        updated = generator._apply_platform_preset(intent)

        assert updated.target_duration is not None
        assert updated.style == EditStyle.FAST_PACED

    def test_apply_platform_preset_youtube(self, generator):
        """Test applying YouTube preset."""
        intent = EditIntent(platform="youtube")
        updated = generator._apply_platform_preset(intent)

        assert updated.style == EditStyle.MODERATE

    def test_apply_platform_preset_unknown(self, generator):
        """Test applying unknown platform preset."""
        intent = EditIntent(platform="unknown_platform")
        updated = generator._apply_platform_preset(intent)

        # Should return unchanged intent
        assert updated.platform == "unknown_platform"

    def test_generate_basic(self, generator, mock_analysis):
        """Test basic strategy generation."""
        intent = EditIntent(target_duration=30.0)
        strategy = generator.generate(mock_analysis, intent)

        assert isinstance(strategy, EditingStrategy)
        assert strategy.target_duration == 30.0
        assert len(strategy.clips) > 0

    def test_generate_with_platform(self, generator, mock_analysis):
        """Test strategy generation with platform."""
        intent = EditIntent(platform="tiktok")
        strategy = generator.generate(mock_analysis, intent)

        assert strategy.target_aspect_ratio == (9, 16)

    def test_generate_with_keywords(self, generator, mock_analysis):
        """Test strategy generation with keywords."""
        intent = EditIntent(
            target_duration=30.0,
            keywords=["important"],
        )
        strategy = generator.generate(mock_analysis, intent)

        assert isinstance(strategy, EditingStrategy)

    def test_generate_fast_paced_style(self, generator, mock_analysis):
        """Test strategy generation with fast paced style."""
        intent = EditIntent(
            target_duration=30.0,
            style=EditStyle.FAST_PACED,
        )
        strategy = generator.generate(mock_analysis, intent)

        assert strategy.target_style == EditStyle.FAST_PACED

    def test_generate_with_subtitles(self, generator, mock_analysis):
        """Test strategy generation with subtitles enabled."""
        intent = EditIntent(
            target_duration=30.0,
            add_subtitles=True,
        )
        strategy = generator.generate(mock_analysis, intent)

        assert strategy.add_subtitles is True

    def test_generate_no_segments(self, generator):
        """Test strategy generation with no segments."""
        from video_cut_skill.ai.analyzer import ContentAnalysis

        empty_analysis = ContentAnalysis(
            video_path=Path("/path/to/video.mp4"),
            duration=60.0,
            segments=[],
        )
        intent = EditIntent(target_duration=30.0)
        strategy = generator.generate(empty_analysis, intent)

        assert isinstance(strategy, EditingStrategy)

    def test_select_segments_with_keywords(self, generator, mock_analysis):
        """Test segment selection with keywords."""
        intent = EditIntent(
            target_duration=30.0,
            keywords=["test"],
        )
        segments = generator._select_segments(mock_analysis, 30.0, intent)

        assert isinstance(segments, list)

    def test_select_segments_fast_paced(self, generator, mock_analysis):
        """Test segment selection for fast paced style."""
        intent = EditIntent(
            target_duration=30.0,
            style=EditStyle.FAST_PACED,
        )
        segments = generator._select_segments(mock_analysis, 30.0, intent)

        assert isinstance(segments, list)

    def test_select_segments_slow(self, generator, mock_analysis):
        """Test segment selection for slow style."""
        intent = EditIntent(
            target_duration=30.0,
            style=EditStyle.SLOW,
        )
        segments = generator._select_segments(mock_analysis, 30.0, intent)

        assert isinstance(segments, list)

    def test_generate_clips(self, generator, mock_analysis):
        """Test clip generation."""
        from video_cut_skill.ai.analyzer import ContentSegment

        intent = EditIntent(target_duration=30.0, layout=LayoutType.VERTICAL)
        segments = [
            ContentSegment(start_time=0.0, end_time=10.0),
            ContentSegment(start_time=10.0, end_time=20.0),
        ]
        clips = generator._generate_clips(segments, intent)

        assert isinstance(clips, list)
        assert len(clips) == 2
        assert all(isinstance(c, ClipSpec) for c in clips)

    def test_generate_text_overlays(self, generator):
        """Test text overlay generation."""
        clips = [
            ClipSpec(start_time=0.0, end_time=5.0),
            ClipSpec(start_time=5.0, end_time=10.0),
        ]
        intent = EditIntent(target_duration=10.0)
        overlays = generator._generate_text_overlays(clips, intent)

        assert isinstance(overlays, list)
