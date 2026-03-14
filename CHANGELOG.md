# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Unified `AutoEditor` class supporting both smart and basic modes via `use_smart_transcriber` flag
- Type hints improved across the codebase (mypy now passes with no errors)
- Code review report (`docs/CODE_REVIEW_REPORT.md`)

### Changed
- **BREAKING**: Merged `auto_editor.py` and `auto_editor_enhanced.py` into single `AutoEditor` class
  - Use `AutoEditor(use_smart_transcriber=True)` for smart transcription with dynamic model selection
  - Use `AutoEditor(use_smart_transcriber=False)` for basic mode with scene detection
- Renamed integration test files for clarity:
  - `test9.py` → `test_end_to_end.py`
  - `test_phase1.py` → `test_whisper_base.py`
  - `test_phase2.py` → `test_smart_transcribe.py`

### Removed
- Redundant documentation files:
  - `docs/quickstart.md` (content merged into README)
  - `docs/installation.md` (content merged into README)
  - `docs/development/phase1-log.md` (archived)
  - `docs/development/phase2-log.md` (archived)
  - `docs/testing/test9-summary.md` (superseded by TEST_REPORT.md)

### Security
- Fixed potential command injection vulnerabilities by removing all `shell=True` from subprocess calls in `smart_transcriber.py`

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
