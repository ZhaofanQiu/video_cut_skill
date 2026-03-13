# Video Cut Skill Documentation

## Quick Links

- [GitHub Repository](https://github.com/ZhaofanQiu/video_cut_skill)
- [Installation](installation.md)
- [Quick Start](quickstart.md)
- [API Reference](api/index.md)
- [Testing Guide](testing-guide.md)

## Features

- **AI-Powered Editing**: Intelligent clip selection and pacing
- **Speech Recognition**: Whisper integration for transcription
- **Scene Detection**: Automatic scene segmentation
- **Video Processing**: FFmpeg-based cutting, merging, and conversion
- **Multi-Platform**: Support for TikTok, YouTube, Bilibili, etc.

## Installation

```bash
pip install video-cut-skill
```

See [Installation Guide](installation.md) for detailed instructions.

## Quick Start

```python
from video_cut_skill import FFmpegWrapper, Transcriber, SceneDetector

# Video processing
wrapper = FFmpegWrapper()
info = wrapper.get_video_info("input.mp4")

# Speech recognition
transcriber = Transcriber(model_size="base")
result = transcriber.transcribe("video.mp4")

# Scene detection
detector = SceneDetector()
scenes = detector.detect("video.mp4")
```

See [Quick Start](quickstart.md) for more examples.

## Documentation Structure

- [Getting Started](installation.md) - Installation and setup
- [Quick Start](quickstart.md) - Basic usage examples
- [Testing Guide](testing-guide.md) - How to run tests
- [API Reference](api/index.md) - API documentation
- [Phase 1 Log](development/phase1-log.md) - Development details
