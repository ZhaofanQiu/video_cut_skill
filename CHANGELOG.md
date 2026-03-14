# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **New API**: `analysis_mode` parameter replaces `use_smart_transcriber`
  - `"audio"` (default): Audio analysis mode - speech recognition, dynamic model selection
  - `"visual"`: Visual analysis mode - scene detection, shot segmentation
  - Backward compatibility: `use_smart_transcriber` still works with deprecation warning
- Hybrid mode planned for future release (combining both audio and visual analysis)

### Changed
- **BREAKING**: `AutoEditor(use_smart_transcriber=...)` → `AutoEditor(analysis_mode="audio"/"visual")`
  - Clear naming reflects actual capabilities
  - Audio mode: SmartTranscriber for speech-based content
  - Visual mode: SceneDetector for visual-based content

### Deprecated
- `use_smart_transcriber` parameter - use `analysis_mode` instead

## [0.3.1] - 2026-03-14

### Added
- Comprehensive test suite achieving 81% code coverage
- New test files: test_logging, test_easing, test_analyzer, test_auto_editor, test_audio, test_cache_utils, test_scene_detector, test_strategy, test_hardware, test_transcriber, test_shape
- Motion graphics easing functions and shape elements
- Hardware detection utilities (`utils/hardware.py`)
- Retry mechanisms with exponential backoff (`utils/retry.py`)
- Cache management system (`utils/cache.py`)
- Structured logging support (`utils/logging.py`)

### Changed
- Improved `FFmpegWrapper` error handling with user-friendly messages
- Enhanced scene detection with content-aware algorithms

## [0.3.0] - 2026-03-01

### Added
- **Phase 3.5**: Cloud service architecture planning
- **Phase 3**: Motion graphics system with animations and text rendering
- **Phase 2.5**: Audio analysis and enhancement tools
- **Phase 2**: AI-powered editing with strategy generation
- **Phase 1**: Core video editing capabilities
  - FFmpeg wrapper with comprehensive video operations
  - Whisper integration for transcription
  - Scene detection using content analysis
  - Basic editing: cut, concatenate, format conversion

### Features
- Video information extraction
- Audio extraction and verification
- Video cutting with precise timing
- Aspect ratio conversion (horizontal/vertical)
- Speech-to-text with multiple Whisper models
- Subtitle generation and burning
- Scene-based video splitting
- Keyword-based highlight extraction
- Content analysis for automatic editing
- Strategy generation for different platforms (TikTok, educational, etc.)

## [0.2.0] - 2025-02-15

### Added
- Initial project structure
- Basic FFmpeg integration
- Whisper transcription support
- Scene detection prototype

## [0.1.0] - 2025-01-20

### Added
- Project initialization
- Basic video processing capabilities
- Initial documentation

---

## Versioning Guide

- **MAJOR**: Breaking changes that require user code modifications
- **MINOR**: New features, backwards compatible
- **PATCH**: Bug fixes, backwards compatible
