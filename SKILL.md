# Video Cut Skill

Intelligent video editing skill for OpenClaw Agent - 智能视频剪辑 Skill

## Description

Video Cut Skill 是一个专为 AI Agent 设计的智能视频剪辑工具，提供从原始视频到成片的自动化/半自动化处理能力。

### Key Capabilities

- 🎬 **Auto Editing**: One-click video processing with AI
- 🎯 **Smart Clipping**: Cut by scenes, duration, or keywords
- 📝 **Subtitle Generation**: Automatic transcription with Whisper
- 🎨 **Motion Graphics**: Dynamic text and shape animations
- 📐 **Format Conversion**: Aspect ratio changes, padding, cropping
- 🔊 **Audio Extraction**: MP3/WAV extraction from video

## Installation

```bash
# Install system dependencies (Ubuntu/Debian)
sudo apt update
sudo apt install ffmpeg libavcodec-dev libavformat-dev libswscale-dev

# Install Python package
pip install video-cut-skill

# Or install from source
git clone https://github.com/ZhaofanQiu/video_cut_skill.git
cd video_cut_skill
pip install -e .
```

### Pre-download Models (Recommended)

```bash
# Download Whisper models
python -m video_cut_skill.scripts.download_models base

# View available models
python -m video_cut_skill.scripts.download_models --list
```

## Usage Examples

### 1. Auto Editor - One-Click Processing

Process a video with automatic transcription and subtitles:

```python
from video_cut_skill import AutoEditor, EditConfig

editor = AutoEditor()

result = editor.process_video(
    "input.mp4",
    EditConfig(
        target_duration=60,        # Cut to 60 seconds
        add_subtitles=True,        # Auto-generate subtitles
        whisper_model="base",      # Whisper model (tiny/base/small/medium/large)
        output_path="output.mp4"
    )
)

print(f"Output: {result.output_path}")
print(f"Language: {result.transcript.language}")
print(f"Segments: {len(result.transcript.segments)}")
```

### 2. Extract Highlights by Keywords

Find and extract clips containing specific keywords:

```python
from video_cut_skill import AutoEditor

editor = AutoEditor()

result = editor.extract_highlights(
    "input.mp4",
    keywords=["important", "key point"],
    output_path="highlights.mp4",
    context_seconds=2.0,         # Add 2s before/after each match
    whisper_model="base"
)
```

### 3. Cut by Scenes

Automatically detect scene changes and split video:

```python
from video_cut_skill import AutoEditor

editor = AutoEditor()

clips = editor.cut_by_scenes(
    "input.mp4",
    output_dir="./scenes/",
    min_scene_duration=1.0       # Minimum scene length in seconds
)

print(f"Generated {len(clips)} clips")
```

### 4. FFmpeg Wrapper - Low-Level Operations

Direct access to FFmpeg operations:

```python
from video_cut_skill import FFmpegWrapper

ffmpeg = FFmpegWrapper()

# Get video info
info = ffmpeg.get_video_info("input.mp4")
print(f"Duration: {info['duration']}, Resolution: {info['width']}x{info['height']}")

# Cut a clip
ffmpeg.cut_clip(
    "input.mp4",
    "output.mp4",
    start_time=10.0,
    end_time=30.0
)

# Change aspect ratio
ffmpeg.change_aspect_ratio(
    "input.mp4",
    "vertical.mp4",
    target_ratio=(9, 16),
    mode="pad"  # pad, crop, or stretch
)

# Extract audio
ffmpeg.extract_audio("input.mp4", "audio.mp3")

# Add subtitles (preserves audio)
ffmpeg.add_subtitle(
    "video.mp4",
    "subtitles.srt",
    "output_with_subtitles.mp4"
)
```

### 5. Transcription Only

Use Whisper for speech recognition:

```python
from video_cut_skill import Transcriber

transcriber = Transcriber(model_size="base")

# Transcribe
result = transcriber.transcribe("video.mp4")

print(f"Text: {result.text}")
print(f"Language: {result.language}")

for seg in result.segments:
    print(f"[{seg.start:.2f}s - {seg.end:.2f}s]: {seg.text}")

# Export subtitles
transcriber.export_srt(result, "output.srt")
transcriber.export_ass(result, "output.ass")  # Advanced styling
```

### 6. Scene Detection

Detect scene changes in video:

```python
from video_cut_skill import SceneDetector

detector = SceneDetector(detector_type="content")

result = detector.detect("video.mp4", min_scene_len=0.5)

print(f"Found {result.scene_count} scenes")
for scene in result.scenes[:5]:
    print(f"Scene: {scene.start:.2f}s - {scene.end:.2f}s")

# Get scene at specific time
scene = result.get_scene_at_time(30.0)
```

## Configuration

### EditConfig Options

```python
from video_cut_skill import EditConfig

config = EditConfig(
    target_duration=60.0,        # Target video duration (seconds)
    aspect_ratio="9:16",         # Target aspect ratio or "original"
    add_subtitles=True,          # Enable subtitle generation
    whisper_model="base",        # Whisper model size
    output_path="output.mp4"     # Output file path
)
```

### Whisper Models

| Model | Size | Speed | Memory | Use Case |
|-------|------|-------|--------|----------|
| tiny | ~39M | ~10x | ~1GB | Fast, low accuracy |
| base | ~74M | ~7x | ~1GB | **Default**, good balance |
| small | ~244M | ~4x | ~2GB | Better accuracy |
| medium | ~769M | ~2x | ~5GB | High accuracy |
| large | ~1550M | 1x | ~10GB | Best accuracy |
| turbo | ~809M | ~8x | ~6GB | Fast with large-v3 accuracy |

## API Reference

### AutoEditor

Main class for automated video editing.

**Methods:**
- `process_video(video_path, config)` - Process video with configuration
- `extract_highlights(video_path, keywords, output_path, context_seconds, whisper_model)` - Extract keyword segments
- `cut_by_scenes(video_path, output_dir, min_scene_duration)` - Split by scenes

### FFmpegWrapper

Low-level FFmpeg operations.

**Methods:**
- `get_video_info(video_path)` - Get video metadata
- `cut_clip(input, output, start_time, end_time, copy_codec=False)` - Cut clip
- `concatenate_clips(clips, output, reencode=False)` - Join clips
- `add_subtitle(video_path, subtitle_path, output_path)` - Burn subtitles
- `extract_audio(video_path, output_path, format, bitrate)` - Extract audio
- `change_aspect_ratio(video_path, output_path, target_ratio, mode)` - Change ratio

### Transcriber

Whisper-based speech recognition.

**Methods:**
- `transcribe(video_path, language, word_timestamps, task)` - Transcribe audio
- `export_srt(transcript, output_path)` - Export SRT subtitles
- `export_ass(transcript, output_path, style)` - Export ASS subtitles
- `detect_keywords(transcript, keywords, context_seconds)` - Find keywords

### SceneDetector

Automatic scene change detection.

**Methods:**
- `detect(video_path, min_scene_len)` - Detect scenes
- `get_scene_at_time(time)` - Get scene at timestamp

## Testing

Run the test suite:

```bash
# Phase 1 tests (basic functionality)
python tests/integration/test_phase1.py

# Test 9 (Whisper base model + subtitle fix)
python tests/integration/test9.py

# Unit tests
pytest tests/unit/ -v
```

## Platform Notes

### Feishu File Transfer

When sending videos via Feishu, rename `.mp4` to `.bin` before sending:

```python
import shutil
# Rename for Feishu
shutil.copy("video.mp4", "video.mp4.bin")
# Send video.mp4.bin via Feishu
# Recipient renames back to .mp4 after download
```

## 7. Smart Transcriber - 智能转录 (新增 v0.3.1)

Intelligent transcription with dynamic model selection and silent video detection.

### 7.1 Basic Usage

```python
from video_cut_skill.core.smart_transcriber import SmartTranscriber, ModelSize

transcriber = SmartTranscriber()

# Auto-select model based on video duration
result = transcriber.transcribe("video.mp4")

if result.error:
    print(f"Error: {result.error}")
else:
    print(f"Text: {result.text}")
    print(f"Model used: {result.model_used}")
    print(f"Segments: {len(result.segments)}")
```

### 7.2 Silent Video Detection

```python
# Automatically detect videos without audio
result = transcriber.transcribe("silent_video.mp4")

if result.error:
    # Friendly error message:
    # 【无音频】该视频没有音频轨道，无法进行语音识别。请检查：
    #   1. 视频是否包含声音
    #   2. 视频文件是否损坏
    #   3. 尝试使用其他视频文件
    print(result.error)
```

### 7.3 Tiered Transcription Strategy

```python
# Step 1: Fast analysis with TINY model
rough_result = transcriber.transcribe(
    "long_video.mp4",
    model=ModelSize.TINY
)

# Extract highlight timestamps...

# Step 2: Precise transcription with BASE model
final_result = transcriber.transcribe(
    "highlight_clip.mp4",
    model=ModelSize.BASE
)
```

### 7.4 Model Selection Guide

| Model | Size | Speed | Memory | Best For |
|-------|------|-------|--------|----------|
| tiny | ~39M | ~10x | ~1GB | Long video analysis |
| base | ~74M | ~7x | ~1GB | Short clips, output videos |

**Note**: small/medium/large models require 2GB+/5GB+/10GB+ memory and may not work on low-memory systems.

## Troubleshooting

### FFmpeg Not Found

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install ffmpeg

# macOS
brew install ffmpeg
```

### CUDA Out of Memory

Use smaller Whisper model or CPU:

```python
transcriber = Transcriber(model_size="tiny", device="cpu")
```

### Subtitles Not Showing

Ensure subtitle file path is correct and video player supports subtitles.

## License

MIT License - See [LICENSE](LICENSE) for details.

## Links

- GitHub: https://github.com/ZhaofanQiu/video_cut_skill
- Documentation: https://zhaofanqiu.github.io/video_cut_skill/
