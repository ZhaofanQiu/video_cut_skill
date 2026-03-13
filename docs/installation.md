# Installation

## System Requirements

- Python 3.9+
- FFmpeg 4.4+
- (Optional) CUDA-capable GPU for faster processing

## Install FFmpeg

### Ubuntu/Debian

```bash
sudo apt update
sudo apt install ffmpeg
```

### macOS

```bash
brew install ffmpeg
```

### Windows

Download from [ffmpeg.org](https://ffmpeg.org/download.html) and add to PATH.

## Install Video Cut Skill

### From PyPI (recommended)

```bash
pip install video-cut-skill
```

### From Source

```bash
git clone https://github.com/ZhaofanQiu/video_cut_skill.git
cd video_cut_skill
pip install -e "."
```

### Development Installation

```bash
git clone https://github.com/ZhaofanQiu/video_cut_skill.git
cd video_cut_skill
pip install -e ".[dev]"
```

## Verify Installation

```python
from video_cut_skill import FFmpegWrapper, Transcriber, SceneDetector

# Test FFmpeg
wrapper = FFmpegWrapper()
print("FFmpeg OK")

# Test other modules
print("All modules imported successfully!")
```

## GPU Support (Optional)

For GPU acceleration with Whisper:

```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```
