# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.5.0] - 2026-03-16

### Added
- **节拍检测 (Beat Detection)**: 音乐节拍检测与智能卡点
  - 多方法支持: `librosa` (推荐), `madmom`, `basic` (回退)
  - BPM 自动计算与重拍检测
  - 智能卡点剪辑方案生成
  - 视频片段对齐到节拍
  - 支持导出节拍标记到主流剪辑软件
  - `BeatSyncEditor`: 节拍同步编辑工作流

- **MG 模板引擎 (Template Engine)**: 可复用的动效模板系统
  - JSON/YAML 模板定义格式
  - 6种参数类型: `string`, `number`, `color`, `boolean`, `select`, `file`
  - 占位符替换系统: `{{param_name}}`
  - 4个内置模板:
    - `youtube_intro_v1`: YouTube 频道片头
    - `lower_third_v1`: 新闻风格字幕条
    - `quote_card_v1`: 引用卡片
    - `title_card_v1`: 章节标题卡片
  - 自定义模板注册与导入/导出

- **说话人识别 (Speaker Recognition)**: 语音活动检测与说话人分离
  - `VoiceActivityDetector`: WebRTC VAD 语音检测
  - `SpeakerDiarizer`: 说话人分离 (支持 pyannote 和基础回退)
  - 声纹嵌入与相似度计算
  - `SpeakerAwareEditor`: 集成到视频编辑流程
  - 支持导出带说话人标记的字幕 (SRT/VTT)

- **智能布局 (Smart Layout)**: 自动构图与多画幅适配
  - 8种构图规则: 中心构图、三分法、黄金分割、人脸居中、主体居中、头部空间、对称构图
  - 人脸检测: OpenCV Haar 级联分类器
  - 主体检测: 边缘检测与轮廓分析
  - 多画幅适配: 9:16, 16:9, 1:1, 4:5, 4:3, 21:9
  - `SmartLayoutEditor`: 自动裁剪与批量生成
  - 平台批量生成: 一次生成 TikTok/Instagram/YouTube 多版本

### Technical
- 新增 ~4,600 行代码，4个核心模块 + 完整单元测试
- 所有 P1 功能均支持依赖缺失时的优雅降级
- 完整类型注解和文档字符串

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
