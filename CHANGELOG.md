# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.4.0] - 2026-03-16

### Added
- **InteractiveEditor**: 全新交互式视频编辑器 (v0.4.0 核心功能)
  - `analyze()`: 视频分析和语义理解，支持阿里云 Paraformer/Qwen3-ASR-Flash
  - `edit()`: 自然语言指令编辑，智能理解剪辑意图
  - `confirm_edit()`: 确认并执行剪辑策略
  - `feedback()`: 多轮反馈优化，支持迭代精调
- **阿里云 ASR 集成**: 支持多模型语音识别
  - `paraformer-realtime-v2`: 默认稳定模型
  - `qwen3-asr-flash-realtime`: 更高准确率推荐模型
- **CostGuardian**: 实时成本估算和用户确认机制
  - 视频时长检查，超长视频需要确认
  - 成本估算，超额成本需要确认
  - 自动降级策略，无 API Key 时回退到本地 Whisper
- **SessionManager**: 会话持久化和管理
  - 会话状态跟踪 (CREATED -> ANALYZED -> EDITING -> COMPLETED)
  - 语义数据缓存，避免重复转录
  - 会话历史记录
- **智能字幕**: LLM 驱动的字幕断句和优化
  - 支持横屏/竖屏不同字数限制
  - 语义断句，避免截断句子
- **FileUploader**: 阿里云 OSS 文件上传支持

### Changed
- **工作目录**: AutoEditor 默认使用临时目录而非当前目录，避免污染项目
- **配置验证**: API Key 缺失时改为警告而非错误，支持纯本地 Whisper 模式
- **analysis_mode**: 更清晰的新 API 替代 `use_smart_transcriber`
  - `"audio"`: 音频分析模式，适合访谈、教学、播客
  - `"visual"`: 视觉分析模式，适合电影、MV

### Fixed
- 修复单元测试: `test_extract_highlights_smart_mode` 断言修正
- 修复集成测试: `test_auto_editor` 使用临时目录避免文件冲突
- 修复字幕生成: 优化字幕断句逻辑

### Deprecated
- `use_smart_transcriber` 参数: 使用 `analysis_mode` 替代
- `interactive_editor_v2.py`: 已删除，功能合并到主编辑器

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
