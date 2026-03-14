# Video Cut Skill Documentation

智能视频剪辑 Skill for OpenClaw Agent

## Quick Links

- [GitHub Repository](https://github.com/ZhaofanQiu/video_cut_skill)
- [README](https://github.com/ZhaofanQiu/video_cut_skill/blob/main/README.md) - Installation and quick start
- [Model Management](models.md)
- [API Reference](api/index.md)
- [Testing Guide](testing-guide.md)
- [Configuration](configuration.md)

## Features

### ✅ Phase 1: Core Foundation
- 🔧 **FFmpeg Engine**: Video cutting, merging, conversion
- 🎵 **Speech Recognition**: Whisper integration for transcription
- 📐 **Scene Detection**: Automatic scene segmentation
- 📝 **Subtitle Generation**: SRT/ASS export

### ✅ Phase 2: Smart Features
- 🤖 **AI Content Analysis**: Speech + visual understanding
- 🎯 **Smart Editing Strategy**: Platform adaptation, style selection
- ✨ **Motion Graphics**: Dynamic text, shapes, easing animations
- 🎬 **One-Click Editing**: AutoEditor automation

### ✅ Phase 3: Production Features
- 🚀 **GPU Acceleration**: CUDA auto-detection
- 💾 **Cache System**: Transcription and scene detection caching
- 🔊 **Audio Enhancement**: LUFS normalization, noise reduction
- 🛡️ **Error Handling**: Structured logging, graceful degradation

### 🚧 Phase 4: Advanced Features (Planned)
- 🎨 Color grading, LUT filters
- 🔊 Audio enhancement, beat detection
- 🧠 Generative titles/summaries

## Installation

```bash
# Clone repository
git clone https://github.com/ZhaofanQiu/video_cut_skill.git
cd video_cut_skill

# Install Python package
pip install -e .
```

See [README](https://github.com/ZhaofanQiu/video_cut_skill/blob/main/README.md) for detailed instructions.

## Quick Start

### Basic Editing

```python
from video_cut_skill import AutoEditor, EditConfig

editor = AutoEditor()
result = editor.process_video(
    "input.mp4",
    EditConfig(
        target_duration=60,
        aspect_ratio="9:16",
        add_subtitles=True,
        output_path="output.mp4"
    )
)
```

### AI Content Analysis

```python
from video_cut_skill import ContentAnalyzer

analyzer = ContentAnalyzer()
analysis = analyzer.analyze("video.mp4")

print(f"Keywords: {analysis.keywords}")
print(f"Highlights: {len(analysis.highlight_candidates)}")
```

### Motion Graphics

```python
from video_cut_skill import TextElement, TextStyle, TextAnimation

text = TextElement(
    text="Hello World",
    position=(960, 540),
    style=TextStyle(font_size=64, font_color="#FFFFFF"),
    entry_animation=TextAnimationConfig(
        animation_type=TextAnimation.SLIDE_UP,
        duration=0.5
    ),
    start_time=0,
    end_time=3
)
```

See [README](https://github.com/ZhaofanQiu/video_cut_skill/blob/main/README.md) for more examples.

## Documentation Structure

### Getting Started
- [README](https://github.com/ZhaofanQiu/video_cut_skill/blob/main/README.md) - Installation and quick start
- [Model Management](models.md) - Whisper model download guide
- [Troubleshooting](troubleshooting.md) - Common issues and solutions
- [Configuration](configuration.md) - Complete configuration reference

### Development
- [Testing Guide](testing-guide.md) - How to run tests
- [Architecture Decisions](adr/README.md) - Design decision records (ADR)

### API Reference
- [Core API](api/index.md) - FFmpeg wrapper and models

### Reports
- [Test Report](TEST_REPORT.md) - Complete test results
- [Integration Guide](INTEGRATION.md) - Integration documentation
- [Code Review Report](CODE_REVIEW_REPORT.md) - Code quality analysis

## Model Management

Before using Whisper features, download models:

```bash
# Download models
python scripts/download_models.py tiny base

# List downloaded models
python scripts/download_models.py --list
```

See [Model Management](models.md) for details.

## Testing

```bash
# Run all tests
pytest tests/ -v

# Unit tests only
pytest tests/unit/ -v

# Integration tests
pytest tests/integration/ -v
```

## Version History

See [CHANGELOG](https://github.com/ZhaofanQiu/video_cut_skill/blob/main/CHANGELOG.md) for complete version history.

- **v0.3.1** (2026-03-14) - Unified AutoEditor, type safety, documentation
- **v0.3.0** (2026-03-14) - SmartTranscriber, tiered transcription strategy
- **v0.2.0** (2026-03-14) - Phase 2: AI Analysis, Strategy, Motion Graphics
- **v0.1.0** (2026-03-13) - Phase 1: Core foundation

## License

MIT License - See [LICENSE](https://github.com/ZhaofanQiu/video_cut_skill/blob/main/LICENSE) for details.
