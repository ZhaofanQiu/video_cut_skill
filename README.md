# Video Cut Skill

智能视频剪辑 Skill for OpenClaw Agent

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 项目简介

Video Cut Skill 是一个专为 AI Agent 设计的智能视频剪辑工具，提供从原始视频到成片的自动化/半自动化处理能力。

### 当前版本: v0.5.0

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

### ✅ Phase 4: 交互式功能 (已完成 v0.4.0)
- 🎙️ **交互式编辑器**: InteractiveEditor 多轮对话剪辑
- 💰 **成本 guardian**: 实时成本估算和确认
- 💾 **会话管理**: 持久化会话状态和历史
- 🔗 **阿里云集成**: Paraformer/Qwen3-ASR-Flash 语音识别

### ✅ Phase 5: 高级功能 (已完成 v0.5.0)
- 🎵 **节拍检测**: 多方法 BPM 检测 (librosa/madmom)，智能卡点剪辑
- 🎨 **MG 模板引擎**: JSON/YAML 模板，4个内置模板，参数化渲染
- 🗣️ **说话人识别**: VAD 语音检测，说话人分离，声纹识别
- 📐 **智能布局**: 自动构图 (8种规则)，多画幅适配，人脸/主体检测

### 🚧 Phase 6: 未来规划
- 🎬 高级字幕动画与特效
- 🧠 生成式 AI 集成
- 🔊 高级音频分离与增强

## 快速开始

### 安装

```bash
# 克隆仓库
git clone https://github.com/ZhaofanQiu/video_cut_skill.git
cd video_cut_skill

# 安装系统依赖 (Ubuntu/Debian)
sudo apt update
sudo apt install ffmpeg libavcodec-dev libavformat-dev libswscale-dev

# 安装 Python 包
pip install -e .
```

### 配置阿里云 API Key (可选但推荐)

如需使用 **InteractiveEditor** 或 **阿里云 ASR** 功能，需要配置阿里云 API Key：

```bash
# 方式1: 环境变量
export DASHSCOPE_API_KEY="your-api-key-here"

# 方式2: 配置文件 (推荐)
cp config.example.yaml config.yaml
# 编辑 config.yaml，填入你的 API Key
```

获取阿里云 API Key：
1. 访问 [阿里云 DashScope 控制台](https://dashscope.aliyun.com/)
2. 注册/登录账号
3. 在"API Key 管理"中创建新的 API Key

> **注意**: 未配置 API Key 时，系统会自动回退到本地 Whisper 模型，但 InteractiveEditor 的智能字幕优化功能将不可用。

### 预下载模型（推荐）

```bash
# 下载 Whisper 模型
python scripts/download_models.py base

# 查看已下载模型
python scripts/download_models.py --list
```

## 使用示例

### AutoEditor - 一键剪辑（统一版 v0.3.2+）

```python
from video_cut_skill import AutoEditor, EditConfig

# 音频分析模式（默认，适合访谈、教学、播客）
editor = AutoEditor(analysis_mode="audio")

# 视觉分析模式（适合电影、MV、场景化内容）
# editor = AutoEditor(analysis_mode="visual")

# 处理视频
result = editor.process_video(
    "input.mp4",
    EditConfig(
        target_duration=60,
        aspect_ratio="9:16",
        add_subtitles=True,
        whisper_model="auto",  # auto/tiny/base/small/medium/large
        highlight_keywords=["重点", "总结"],
        output_path="output.mp4"
    )
)
print(f"Output: {result.output_path}")
print(f"Processing time: {result.processing_time:.1f}s")
```

### InteractiveEditor - 交互式剪辑 (v0.4.0+)

适合需要多轮对话、逐步精调的剪辑场景：

```python
from video_cut_skill import InteractiveEditor, Config

# 创建编辑器
config = Config()
editor = InteractiveEditor(config=config)

# 1. 分析视频 - 自动转录和语义分析
response = editor.analyze("input.mp4")
session_id = response.data["session_id"]

# 2. 编辑指令 - 自然语言描述需求
edit_response = editor.edit(
    session_id, 
    "提取关于 AI 技术的关键段落，时长控制在 30 秒"
)

# 3. 确认并导出
if edit_response.state == "awaiting_confirm":
    confirm_response = editor.confirm_edit(session_id)
    output_path = confirm_response.data["output_path"]
    print(f"导出成功: {output_path}")

# 4. 反馈优化（可选）
feedback_response = editor.feedback(
    session_id,
    "保留更多开头部分"
)
```

### 按场景切割（仅视觉分析模式）

```python
from video_cut_skill import AutoEditor

# 视觉分析模式支持场景检测
editor = AutoEditor(analysis_mode="visual")

clips = editor.cut_by_scenes(
    "input.mp4",
    output_dir="./scenes/",
    min_scene_duration=1.0
)
print(f"Generated {len(clips)} clips")
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

### 节拍检测与卡点剪辑 (v0.5.0+)

```python
from video_cut_skill import BeatDetector, BeatSyncEditor

# 检测节拍
detector = BeatDetector(method="librosa")
result = detector.detect("music.mp3")

print(f"BPM: {result.bpm}")
print(f"Beats: {result.beat_count}")
print(f"Downbeats: {result.downbeat_count}")

# 生成卡点剪辑方案
cuts = detector.generate_cuts(
    audio_path="music.mp3",
    target_duration=30,
    align_to_beat=True,
    prefer_downbeat=True
)

print(f"Generated {len(cuts.cut_points)} cut points")
for cp in cuts.cut_points:
    print(f"  {cp.time:.2f}s - {cp.reason}")

# 节拍同步编辑器
editor = BeatSyncEditor()
editor.load_audio("music.mp3")

# 创建卡点剪辑策略
strategy = editor.create_beat_cut_strategy(
    target_duration=30,
    cut_on_downbeat=True
)

# 建议 B-roll 插入点
b_roll_slots = editor.suggest_b_roll_insertion_points(min_interval=5.0)
```

### MG 模板引擎 (v0.5.0+)

```python
from video_cut_skill import TemplateEngine, create_youtube_intro, create_lower_third

# 快速创建 YouTube 片头
elements = create_youtube_intro(
    channel_name="My Channel",
    subtitle="Subscribe for more!",
    accent_color="#FF0000"
)

# 创建 Lower Third 字幕条
elements = create_lower_third(
    name="John Doe",
    title="Software Engineer",
    color="#0066CC"
)

# 使用模板引擎
engine = TemplateEngine()

# 列出所有模板
templates = engine.list_templates()
for t in templates:
    print(f"{t.template_id}: {t.name}")

# 渲染模板
elements = engine.render_template(
    "youtube_intro_v1",
    {
        "channel_name": "My Channel",
        "accent_color": "#FF5733",
        "subtitle": "New videos every week"
    }
)

# 导出为视频
engine.render_to_video(
    "youtube_intro_v1",
    {"channel_name": "Test"},
    "intro.mp4"
)
```

### 说话人识别 (v0.5.0+)

```python
from video_cut_skill import SpeakerAwareEditor, SpeakerDiarizer

# 分析视频中的说话人
editor = SpeakerAwareEditor()
result = editor.analyze("meeting.mp4")

print(f"Detected {result.num_speakers} speakers")
for speaker in result.speakers:
    duration = editor.get_speaker_duration(speaker.speaker_id)
    print(f"  {speaker.name}: {duration:.1f}s")

# 获取说话人时间线
timeline = editor.get_speaker_timeline()
for item in timeline:
    print(f"{item['start']:.1f}s - {item['speaker_name']}")

# 只保留主导说话人
clips = editor.extract_by_speaker(dominant_only=True)

# 创建带说话人标记的字幕
srt = editor.create_speaker_subtitles(subtitle_format="srt")
with open("subtitles.srt", "w") as f:
    f.write(srt)

# 导出分析结果
editor.export_to_json("speaker_analysis.json")
```

### 智能布局与自动构图 (v0.5.0+)

```python
from video_cut_skill import SmartLayoutEditor, AspectRatio, CompositionRule

# 分析视频并建议布局
editor = SmartLayoutEditor()
suggestions = editor.analyze("video.mp4")

for suggestion in suggestions:
    print(f"{suggestion.aspect_ratio.value}: score {suggestion.score}")
    print(f"  Crop: {suggestion.crop_region.bbox}")
    print(f"  Rule: {suggestion.crop_region.rule_applied.value}")

# 自动裁剪为 9:16 (抖音/Instagram)
editor.auto_crop(
    "input.mp4",
    "output_9_16.mp4",
    aspect_ratio=AspectRatio.PORTRAIT_9_16,
    rule=CompositionRule.FACE_CENTER
)

# 使用三分法构图
crop = editor.composition_engine.compute_crop(
    video_width=1920,
    video_height=1080,
    target_ratio=AspectRatio.SQUARE_1_1,
    rule=CompositionRule.RULE_OF_THIRDS
)

# 批量生成不同平台版本
results = editor.batch_crop_for_platforms(
    "input.mp4",
    output_dir="./platforms/"
)
# 生成: tiktok_*.mp4, instagram_*.mp4, youtube_*.mp4, youtube_shorts_*.mp4
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
│   │   ├── smart_transcriber.py  # 智能转录
│   │   └── models.py          # 数据模型
│   ├── ai/                    # AI 决策层
│   │   ├── transcriber.py     # Whisper 语音识别
│   │   ├── scene_detector.py  # 场景检测
│   │   ├── analyzer.py        # 内容分析
│   │   └── strategy.py        # 剪辑策略
│   ├── motion_graphics/       # 动效系统
│   │   ├── animations/        # 动画库
│   │   ├── elements/          # 元素库
│   │   └── renderer.py        # 渲染器
│   ├── audio/                 # 音频处理
│   ├── utils/                 # 工具模块
│   └── auto_editor.py         # 一键剪辑（统一版）
├── tests/                     # 测试
│   ├── unit/                  # 单元测试
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
| Phase 3 | ✅ 完成 | GPU加速, 缓存, 音频增强, SmartTranscriber |
| Phase 4 | ✅ 完成 | InteractiveEditor, Aliyun ASR, CostGuardian |
| Phase 5 | ✅ 完成 | 节拍检测, MG模板, 说话人识别, 智能布局 |
| Phase 6 | 🚧 规划 | 高级特效, 生成式AI, 音频分离 |

## 文档

- [SKILL.md](SKILL.md) - Agent 调用文档
- [CHANGELOG.md](CHANGELOG.md) - 版本历史和更新日志
- [配置参考](docs/configuration.md) - 完整配置选项
- [架构决策](docs/adr/) - 设计决策记录 (ADR)
- [模型管理](docs/models.md) - Whisper 模型下载和管理
- [API 文档](docs/api/) - 详细 API 参考
- [测试报告](docs/TEST_REPORT.md) - 完整测试报告
- [故障排除](docs/troubleshooting.md) - 常见问题

## 测试

```bash
# 运行所有测试
pytest tests/ -v

# 运行单元测试
pytest tests/unit/ -v

# 运行集成测试
pytest tests/integration/ -v

# 代码检查
mypy src/video_cut_skill --ignore-missing-imports
```

## 依赖

- **Python**: 3.8+
- **FFmpeg**: 4.0+
- **核心库**: moviepy, whisper, scenedetect, pillow
- **ML**: torch, transformers

完整依赖列表见 `pyproject.toml`。

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

查看 [CHANGELOG.md](CHANGELOG.md) 获取完整版本历史。

### 最新更新 (v0.5.0)
- ✅ **节拍检测**: librosa/madmom 多方法 BPM 检测，智能卡点剪辑
- ✅ **MG 模板引擎**: JSON/YAML 模板定义，4个内置模板，参数化渲染
- ✅ **说话人识别**: VAD 语音活动检测，说话人分离，声纹识别
- ✅ **智能布局**: 8种构图规则，多画幅适配 (9:16/16:9/1:1)，人脸/主体检测
