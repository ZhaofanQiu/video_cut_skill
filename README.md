# Video Cut Skill

智能视频剪辑 Skill for OpenClaw Agent

## 项目简介

Video Cut Skill 是一个专为 AI Agent 设计的智能视频剪辑工具，提供从原始视频到成片的自动化/半自动化处理能力。

## 核心特性

- 🤖 **AI 驱动剪辑决策**: 基于内容理解的智能片段选择、节奏设计、布局决策
- 🎬 **高级感 Motion Graphics**: 程序化生成交互式动画、字幕条、转场效果
- 🎵 **语音内容识别**: 集成 Whisper 进行精准转录和语义分析
- 📐 **智能场景检测**: 基于 PySceneDetect 的视觉场景分割
- 🔧 **完整视频工作流**: 剪辑、排版、字幕、转场、特效一站式处理

## 项目结构

```
video_cut_skill/
├── docs/                       # 文档目录
│   ├── research/              # 调研文档
│   ├── architecture/          # 架构设计
│   ├── api/                   # API 文档
│   └── tutorials/             # 使用教程
├── src/                       # 源代码
│   ├── core/                  # 核心引擎
│   ├── ai/                    # AI 决策层
│   ├── motion_graphics/       # 动效生成
│   ├── effects/               # 视频特效
│   └── utils/                 # 工具函数
├── tests/                     # 测试套件
│   ├── unit/                  # 单元测试
│   ├── integration/           # 集成测试
│   └── fixtures/              # 测试资源
├── examples/                  # 示例代码
├── scripts/                   # 脚本工具
├── config/                    # 配置文件
├── requirements/              # 依赖管理
├── .github/                   # GitHub 工作流
├── Makefile                   # 构建脚本
├── pyproject.toml            # Python 项目配置
└── README.md                 # 项目说明
```

## 快速开始

### 安装依赖

```bash
# 安装系统依赖 (Ubuntu/Debian)
sudo apt update
sudo apt install ffmpeg libavcodec-dev libavformat-dev libswscale-dev

# 安装 Python 依赖
pip install -r requirements.txt
```

### 基础使用

```python
from video_cut_skill import AutoEditor

editor = AutoEditor()

# 一键智能剪辑
result = editor.auto_edit(
    video_path="input.mp4",
    config={
        "target_duration": 60,
        "aspect_ratio": "9:16",
        "add_subtitles": True,
        "style": "modern"
    }
)
```

## 开发指南

参见 [docs/development.md](docs/development.md)

## 许可证

MIT License
