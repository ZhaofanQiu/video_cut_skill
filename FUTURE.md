# Future Plans - 未来计划

Video Cut Skill 的长期路线图和功能规划。

**Version**: v0.4.0+  
**Last Updated**: 2026-03-16

---

## 执行摘要

当前项目处于 **v0.4.0 已发布** 阶段。

| 阶段 | 状态 | 说明 |
|------|------|------|
| Phase 1-3 | ✅ 完成 | 核心功能稳定，CI/CD健全 |
| Phase 4 (v0.4.0) | ✅ 完成 | InteractiveEditor、阿里云ASR、CostGuardian、智能字幕 |
| **P0 任务** | 📋 **规划中** | 任务队列、并发控制、错误恢复 |
| P1 任务 | 📋 规划中 | 节拍检测、模板系统、说话人识别 |
| P2 任务 | 📋 远期规划 | 生成式AI、平台上传、音频分离 |

> **文档同步说明**: 本次更新修正了已完成功能的状态。v0.4.0 已包含：测试覆盖率81%、阿里云ASR、智能字幕(LLM断句)、InteractiveEditor 等核心功能。

**当前重点**: 实现任务队列与并发控制，为生产环境部署做准备。

---

## ✅ 已完成功能 (v0.4.0)

以下功能已在 v0.4.0 中实现，从 Future Plans 移至完成列表：

| 功能 | 版本 | 说明 |
|------|------|------|
| **测试覆盖率 81%** | v0.3.1 | 全面的单元测试和集成测试覆盖 |
| **阿里云 ASR 集成** | v0.4.0 | Paraformer + Qwen3-ASR-Flash 云端语音识别 |
| **智能字幕系统** | v0.4.0 | LLM驱动的语义断句、横竖屏适配 |
| **InteractiveEditor** | v0.4.0 | 多轮对话式视频剪辑 |
| **CostGuardian** | v0.4.0 | 实时成本估算和用户确认机制 |
| **SessionManager** | v0.4.0 | 会话持久化和管理 |
| **自动降级策略** | v0.4.0 | 云端失败自动回退到本地 Whisper |

---

## 🔴 P0 - 最高优先级 (2026 Q2)

### P0.1 任务队列与并发控制

**问题**: 当前无并发控制，多视频同时处理可能导致内存不足或系统崩溃

**解决方案**:
```python
class TaskQueue:
    """视频处理任务队列 - 防止资源耗尽"""
    
    def __init__(self, max_concurrent: int = 2):
        self.max_concurrent = max_concurrent
        self.queue = asyncio.Queue(maxsize=10)
        self.running = set()
        
    async def submit(self, task: VideoTask) -> str:
        """提交任务，返回 task_id"""
        
    async def get_status(self, task_id: str) -> TaskStatus:
        """查询任务状态"""
```

**配置设计**:
```yaml
# config.yaml
queue:
  max_concurrent: 2        # 最大并发数 (根据GPU内存调整)
  max_queue_size: 10       # 队列最大长度
  timeout_seconds: 3600    # 任务超时时间
  retry_count: 2           # 失败重试次数
  retry_delay_seconds: 30  # 重试间隔
```

**集成点**:
- AutoEditor 自动使用 TaskQueue
- InteractiveEditor 会话级任务管理
- 提供 RESTful API 接口

**时间**: 2026-04 (2周)

---

### P0.2 错误恢复与断点续传

**问题**: 长视频处理失败需要完全重新开始，浪费资源

**解决方案**:
```python
class CheckpointManager:
    """断点续传管理器"""
    
    def save_checkpoint(self, task_id: str, stage: str, data: dict):
        """保存处理进度"""
        
    def resume_from_checkpoint(self, task_id: str) -> Optional[Checkpoint]:
        """从断点恢复"""
```

**检查点阶段**:
1. `transcription_complete` - 转录完成
2. `analysis_complete` - 分析完成
3. `clips_extracted` - 片段提取完成
4. `rendering` - 渲染中 (帧级别检查点)

**时间**: 2026-04 (1-2周)

---

### P0.3 性能监控与可观测性

**功能**:
- 处理时长统计 (P95/P99)
- 成功率/失败率监控
- 资源使用监控 (CPU/GPU/内存)
- 成本使用统计

**API 设计**:
```python
from video_cut_skill import MetricsCollector

metrics = MetricsCollector()

# 自动收集
with metrics.track_operation("video_processing"):
    result = editor.process_video(...)

# 查询指标
stats = metrics.get_stats(time_range="24h")
```

**时间**: 2026-04 (1周)

---

## 🟠 P1 - 高优先级 (2026 Q2-Q3)

### P1.1 节拍检测与智能卡点

**应用场景**: 短视频卡点、MV制作、节奏感强的广告快剪

**技术方案**:
```python
from video_cut_skill import BeatDetector

detector = BeatDetector(
    method="librosa",  # 或 "madmom"
    bpm_range=(60, 180)
)

# 检测节拍
beats = detector.detect("audio.mp3")

# 生成卡点剪辑方案
cuts = detector.generate_cuts(
    target_duration=30,
    align_to_beat=True  # 剪辑点对齐节拍
)
```

**功能清单**:
- [ ] 音乐节拍检测 (BPM + 节拍时间戳)
- [ ] 自动对齐剪辑点
- [ ] B-roll 自动插入 (在节拍点插入素材)
- [ ] 节奏变速 (音频时间拉伸)

**时间**: 2026-05 (2-3周)

---

### P1.2 Motion Graphics 模板系统

**目标**: 将常用动效模板化，降低使用门槛

**模板定义** (YAML):
```yaml
# templates/youtube_intro.yaml
template: youtube_intro
version: "1.0"
description: "YouTube 频道标准片头"

parameters:
  channel_name:
    type: string
    required: true
  accent_color:
    type: color
    default: "#FF6B6B"

elements:
  - type: text
    text: "{{channel_name}}"
    position: [960, 540]
    animation: 
      entry: slide_up
      duration: 0.5
      easing: ease_out_back
    style:
      font_size: 64
      font_color: "{{accent_color}}"
```

**模板类型规划**:
| 类型 | 数量目标 | 示例 |
|------|----------|------|
| 片头/片尾 | 5+ | 品牌展示、订阅引导 |
| Lower Thirds | 5+ | 人名条、信息提示 |
| 章节分隔 | 3+ | 转场动画 |
| 数据可视化 | 3+ | 图表动画 |

**时间**: 2026-05~06 (3-4周)

---

### P1.3 说话人识别与标注

**应用场景**: 播客/访谈视频自动标注说话人、会议记录

**技术方案**: pyannote.audio (开源声纹识别)

```python
from video_cut_skill import SpeakerDiarization

diarization = SpeakerDiarization()

# 识别说话人
speakers = diarization.process("audio.mp4")

# 生成带说话人标注的字幕
subtitles = diarization.generate_subtitles(
    assign_names={"SPEAKER_01": "主持人", "SPEAKER_02": "嘉宾"}
)
```

**时间**: 2026-06 (2周)

---

### P1.4 智能布局

**功能清单**:
- [ ] **人脸智能居中追踪**: OpenCV人脸检测 + 追踪算法
- [ ] **安全区域检测**: 识别平台UI区域 (抖音的点赞区、B站的弹幕区)
- [ ] **字幕位置智能调整**: 避开人脸和重要视觉区域
- [ ] **多画面智能布局**: 画中画自动排列

**API 设计**:
```python
from video_cut_skill import SmartLayout

layout = SmartLayout(
    aspect_ratio="9:16",
    platform="douyin"  # 影响安全区域计算
)

# 分析视频并推荐布局
recommendation = layout.analyze("input.mp4")

# 应用布局
output = layout.apply("input.mp4", recommendation)
```

**时间**: 2026-06 (2-3周)

---

## 🟡 P2 - 中等优先级 (2026 Q3)

### P2.1 生成式 AI 集成

**功能清单**:
| 功能 | AI能力 | 应用场景 |
|------|--------|----------|
| 自动生成标题 | GPT-4o / 通义千问 | 视频发布 |
| 自动摘要/描述 | 长文本生成 | 视频简介 |
| 标签推荐 | 关键词提取 | SEO优化 |
| 缩略图生成建议 | 视觉分析 | 封面选择 |

**API 设计**:
```python
from video_cut_skill.ai import ContentGenerator

generator = ContentGenerator(provider="aliyun")

metadata = generator.generate_metadata(
    video_path="output.mp4",
    platform="youtube",
    language="zh"
)
# {
#   "title": "10个Python技巧让你成为更好的程序员",
#   "description": "在本视频中，我们将介绍...",
#   "tags": ["python", "programming", "tutorial"],
#   "thumbnail_suggestions": ["frame_1200", "frame_3500"]
# }
```

**时间**: 2026-07 (2-3周)

---

### P2.2 音频分离

**功能**:
- 人声/背景音分离 (Demucs/Spleeter)
- 噪音消除
- BGM 智能匹配

**时间**: 2026-07 (2周)

---

### P2.3 平台直接上传

**支持平台**:
| 平台 | 优先级 | API状态 |
|------|--------|---------|
| YouTube | P0 | ✅ 成熟 |
| Bilibili | P1 | ✅ 成熟 |
| TikTok/抖音 | P1 | ⚠️ 有限制 |

**API 设计**:
```python
from video_cut_skill.platforms import YouTubeUploader, BilibiliUploader

uploader = YouTubeUploader(credentials="oauth.json")
uploader.upload(
    video_path="output.mp4",
    title="自动生成的标题",
    description="自动生成的描述...",
    tags=["python", "tutorial"],
    privacy="public"
)
```

**时间**: 2026-07~08 (3-4周)

---

### P2.4 色彩校正与 LUT

**功能**:
- LUT 滤镜应用 (FFmpeg lut3d)
- 自动白平衡
- 曝光调整
- 电影级调色预设库

**时间**: 2026-08 (2周)

---

### P2.5 高级转场效果

**功能**:
- 滑动/缩放/旋转转场
- 遮罩转场
- 光流转场 (optical flow)
- AI 智能转场时机推荐

**时间**: 2026-08~09 (3周)

---

## 📊 优先级矩阵

### 综合评估

| 功能 | 影响力 | 难度 | ROI | 优先级 |
|------|--------|------|-----|--------|
| 任务队列 | 高 | 中 | 高 | **P0** |
| 断点续传 | 高 | 中 | 高 | **P0** |
| 性能监控 | 中 | 低 | 高 | **P0** |
| 节拍检测 | 高 | 高 | 中 | **P1** |
| 模板系统 | 中 | 高 | 中 | **P1** |
| 说话人识别 | 中 | 中 | 中 | **P1** |
| 智能布局 | 中 | 中 | 中 | **P1** |
| 生成式AI | 中 | 中 | 中 | **P2** |
| 音频分离 | 中 | 高 | 中 | **P2** |
| 平台上传 | 中 | 中 | 中 | **P2** |
| 色彩校正 | 中 | 高 | 低 | **P2** |

---

## 🔧 技术债务清理计划

### 当前债务

| 债务项 | 影响 | 状态 | 清理计划 |
|--------|------|------|----------|
| 无并发控制 | 高 | 🚧 | P0: TaskQueue |
| 无断点续传 | 中 | 📋 | P0: CheckpointManager |
| 无性能监控 | 中 | 📋 | P0: MetricsCollector |
| 硬编码参数 | 低 | 📋 | P1: 配置化改造 |

### 清理时间表

```
2026-04 (v0.4.2): TaskQueue, CheckpointManager, MetricsCollector
2026-05 (v0.5.0): 模板系统, 节拍检测
2026-06 (v0.5.1): 说话人识别, 智能布局
```

---

## 🚨 风险与缓解

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|----------|
| 任务队列实现复杂 | 中 | 中 | 参考 Celery/RQ 设计，分阶段实现 |
| 节拍检测精度不足 | 中 | 中 | 多算法对比 (librosa/madmom) |
| 平台API限制 | 低 | 中 | 多平台备份方案 |
| AI模型成本上涨 | 中 | 低 | 本地模型 + API降级策略 |

---

## 📈 成功指标

### v0.4.2 (P0完成)
- [ ] TaskQueue 并发控制上线
- [ ] 断点续传功能可用
- [ ] 性能监控 dashboard 可用
- [ ] 生产环境部署无内存问题

### v0.5.0 (P1核心完成)
- [ ] 节拍检测功能可用
- [ ] 至少5个Motion Graphics模板
- [ ] 模板系统架构稳定

### v0.5.1 (P1补充完成)
- [ ] 说话人识别功能可用
- [ ] 智能布局功能可用
- [ ] 人脸识别准确率 > 90%

### v0.6.0 (P2完成)
- [ ] 生成式AI标题/描述生成
- [ ] 支持2+平台直接上传
- [ ] 音频分离功能可用

---

## 🤝 参与贡献

欢迎通过以下渠道参与项目：

- **GitHub Issues**: 功能请求和Bug报告
- **Discussions**: 设计讨论
- **飞书**: 实时交流

---

**Maintainer**: Zhaofan Qiu  
**License**: MIT
