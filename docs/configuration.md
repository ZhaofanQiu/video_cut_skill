# Configuration Reference

Complete reference for all configuration options in Video Cut Skill.

## EditConfig

Configuration for video editing operations.

```python
from video_cut_skill import EditConfig

config = EditConfig(
    target_duration=60.0,        # Target output duration in seconds
    aspect_ratio="9:16",         # Output aspect ratio
    add_subtitles=True,          # Whether to add subtitles
    output_path="output.mp4",    # Output file path
    whisper_model="auto",        # Whisper model for transcription
    highlight_keywords=[],       # Keywords for highlight extraction
    context_seconds=2.0,         # Context padding for highlights
)
```

### Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `target_duration` | `Optional[float]` | `None` | Target duration in seconds. `None` means no duration limit. |
| `aspect_ratio` | `str` | `"original"` | Output aspect ratio. Options: `"original"`, `"16:9"`, `"9:16"`, `"1:1"`, `"4:3"` |
| `add_subtitles` | `bool` | `True` | Whether to burn subtitles into the output video |
| `output_path` | `Optional[str]` | `None` | Output file path. `None` generates automatic path |
| `whisper_model` | `str` | `"base"` | Whisper model size. Options: `"auto"`, `"tiny"`, `"base"`, `"small"`, `"medium"`, `"large"` |
| `highlight_keywords` | `List[str]` | `[]` | Keywords to search for highlight extraction |
| `context_seconds` | `float` | `2.0` | Seconds of padding around highlight segments |

## AutoEditor Analysis Modes

AutoEditor supports two analysis modes via the `analysis_mode` parameter:

### Audio Analysis Mode (Default)

```python
from video_cut_skill import AutoEditor

editor = AutoEditor(analysis_mode="audio")  # Default
```

**Features:**
- Speech recognition with Whisper
- Dynamic model selection (auto/base/tiny)
- Audio stream detection
- Keyword-based highlight extraction

**Best for:** Interviews, podcasts, tutorials, speech-heavy content

### Visual Analysis Mode

```python
from video_cut_skill import AutoEditor

editor = AutoEditor(analysis_mode="visual")
```

**Features:**
- Scene detection with PySceneDetect
- Shot boundary detection
- Visual continuity analysis
- `cut_by_scenes()` method available

**Best for:** Movies, MVs, scene-based content

### Mode Comparison

| Feature | Audio Analysis | Visual Analysis |
|---------|----------------|-----------------|
| Initialization | `AutoEditor(analysis_mode="audio")` | `AutoEditor(analysis_mode="visual")` |
| Speech recognition | ✅ | ❌ |
| Dynamic model selection | ✅ | ❌ |
| Scene detection | ❌ | ✅ |
| `cut_by_scenes()` | ❌ | ✅ |
| `process_video()` | ✅ | ✅ |
| `extract_highlights()` | ✅ | ✅ |

## Whisper Models

Available Whisper models and their characteristics:

| Model | Size | Speed | Memory | Best For |
|-------|------|-------|--------|----------|
| `tiny` | ~39M | 10x | ~1GB | Fast preview, long videos |
| `base` | ~74M | 7x | ~1GB | Balanced quality, most videos |
| `small` | ~244M | 4x | ~2GB | Better accuracy |
| `medium` | ~769M | 2x | ~5GB | High accuracy |
| `large` | ~1550M | 1x | ~10GB | Professional quality |

**Note:** In local environment, only `tiny` and `base` are fully supported due to memory constraints.

### Model Selection Strategy

When using `whisper_model="auto"` (audio analysis mode):

```python
if video_duration < 300:  # < 5 minutes
    selected_model = "base"
else:
    selected_model = "tiny"  # Faster for long videos
```

When `is_output=True` (processing final clips):

```python
selected_model = "base"  # Always use best local quality
```

## Retry Configuration

Pre-configured retry policies for different operations:

### NETWORK_RETRY

For network operations (API calls, downloads):

```python
from video_cut_skill.utils import NETWORK_RETRY

@NETWORK_RETRY()
def fetch_data():
    # Will retry on ConnectionError, TimeoutError, OSError
    # Max 5 attempts, delays: 1s, 2s, 4s, 8s, 16s (+ jitter)
    pass
```

**Settings:**
- Max attempts: 5
- Initial delay: 1.0s
- Max delay: 30.0s
- Exceptions: `ConnectionError`, `TimeoutError`, `OSError`

### DOWNLOAD_RETRY

For file downloads:

```python
from video_cut_skill.utils import DOWNLOAD_RETRY

@DOWNLOAD_RETRY()
def download_file(url):
    # Will retry on network/IO errors
    # Max 3 attempts, delays: 2s, 4s, 8s (+ jitter)
    pass
```

**Settings:**
- Max attempts: 3
- Initial delay: 2.0s
- Max delay: 60.0s
- Exceptions: `ConnectionError`, `TimeoutError`, `IOError`

### API_RETRY

For API calls with faster retries:

```python
from video_cut_skill.utils import API_RETRY

@API_RETRY()
def call_api():
    # Quick retries for API calls
    # Max 3 attempts, delays: 1s, 2s, 4s (+ jitter)
    pass
```

**Settings:**
- Max attempts: 3
- Initial delay: 1.0s
- Max delay: 10.0s
- Exceptions: `ConnectionError`, `TimeoutError`

## Custom Retry Configuration

```python
from video_cut_skill.utils import retry_with_backoff

@retry_with_backoff(
    max_attempts=5,
    initial_delay=0.5,
    max_delay=30.0,
    exponential_base=2.0,
    jitter=True,
    exceptions=(ValueError, RuntimeError),
    on_retry=lambda e, attempt, delay: print(f"Retry {attempt}: {e}"),
)
def my_function():
    pass
```

## FFmpeg Settings

FFmpeg wrapper uses the following default settings:

### Video Encoding

| Setting | Default | Description |
|---------|---------|-------------|
| Video codec | `libx264` | H.264 encoder |
| Preset | `medium` | Encoding speed/quality tradeoff |
| CRF | `23` | Quality (0=lossless, 51=worst, 23=default) |
| Pixel format | `yuv420p` | Compatibility format |

### Audio Encoding

| Setting | Default | Description |
|---------|---------|-------------|
| Audio codec | `aac` | Advanced Audio Coding |
| Bitrate | `128k` | Audio bitrate |
| Sample rate | `44100` | Sample rate in Hz |

### Scene Detection

| Setting | Default | Description |
|---------|---------|-------------|
| Detector type | `"content"` | Detection algorithm |
| Threshold | `27.0` | Scene change threshold (lower = more sensitive) |
| Min scene length | `1.0` | Minimum scene duration in seconds |

## Cache Configuration

Cache settings for expensive operations:

```python
from video_cut_skill.utils import CacheManager

cache = CacheManager(
    cache_dir="~/.cache/video_cut_skill",
    max_size_gb=5.0,
    ttl_hours=24 * 7,  # 1 week
)
```

### Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `cache_dir` | `str` | `"~/.cache/video_cut_skill"` | Cache directory path |
| `max_size_gb` | `float` | `5.0` | Maximum cache size in GB |
| `ttl_hours` | `float` | `168` (7 days) | Time-to-live for cached items |

## Logging Configuration

Structured logging configuration:

```python
from video_cut_skill.utils import setup_structured_logging

setup_structured_logging(
    level="INFO",
    format="json",  # or "text"
    output_file="video_cut.log",
)
```

### Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `level` | `str` | `"INFO"` | Log level: `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `format` | `str` | `"text"` | Output format: `text` or `json` |
| `output_file` | `Optional[str]` | `None` | Log file path (console only if None) |

## Environment Variables

Video Cut Skill respects the following environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `VIDEO_CUT_LOG_LEVEL` | Default log level | `INFO` |
| `VIDEO_CUT_CACHE_DIR` | Cache directory | `~/.cache/video_cut_skill` |
| `VIDEO_CUT_WORK_DIR` | Working directory for temp files | Current directory |
| `WHISPER_CACHE_DIR` | Whisper model cache | `~/.cache/whisper` |
| `FFMPEG_PATH` | Path to ffmpeg binary | System PATH |
| `FFPROBE_PATH` | Path to ffprobe binary | System PATH |

## Complete Example

```python
from video_cut_skill import AutoEditor, EditConfig
from video_cut_skill.utils import setup_structured_logging
import os

# Setup logging
setup_structured_logging(
    level=os.getenv("VIDEO_CUT_LOG_LEVEL", "INFO"),
    format="json",
)

# Create editor with audio analysis mode
editor = AutoEditor(analysis_mode="audio")

# Configure processing
config = EditConfig(
    target_duration=60.0,
    aspect_ratio="9:16",
    add_subtitles=True,
    whisper_model="auto",
    highlight_keywords=["intro", "summary"],
    context_seconds=3.0,
)

# Process video
result = editor.process_video("input.mp4", config)
```

## See Also

- [README](https://github.com/ZhaofanQiu/video_cut_skill/blob/main/README.md) - Get started quickly
- [API Reference](api/index.md) - Complete API documentation
- [Architecture Decisions](adr/README.md) - Design decisions and rationale
