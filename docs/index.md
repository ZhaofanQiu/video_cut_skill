# Video Cut Skill Documentation

智能视频剪辑 Skill for OpenClaw Agent

## Quick Links

- [GitHub Repository](https://github.com/ZhaofanQiu/video_cut_skill)
- [README](https://github.com/ZhaofanQiu/video_cut_skill/blob/main/README.md) - Installation and quick start
- [ROADMAP](../ROADMAP.md) - Future development plans
- [CHANGELOG](../CHANGELOG.md) - Version history
- [Model Management](models.md)
- [API Reference](api/index.md)
- [Testing Guide](testing-guide.md)
- [Configuration](configuration.md)

## Features

### ✅ Phase 1: Core Foundation (v0.1.0)
- 🔧 **FFmpeg Engine**: Video cutting, merging, conversion
- 🎵 **Speech Recognition**: Whisper integration for transcription
- 📐 **Scene Detection**: Automatic scene segmentation
- 📝 **Subtitle Generation**: SRT/ASS export

### ✅ Phase 2: Smart Features (v0.2.0)
- 🤖 **AI Content Analysis**: Speech + visual understanding
- 🎯 **Smart Editing Strategy**: Platform adaptation, style selection
- ✨ **Motion Graphics**: Dynamic text, shapes, easing animations
- 🎬 **One-Click Editing**: AutoEditor automation

### ✅ Phase 3: Production Features (v0.3.0)
- 🚀 **GPU Acceleration**: CUDA auto-detection
- 💾 **Cache System**: Transcription and scene detection caching
- 🔊 **Audio Enhancement**: LUFS normalization, noise reduction
- 🛡️ **Error Handling**: Structured logging, graceful degradation

### ✅ Phase 4: Interactive Features (v0.4.0) ⭐ Latest
- 🎙️ **InteractiveEditor**: Multi-round conversational video editing
- 💰 **CostGuardian**: Real-time cost estimation and confirmation
- 💾 **Session Management**: Persistent session state
- 🔗 **Aliyun ASR**: Paraformer + Qwen3-ASR-Flash integration

### 🚧 Phase 5: Advanced Features (Planned)
- 🎵 Beat detection, smart卡点
- 🎨 Advanced subtitle animations
- 🧠 Generative AI integration

See [ROADMAP](../ROADMAP.md) for detailed future plans.

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

### AutoEditor - One-Click Editing

```python
from video_cut_skill import AutoEditor, EditConfig

editor = AutoEditor(analysis_mode="audio")
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

### InteractiveEditor - Conversational Editing (v0.4.0+)

```python
from video_cut_skill import InteractiveEditor, Config

config = Config()
editor = InteractiveEditor(config=config)

# Step 1: Analyze video
response = editor.analyze("input.mp4")
session_id = response.data["session_id"]

# Step 2: Edit with natural language
edit_response = editor.edit(
    session_id,
    "Extract highlights about AI technology, keep it under 30 seconds"
)

# Step 3: Confirm and export
if edit_response.state == "awaiting_confirm":
    confirm_response = editor.confirm_edit(session_id)
    print(f"Output: {confirm_response.data['output_path']}")
```

### AI Content Analysis

```python
from video_cut_skill import ContentAnalyzer

analyzer = ContentAnalyzer()
analysis = analyzer.analyze("video.mp4")

print(f"Keywords: {analysis.keywords}")
print(f"Highlights: {len(analysis.highlight_candidates)}")
```

See [README](https://github.com/ZhaofanQiu/video_cut_skill/blob/main/README.md) for more examples.

## Documentation Structure

### Getting Started
- [README](https://github.com/ZhaofanQiu/video_cut_skill/blob/main/README.md) - Installation and quick start
- [ROADMAP](../ROADMAP.md) - Development roadmap and future plans
- [CHANGELOG](../CHANGELOG.md) - Version history
- [Model Management](models.md) - Whisper model download guide
- [Troubleshooting](troubleshooting.md) - Common issues and solutions
- [Configuration](configuration.md) - Complete configuration reference

### Development
- [Testing Guide](testing-guide.md) - How to run tests
- [Architecture Decisions](adr/README.md) - Design decision records (ADR)
- [Contributing](../docs/development/contributing.md) - How to contribute

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

Current status: **433 passed, 4 skipped**

## Version History

See [CHANGELOG](../CHANGELOG.md) for complete version history.

- **v0.4.0** (2026-03-16) - InteractiveEditor, Aliyun ASR, CostGuardian
- **v0.3.1** (2026-03-14) - Unified AutoEditor, type safety, documentation
- **v0.3.0** (2026-03-14) - SmartTranscriber, tiered transcription strategy
- **v0.2.0** (2026-03-14) - Phase 2: AI Analysis, Strategy, Motion Graphics
- **v0.1.0** (2026-03-13) - Phase 1: Core foundation

## License

MIT License - See [LICENSE](https://github.com/ZhaofanQiu/video_cut_skill/blob/main/LICENSE) for details.
