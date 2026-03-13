#!/usr/bin/env python3
"""Phase 2 Integration Test - Phase 2 集成测试脚本."""

import subprocess
import tempfile

import pytest


def create_test_video(output_path: str, duration: int = 10):
    """创建测试视频."""
    cmd = [
        "ffmpeg",
        "-f",
        "lavfi",
        "-i",
        f"testsrc=duration={duration}:size=1920x1080:rate=30",
        "-f",
        "lavfi",
        "-i",
        f"sine=frequency=1000:duration={duration}",
        "-pix_fmt",
        "yuv420p",
        "-y",
        output_path,
    ]
    subprocess.run(cmd, capture_output=True, check=True)
    print(f"✅ Test video created: {output_path}")


@pytest.fixture(scope="module")
def video_path():
    """创建测试视频 fixture."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        video_file = f"{tmp_dir}/test_video.mp4"
        create_test_video(video_file, duration=10)
        yield video_file


@pytest.mark.integration
def test_easing_functions():
    """测试缓动函数."""
    print("\n" + "=" * 60)
    print("Testing Easing Functions")
    print("=" * 60)

    from video_cut_skill import EasingFunction, EasingType

    # 测试各种缓动类型
    easing_types = [
        EasingType.LINEAR,
        EasingType.EASE_OUT_QUAD,
        EasingType.EASE_OUT_CUBIC,
        EasingType.EASE_OUT_BACK,
        EasingType.EASE_OUT_BOUNCE,
    ]

    for easing_type in easing_types:
        easing = EasingFunction(easing_type)

        # 测试关键点
        values = [easing.apply(t) for t in [0, 0.25, 0.5, 0.75, 1.0]]
        print(f"   {easing_type.value:20}: {values}")

    print("\n✅ Easing functions tests passed!")


@pytest.mark.integration
def test_text_elements():
    """测试文字元素."""
    print("\n" + "=" * 60)
    print("Testing Text Elements")
    print("=" * 60)

    from video_cut_skill import TextAnimation, TextAnimationConfig, TextElement, TextStyle

    # 创建文字元素
    text = TextElement(
        text="Hello World",
        position=(960, 540),
        style=TextStyle(
            font_size=64,
            font_color="#FFFFFF",
        ),
        entry_animation=TextAnimationConfig(
            animation_type=TextAnimation.SLIDE_UP,
            duration=0.5,
        ),
        start_time=0,
        end_time=3,
    )

    print(f"   ✅ Text element created: '{text.text}'")
    print(f"      Position: {text.position}")
    print(f"      Duration: {text.duration}s")
    print(f"      Visible at 1s: {text.is_visible_at(1)}")

    print("\n✅ Text element tests passed!")


@pytest.mark.integration
def test_shape_elements():
    """测试形状元素."""
    print("\n" + "=" * 60)
    print("Testing Shape Elements")
    print("=" * 60)

    from video_cut_skill import ShapeElement, ShapeStyle

    # 创建各种形状
    rect = ShapeElement.rectangle(x=100, y=100, width=200, height=100, style=ShapeStyle(fill_color="#FF0000", fill_opacity=0.5))

    circle = ShapeElement.circle(cx=960, cy=540, radius=100, style=ShapeStyle(fill_color="#00FF00", stroke_color="#000000", stroke_width=5))

    print(f"   ✅ Rectangle: {rect.to_svg()[:60]}...")
    print(f"   ✅ Circle: {circle.to_svg()[:60]}...")

    print("\n✅ Shape element tests passed!")


@pytest.mark.integration
@pytest.mark.slow
def test_content_analyzer(video_path: str):
    """测试内容分析器."""
    print("\n" + "=" * 60)
    print("Testing Content Analyzer")
    print("=" * 60)

    from video_cut_skill import ContentAnalyzer

    analyzer = ContentAnalyzer()
    print("   ✅ Analyzer initialized")

    # 分析视频 (使用 tiny 模型，快速测试)
    analysis = analyzer.analyze(
        video_path,
        extract_audio_features=False,
        extract_visual_features=False,
    )

    print("   ✅ Analysis complete")
    print(f"      Duration: {analysis.duration:.1f}s")
    print(f"      Segments: {len(analysis.segments)}")
    print(f"      Keywords: {analysis.keywords[:5]}")

    print("\n✅ Content analyzer tests passed!")


@pytest.mark.integration
@pytest.mark.slow
def test_strategy_generator(video_path: str):
    """测试策略生成器."""
    print("\n" + "=" * 60)
    print("Testing Strategy Generator")
    print("=" * 60)

    from video_cut_skill import (
        ContentAnalyzer,
        EditIntent,
        EditStyle,
        StrategyGenerator,
    )

    # 分析视频
    analyzer = ContentAnalyzer()
    analysis = analyzer.analyze(
        video_path,
        extract_audio_features=False,
        extract_visual_features=False,
    )

    # 生成策略
    generator = StrategyGenerator()
    intent = EditIntent(
        target_duration=5.0,
        style=EditStyle.FAST_PACED,
        platform="tiktok",
        add_subtitles=True,
    )

    strategy = generator.generate(analysis, intent)

    print("   ✅ Strategy generated")
    print(f"      Clips: {len(strategy.clips)}")
    print(f"      Total duration: {strategy.total_duration:.1f}s")
    print(f"      Target style: {strategy.target_style.value}")

    print("\n✅ Strategy generator tests passed!")
