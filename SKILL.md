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
pip install -e .

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

### 1. Auto Editor - One-Click Processing (Unified API v0.3.2+)

The unified `AutoEditor` supports two analysis modes:
- **Audio Analysis** (`analysis_mode="audio"`): Speech recognition, dynamic model selection
- **Visual Analysis** (`analysis_mode="visual"`): Scene detection, shot segmentation

```python
from video_cut_skill import AutoEditor, EditConfig

# Audio Analysis Mode (Default) - Best for interviews, podcasts, tutorials
editor = AutoEditor(analysis_mode="audio")

result = editor.process_video(
    "input.mp4",
    EditConfig(
        target_duration=60,        # Cut to 60 seconds
        add_subtitles=True,        # Auto-generate subtitles
        whisper_model="auto",      # "auto" selects tiny/base based on duration
        highlight_keywords=["intro", "key point"],
        context_seconds=2.0,
        output_path="output.mp4"
    )
)

print(f"Output: {result.output_path}")
print(f"Processing time: {result.processing_time:.1f}s")
print(f"Model used: {result.transcript.get('model_used')}")
```

### 2. Extract Highlights by Keywords

```python
from video_cut_skill import AutoEditor

editor = AutoEditor(analysis_mode="audio")

result = editor.extract_highlights(
    "input.mp4",
    keywords=["important", "key point"],
    output_path="highlights.mp4",
    context_seconds=2.0,         # Add 2s before/after each match
    whisper_model="auto"
)
```

### 3. Cut by Scenes (Visual Analysis Mode Only)

Scene detection requires Visual Analysis Mode:

```python
from video_cut_skill import AutoEditor

# Visual Analysis Mode supports scene detection
editor = AutoEditor(analysis_mode="visual")

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

### 7. Smart Transcriber

Intelligent transcription with dynamic model selection and silent video detection.

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

### 8. Tiered Transcription Strategy

```python
from video_cut_skill.core.smart_transcriber import SmartTranscriber, ModelSize

transcriber = SmartTranscriber()

# Step 1: Fast analysis with TINY model for long videos
rough_result = transcriber.transcribe(
    "long_video.mp4",
    model=ModelSize.TINY
)

# Step 2: Precise transcription with BASE model for output clips
final_result = transcriber.transcribe(
    "highlight_clip.mp4",
    model=ModelSize.BASE
)
```

## Configuration

### EditConfig Options

```python
from video_cut_skill import EditConfig

config = EditConfig(
    target_duration=60.0,        # Target video duration (seconds)
    aspect_ratio="9:16",         # Target aspect ratio or "original"
    add_subtitles=True,          # Enable subtitle generation
    whisper_model="auto",        # "auto", "tiny", "base", "small", "medium", "large"
    highlight_keywords=[],       # Keywords for highlight extraction
    context_seconds=2.0,         # Context padding for highlights
    output_path="output.mp4"     # Output file path
)
```

### Mode Comparison

| Feature | Audio Analysis | Visual Analysis |
|---------|----------------|-----------------|
| Initialization | `AutoEditor(analysis_mode="audio")` | `AutoEditor(analysis_mode="visual")` |
| Best for | Interviews, podcasts, tutorials | Movies, MVs, scene-based content |
| Speech recognition | ✅ | ❌ |
| Dynamic model selection | ✅ | ❌ |
| Keyword extraction | ✅ | ❌ |
| Audio stream detection | ✅ | ❌ |
| Scene detection | ❌ | ✅ |
| `cut_by_scenes()` | ❌ | ✅ |
| `process_video()` | ✅ | ✅ |
| `extract_highlights()` | ✅ | ✅ |

### Future: Hybrid Mode

Planned for future release: `analysis_mode="hybrid"` will combine both audio and visual analysis for comprehensive content understanding.

### Whisper Models

| Model | Size | Speed | Memory | Use Case |
|-------|------|-------|--------|----------|
| tiny | ~39M | ~10x | ~1GB | Fast, low accuracy |
| base | ~74M | ~7x | ~1GB | **Default**, good balance |
| small | ~244M | ~4x | ~2GB | Better accuracy |
| medium | ~769M | ~2x | ~5GB | High accuracy |
| large | ~1550M | 1x | ~10GB | Best accuracy |

**Note**: In local environment, only `tiny` and `base` are fully supported due to memory constraints.

## API Reference

### AutoEditor

Main class for automated video editing.

**Constructor:**
- `AutoEditor(use_smart_transcriber=True, work_dir=None)` - Create editor instance

**Methods:**
- `process_video(video_path, config)` - Process video with configuration
- `extract_highlights(video_path, keywords, output_path, context_seconds, whisper_model)` - Extract keyword segments
- `cut_by_scenes(video_path, output_dir, min_scene_duration)` - Split by scenes (Basic Mode only)

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
# Run all tests
pytest tests/ -v

# Unit tests
pytest tests/unit/ -v

# Integration tests
pytest tests/integration/ -v
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

## Documentation

- [README.md](README.md) - Main documentation
- [CHANGELOG.md](CHANGELOG.md) - Version history
- [Configuration Reference](docs/configuration.md) - Complete configuration options
- [Architecture Decisions](docs/adr/) - Design decision records

## License

MIT License - See [LICENSE](LICENSE) for details.

## Links

- GitHub: https://github.com/ZhaofanQiu/video_cut_skill
- Documentation: https://zhaofanqiu.github.io/video_cut_skill/
