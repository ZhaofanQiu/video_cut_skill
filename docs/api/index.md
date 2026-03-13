# API Reference

## Core Module

### FFmpegWrapper

视频处理的核心封装类。

```python
from video_cut_skill.core import FFmpegWrapper

wrapper = FFmpegWrapper()
```

#### Methods

##### `probe(video_path)`

获取视频元数据。

**Parameters:**
- `video_path`: 视频文件路径

**Returns:** 视频元数据字典

**Example:**
```python
info = wrapper.probe("video.mp4")
print(info["format"]["duration"])
```

##### `get_video_info(video_path)`

获取视频信息摘要。

**Returns:**
```python
{
    "duration": float,      # 时长（秒）
    "width": int,           # 宽度
    "height": int,          # 高度
    "fps": float,           # 帧率
    "bitrate": int,         # 比特率
    "codec": str,           # 编码格式
    "has_audio": bool,      # 是否有音频
}
```

##### `cut_clip(input_path, output_path, start_time, end_time, copy_codec=True)`

剪辑视频片段。

**Parameters:**
- `input_path`: 输入路径
- `output_path`: 输出路径
- `start_time`: 开始时间（秒）
- `end_time`: 结束时间（秒）
- `copy_codec`: 是否直接复制编码（更快）

##### `concatenate_clips(clip_paths, output_path, reencode=False)`

拼接多个视频片段。

##### `extract_audio(video_path, output_path, format="mp3", bitrate="192k")`

提取音频。

##### `add_subtitle(video_path, subtitle_path, output_path, style=None)`

添加字幕。

##### `change_aspect_ratio(video_path, output_path, target_ratio, mode="pad", pad_color="black")`

改变视频宽高比。

**Modes:**
- `pad`: 添加填充保持比例
- `crop`: 裁剪中心区域
- `stretch`: 拉伸变形

---

## AI Module

### Transcriber

语音识别器，基于 Whisper。

```python
from video_cut_skill.ai import Transcriber

transcriber = Transcriber(model_size="base")
```

**Model Sizes:**
- `tiny`: 39M 参数，最快
- `base`: 74M 参数，推荐
- `small`: 244M 参数，更准确
- `medium`: 769M 参数，高精度
- `large`: 1550M 参数，最高精度
- `turbo`: 809M 参数，速度与精度平衡

#### Methods

##### `transcribe(video_path, language=None, word_timestamps=True, task="transcribe")`

转录音视频。

**Returns:** `TranscriptResult`

##### `export_srt(transcript, output_path)`

导出 SRT 字幕文件。

##### `export_ass(transcript, output_path, style=None)`

导出 ASS 字幕文件（支持高级样式）。

##### `detect_keywords(transcript, keywords, context_seconds=2.0)`

检测关键词出现位置。

### SceneDetector

场景检测器，基于 PySceneDetect。

```python
from video_cut_skill.ai import SceneDetector

detector = SceneDetector(detector_type="content")
```

**Detector Types:**
- `content`: 内容感知检测（推荐）
- `threshold`: 基于阈值的淡入淡出检测
- `adaptive`: 自适应检测（适合运动镜头）

#### Methods

##### `detect(video_path, threshold=27.0, min_scene_len=0.5)`

检测视频场景。

**Returns:** `SceneDetectionResult`

##### `split_video(video_path, scenes, output_dir, filename_template)`

按场景分割视频。

##### `merge_similar_scenes(scenes, max_merge_gap=1.0, min_merged_duration=2.0)`

合并相似/接近的场景。

---

## Data Models

### TranscriptResult

转录结果。

```python
@dataclass
class TranscriptResult:
    text: str                    # 完整文本
    segments: List[TranscriptSegment]
    language: str               # 检测到的语言
    duration: float             # 总时长
```

**Methods:**
- `get_segment_at_time(time)`: 获取指定时间点的片段
- `search_text(keyword)`: 搜索关键词

### SceneDetectionResult

场景检测结果。

```python
@dataclass
class SceneDetectionResult:
    scenes: List[Scene]
    video_path: str
    detector_type: str
    total_duration: float
```

**Methods:**
- `get_scene_at_time(time)`: 获取指定时间所在的场景
- `get_longest_scenes(n=5)`: 获取最长的 N 个场景

---

## AutoEditor

一键智能剪辑器。

```python
from video_cut_skill import AutoEditor, EditIntent

editor = AutoEditor()

result = editor.auto_edit(
    video_path="input.mp4",
    intent=EditIntent(
        target_duration=60,
        aspect_ratio="9:16",
        style="modern",
    ),
)
```
