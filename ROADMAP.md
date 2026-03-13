# Video Cut Skill - 多阶段代码实现规划

**Created**: 2026-03-14  
**Version**: v0.2.1 → v0.5.0  
**Status**: Phase 3 Implementation Started

---

## 当前状态回顾 (v0.2.1)

### ✅ 已完成
| 模块 | 功能 |
|------|------|
| **Phase 1 核心** | FFmpeg封装、Whisper语音识别、场景检测、字幕生成 |
| **Phase 2 基础** | AI内容分析、剪辑策略生成、Motion Graphics基础（缓动函数、文字/形状元素） |
| **CI/CD** | 完整测试套件、文档站点 |

### 🔧 已知技术债务
1. **测试覆盖率**: 仅46%，核心模块缺乏单元测试
2. **GPU支持**: 仅CPU模式，Whisper处理慢
3. **错误处理**: 部分异常未优雅处理
4. **类型注解**: 部分代码类型不完整

---

## Phase 3: 生产级强化 (v0.3.0) - 2个月

### 目标
提升稳定性、性能和用户体验，达到生产可用状态。

### 核心任务

#### 1. GPU加速支持 (P0) - 兼容无GPU机器
```python
from video_cut_skill import Transcriber

# 自动检测并使用GPU
transcriber = Transcriber(model_size="base", device="auto")  # cuda/cpu/auto
```
**实现要点**:
- [ ] CUDA环境检测与自动切换（无GPU时回退到CPU）
- [ ] Whisper FP16支持（速度提升5-10x，仅GPU）
- [ ] FFmpeg NVENC硬件编码（可选，无GPU时用软件编码）
- [ ] 显存管理（大视频分块处理）

**兼容性设计**:
```python
try:
    import torch
    HAS_CUDA = torch.cuda.is_available()
except ImportError:
    HAS_CUDA = False

# 自动选择设备
device = "cuda" if device == "auto" and HAS_CUDA else "cpu"
```

#### 2. 缓存系统 (P0)
```python
from video_cut_skill import CachedTranscriber, CachedSceneDetector

transcriber = CachedTranscriber(cache_dir="~/.cache/video_cut")
# 相同视频直接返回缓存结果
```
- [ ] 转录结果缓存（基于文件哈希）
- [ ] 场景检测结果缓存
- [ ] 视频元数据缓存
- [ ] 缓存过期策略

#### 3. 完善的错误处理与日志 (P0)
- [ ] 结构化日志输出（JSON格式）
- [ ] 用户友好的错误提示
- [ ] 自动重试机制（网络下载失败等）
- [ ] 处理进度回调

#### 4. 音频增强基础 (P1)
```python
from video_cut_skill.audio import AudioEnhancer

enhancer = AudioEnhancer()
enhancer.reduce_noise(input_path, output_path)
enhancer.normalize_lufs(input_path, output_path, target_lufs=-14)
```

#### 5. 测试覆盖率达到80%+
- [ ] 核心模块单元测试
- [ ] 集成测试稳定化
- [ ] 性能基准测试

---

## Phase 4: 智能功能深化 (v0.4.0) - 3个月

### 目标
基于AI的内容理解与自动化决策能力。

### 核心任务

#### 1. 节拍检测与智能卡点 (P1)
```python
from video_cut_skill.audio import BeatDetector

detector = BeatDetector()
beats = detector.detect_beats("music.mp3")
# 自动在节拍点剪辑/转场
editor.cut_on_beats(video_path, beats, output_path)
```

#### 2. 智能字幕系统升级 (P1)
- [ ] 智能断句优化（基于语义）
- [ ] 多语言字幕生成
- [ ] 说话人识别与标注
- [ ] 字幕动画（逐字出现/打字机效果）

#### 3. 高级Motion Graphics (P1)
```python
from video_cut_skill.motion_graphics import TemplateRenderer

# 预设模板系统
template = TemplateRenderer.load("youtube_intro")
template.render(text="Channel Name", output="intro.mp4")
```
- [ ] 模板系统（JSON/YAML定义）
- [ ] 片头/片尾模板
- [ ] 数据可视化动画（图表）
- [ ] Lower Thirds 新闻字幕条

#### 4. 生成式AI集成 (P2)
```python
from video_cut_skill.ai import ContentGenerator

# 自动生成标题/描述/标签
generator = ContentGenerator()
metadata = generator.generate_metadata(video_path, platform="youtube")
# {title, description, tags, thumbnail_suggestions}
```

#### 5. 智能布局 (P2)
- [ ] 人脸智能居中追踪
- [ ] 安全区域检测（避开平台UI）
- [ ] 多画面智能布局（PIP/分屏）

---

## Phase 5: 平台与生态 (v0.5.0) - 3个月

### 目标
完整的工作流集成和平台生态。

### 核心任务

#### 1. 平台直接上传 (P2)
```python
from video_cut_skill.platforms import YouTubeUploader, TikTokUploader

uploader = YouTubeUploader(credentials="oauth.json")
uploader.upload(
    video_path="output.mp4",
    title="Video Title",
    description="...",
    tags=["tag1", "tag2"],
    privacy="public"
)
```

#### 2. 多轨道编辑引擎 (P3)
- [ ] 时间线数据模型重构
- [ ] 视频层叠/画中画
- [ ] 复杂转场效果
- [ ] 项目文件保存/加载

#### 3. 色彩校正与LUT (P3)
```python
from video_cut_skill.effects import ColorGrading

grading = ColorGrading()
grading.apply_lut(video_path, "cinematic.cube", output_path)
grading.auto_white_balance(video_path, output_path)
```

#### 4. 插件系统 (P3)
```python
# 支持第三方插件
from video_cut_skill.plugins import register_plugin

@register_plugin(name="custom_effect")
class CustomEffect:
    def process(self, frame):
        return frame
```

#### 5. 实时预览系统 (P3)
- [ ] 低分辨率代理生成
- [ ] WebSocket实时推送
- [ ] 浏览器预览界面

---

## 实施路线图

```
2026-03 ~ 2026-05 (v0.3.0)  Phase 3: 生产级强化
  ├── GPU加速支持（兼容无GPU）
  ├── 缓存系统
  ├── 完善错误处理
  └── 测试覆盖率80%+

2026-05 ~ 2026-08 (v0.4.0)  Phase 4: 智能功能深化
  ├── 节拍检测
  ├── 智能字幕升级
  ├── Motion Graphics模板
  └── 生成式AI集成

2026-08 ~ 2026-11 (v0.5.0)  Phase 5: 平台与生态
  ├── 平台直接上传
  ├── 多轨道编辑
  ├── 色彩校正/LUT
  └── 插件系统
```

---

## 技术选型建议

| 功能 | 推荐方案 | 理由 |
|------|---------|------|
| GPU加速 | CUDA + PyTorch | Whisper原生支持，生态成熟 |
| 缓存 | SQLite + 文件哈希 | 轻量、可靠、易部署 |
| 节拍检测 | librosa / madmom | 音频分析专业库 |
| 色彩校正 | FFmpeg lut3d + 自研 | FFmpeg内置支持，无需额外依赖 |
| 平台API | 各平台官方SDK | 稳定性、功能完整性 |
| 插件系统 | Python entry_points | 标准做法，易扩展 |

---

## GPU兼容性设计原则

### 1. 自动检测与优雅降级
```python
def get_optimal_device(preferred: str = "auto") -> str:
    """获取最优计算设备，无GPU时自动回退到CPU."""
    if preferred == "cpu":
        return "cpu"
    
    if preferred in ("auto", "cuda"):
        try:
            import torch
            if torch.cuda.is_available():
                return "cuda"
        except ImportError:
            pass
    
    return "cpu"
```

### 2. 功能降级策略
- **GPU可用**: FP16推理、硬件编码、批量处理
- **仅CPU**: FP32推理、软件编码、串行处理

### 3. 用户提示
```python
logger.info(f"Using device: {device}" + 
            (" (CUDA加速已启用)" if device == "cuda" else " (CPU模式)"))
```

---

## 相关文档

- [Test 9 Summary](docs/testing/test9-summary.md) - 当前功能验证报告
- [FUTURE.md](FUTURE.md) - 详细未来计划
- [Research](docs/research/) - 技术调研报告

---

**Last Updated**: 2026-03-14  
**Maintainer**: Zhaofan Qiu
