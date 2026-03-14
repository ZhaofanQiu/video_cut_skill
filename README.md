# Video Cut Skill

智能视频剪辑 Skill for OpenClaw Agent

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 项目简介

Video Cut Skill 是一个专为 AI Agent 设计的智能视频剪辑工具，提供从原始视频到成片的自动化/半自动化处理能力。

### 当前版本: v0.3.1

## 核心特性

### ✅ Phase 1: 核心基础 (已完成)
- 🔧 **FFmpeg 引擎**: 视频剪辑、格式转换、音频提取
- 🎵 **语音识别**: Whisper 集成，支持多语言转录
- 📐 **场景检测**: PySceneDetect 自动场景分割
- 📝 **字幕生成**: SRT/ASS 格式导出

### ✅ Phase 2: 智能功能 (已完成)
- 🤖 **AI 内容分析**: 语音+视觉内容理解
- 🎯 **智能剪辑策略**: 平台适配、风格选择
- ✨ **Motion Graphics**: 动态文字、形状元素、缓动动画
- 🎬 **一键剪辑**: AutoEditor 自动化工作流

### ✅ Phase 3: 生产级强化 (已完成)
- 🚀 **GPU 加速**: CUDA 自动检测与加速（兼容无 GPU）
- 💾 **缓存系统**: 转录结果、场景检测缓存
- 🔊 **音频增强**: LUFS 音量标准化、降噪
- 🛡️ **错误处理**: 结构化日志、优雅降级

### 🚧 Phase 4: 智能功能深化 (规划中)
- 🎵 节拍检测、智能卡点
- 🎨 高级字幕动画
- 🧠 生成式 AI 集成

## 最新测试结果 (2026-03-14)

### 智能转录模块测试 ✅

| 测试项 | 状态 | 关键结果 |
|--------|------|----------|
| 端到端完整流程 | ✅ 通过 | 分级转录策略验证成功 (TINY+BASE) |
| 错误恢复与异常处理 | ✅ 通过 | 7项全部通过 |
| 性能压力测试 | ✅ 通过 | 31分钟视频稳定处理，无内存泄漏 |
| 批量处理测试 | ✅ 通过 | 4/5视频成功处理 |
| 集成兼容测试 | ✅ 通过 | 核心功能正常 |

### 新增功能

- **🧠 智能转录模块** (`SmartTranscriber`): 支持动态模型选择和静音检测
- **🎯 分级转录策略**: 完整视频用TINY快速分析，高光片段用BASE精准转录
- **🔇 静音检测**: 自动识别无音频视频，提供友好错误提示
- **📊 性能优化**: 31分钟视频8分钟处理完成，内存使用稳定

### 已知问题与限制

- **内存限制**: 仅支持 tiny/base 模型（small/medium/large 需要 2GB+/5GB+/10GB+）
- **并发控制**: 需要添加任务队列限制并发数（建议 max_concurrent=2）
- **依赖问题**: FFmpeg Python 绑定可能导致导入失败

## 快速开始

### 安装

```bash
# 克隆仓库
git clone https://github.com/ZhaofanQiu/video_cut_skill.git
cd video_cut_skill

# 安装系统依赖 (Ubuntu/Debian)
sudo apt update
sudo apt install ffmpeg libavcodec-dev libavformat-dev libswscale-dev

# 安装 Python 依赖
pip install -r requirements.txt
```

### 预下载模型（推荐）

```bash
# 下载 Whisper 模型
python scripts/download_models.py base

# 查看已下载模型
python scripts/download_models.py --list
```

## 使用示例

### 基础剪辑

```python
from video_cut_skill import AutoEditor, EditConfig

editor = AutoEditor()

# 基础剪辑
result = editor.process_video(
    "input.mp4",
    EditConfig(
        target_duration=60,
        aspect_ratio="9:16",
        add_subtitles=True,
        whisper_model="base",  # 可选: tiny/base/small/medium/large
        output_path="output.mp4"
    )
)
print(f"Output: {result.output_path}")
```

### AI 内容分析

```python
from video_cut_skill import ContentAnalyzer

analyzer = ContentAnalyzer()
analysis = analyzer.analyze("video.mp4")

print(f"Duration: {analysis.duration}")
print(f"Keywords: {analysis.keywords}")
print(f"Segments: {len(analysis.segments)}")

# 搜索关键词
segments = analysis.search_by_keyword("important")
```

### 智能剪辑策略

```python
from video_cut_skill import (
    StrategyGenerator, 
    EditIntent, 
    EditStyle,
    ContentAnalyzer
)

# 分析内容
analyzer = ContentAnalyzer()
analysis = analyzer.analyze("video.mp4")

# 生成策略
generator = StrategyGenerator()
intent = EditIntent(
    target_duration=60,
    style=EditStyle.FAST_PACED,
    platform="tiktok",
    add_subtitles=True
)

strategy = generator.generate(analysis, intent)
print(f"Generated {len(strategy.clips)} clips")
```

### Motion Graphics

```python
from video_cut_skill import (
    TextElement, TextStyle, TextAnimation, 
    TextAnimationConfig, EasingFunction, EasingType
)

# 创建动态文字
text = TextElement(
    text="Hello World",
    position=(960, 540),
    style=TextStyle(
        font_size=64,
        font_color="#FFFFFF",
        font_weight="bold"
    ),
    entry_animation=TextAnimationConfig(
        animation_type=TextAnimation.SLIDE_UP,
        duration=0.5,
        easing="ease_out_back"
    ),
    start_time=0,
    end_time=3
)

# 使用缓动函数
easing = EasingFunction(EasingType.EASE_OUT_BACK)
value = easing.apply(0.5)  # 获取 50% 进度的缓动值
```

## 项目结构

```
video_cut_skill/
├── src/video_cut_skill/       # 源代码
│   ├── core/                  # 核心引擎
│   │   ├── ffmpeg_wrapper.py  # FFmpeg 封装
│   │   └── models.py          # 数据模型
│   ├── ai/                    # AI 决策层
│   │   ├── transcriber.py     # Whisper 语音识别
│   │   ├── scene_detector.py  # 场景检测
│   │   ├── analyzer.py        # 内容分析 (Phase 2)
│   │   └── strategy.py        # 剪辑策略 (Phase 2)
│   ├── motion_graphics/       # 动效系统 (Phase 2)
│   │   ├── animations/        # 动画库
│   │   ├── elements/          # 元素库
│   │   └── renderer.py        # 渲染器
│   └── auto_editor.py         # 一键剪辑
├── tests/                     # 测试
│   └── integration/           # 集成测试
├── docs/                      # 文档
├── scripts/                   # 工具脚本
└── examples/                  # 示例
```

## 开发阶段

| 阶段 | 状态 | 关键功能 |
|------|------|----------|
| Phase 1 | ✅ 完成 | FFmpeg, Whisper, 场景检测 |
| Phase 2 | ✅ 完成 | AI分析, 策略生成, Motion Graphics |
| Phase 3 | 🚧 规划 | 高级特效, 音频增强, 生成式AI |

## 文档

- [SKILL.md](SKILL.md) - Agent 调用文档
- [模型管理](docs/models.md) - Whisper 模型下载和管理
- [API 文档](docs/api/) - 详细 API 参考
- [开发指南](docs/development.md) - 开发环境设置
- [测试指南](docs/testing-guide.md) - 测试说明
- [测试报告](docs/TEST_REPORT.md) - 完整测试报告
- [故障排除](docs/troubleshooting.md) - 常见问题
- [云端服务规划](docs/cloud_service_plan.md) - 阿里云集成规划

## 测试

```bash
# 运行 Phase 1 测试
python tests/integration/test_phase1.py

# 运行 Test 9 (最新测试)
python tests/integration/test9.py

# 运行 Phase 2 测试
python tests/integration/test_phase2.py

# 运行单元测试
pytest tests/unit/ -v
```

## 依赖

- **Python**: 3.8+
- **FFmpeg**: 4.0+
- **核心库**: moviepy, whisper, scenedetect, pillow
- **ML**: torch, transformers

## 许可证

MIT License - 详见 [LICENSE](LICENSE)

## 贡献

欢迎提交 Issue 和 PR！

1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/amazing`)
3. 提交更改 (`git commit -m 'Add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing`)
5. 创建 Pull Request

## 更新日志

### v0.3.1 (2026-03-14)
- ✅ **Phase 3.5 完成**: 智能转录模块、分级转录策略、静音检测
- ✅ **智能转录模块**: `SmartTranscriber` 类，支持动态模型选择
- ✅ **分级转录策略**: 长视频用TINY快速分析，高光用BASE精准转录
- ✅ **静音检测**: 自动识别无音频视频，提供友好错误提示
- ✅ **性能优化**: 31分钟视频8分钟处理完成，内存使用稳定
- ✅ **完整测试**: 5大测试全部通过 (端到端/错误恢复/性能/批量/集成)
- ✅ **云端规划**: 阿里云全栈服务规划文档

### v0.3.0 (2026-03-14)
- ✅ Phase 3 完成：GPU 加速、缓存系统、音频增强
- ✅ GPU 自动检测（兼容无 GPU 机器）
- ✅ 转录结果/场景检测结果缓存
- ✅ LUFS 音量标准化、降噪
- ✅ 所有新功能导出到主包

### v0.2.1 (2026-03-14)
- ✅ Test 9 通过：Whisper base 模型 + 字幕修复
- ✅ 修复 `add_subtitle()` 音频丢失问题
- ✅ 支持 `whisper_model` 参数 (tiny/base/small/medium/large/turbo)
- ✅ 添加飞书文件传输文档

### v0.2.0 (2026-03-14)
- ✅ Phase 2 完成：AI 分析、策略生成、Motion Graphics
- ✅ 新增 30+ 缓动函数
- ✅ 动态文字和形状元素
- ✅ 平台预设 (TikTok, YouTube, 小红书)

### v0.1.0 (2026-03-13)
- ✅ Phase 1 完成：FFmpeg 引擎、Whisper 集成、场景检测
- ✅ 基础剪辑功能
- ✅ 字幕生成
