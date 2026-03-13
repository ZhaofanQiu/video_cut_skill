# Video Cut Skill

智能视频剪辑 Skill for OpenClaw Agent

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 项目简介

Video Cut Skill 是一个专为 AI Agent 设计的智能视频剪辑工具，提供从原始视频到成片的自动化/半自动化处理能力。

### 当前版本: v0.2.0

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

### 🚧 Phase 3: 高级功能 (规划中)
- 🎨 色彩校正、LUT 滤镜
- 🔊 音频增强、节拍检测
- 🧠 生成式标题/摘要

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
python scripts/download_models.py tiny base

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

- [模型管理](docs/models.md) - Whisper 模型下载和管理
- [API 文档](docs/api/) - 详细 API 参考
- [开发指南](docs/development.md) - 开发环境设置
- [测试指南](docs/testing-guide.md) - 测试说明

## 测试

```bash
# 运行 Phase 1 测试
python tests/integration/test_phase1.py

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

### v0.2.0 (2026-03-14)
- ✅ Phase 2 完成：AI 分析、策略生成、Motion Graphics
- ✅ 新增 30+ 缓动函数
- ✅ 动态文字和形状元素
- ✅ 平台预设 (TikTok, YouTube, 小红书)

### v0.1.0 (2026-03-13)
- ✅ Phase 1 完成：FFmpeg 引擎、Whisper 集成、场景检测
- ✅ 基础剪辑功能
- ✅ 字幕生成
