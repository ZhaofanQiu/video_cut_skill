# Model Management Guide

This guide explains how to manage Whisper models for `video_cut_skill` to avoid runtime download delays.

## Quick Start

```bash
# Download all models (recommended for development)
python scripts/download_models.py all

# Download specific model
python scripts/download_models.py tiny

# Check downloaded models
python scripts/download_models.py --list
```

## Model Information

| Model | Size | Speed | Accuracy | Use Case |
|-------|------|-------|----------|----------|
| `tiny` | ~39 MB | Fastest | Lowest | Testing, quick demos |
| `base` | ~74 MB | Fast | Moderate | General use, default |
| `small` | ~244 MB | Moderate | Good | Balanced performance |
| `medium` | ~769 MB | Slow | High | Better accuracy needed |
| `large` | ~1550 MB | Slowest | Highest | Production quality |
| `turbo` | ~809 MB | Fast | High | Best speed/accuracy tradeoff |

## Default Model Configuration

The skill uses different models based on configuration:

- **Testing**: `tiny` (fast, low resource)
- **Default**: `base` (balanced)
- **High Quality**: `small` or `medium`

Change model in your code:

```python
from video_cut_skill import Transcriber, AutoEditor

# Use specific model
transcriber = Transcriber(model_name="small")
auto_editor = AutoEditor(transcriber_model="small")
```

## Cache Location

Models are cached in:
- **Linux/macOS**: `~/.cache/whisper/`
- **Windows**: `%LOCALAPPDATA%\whisper\`
- **Custom**: Set `XDG_CACHE_HOME` environment variable

```bash
# Use custom cache directory
export XDG_CACHE_HOME=/path/to/cache
python scripts/download_models.py all
```

## Manual Download

If automatic download fails, manually download models:

```bash
# Create cache directory
mkdir -p ~/.cache/whisper

# Download tiny model (~39 MB)
wget -O ~/.cache/whisper/tiny.pt \
    "https://openaipublic.azureedge.net/main/whisper/models/65147644a518d12f04e32d6f3b26facc3f8dd46e5390956a9424a650c0ce22b9/tiny.pt"

# Download base model (~74 MB)
wget -O ~/.cache/whisper/base.pt \
    "https://openaipublic.azureedge.net/main/whisper/models/ed3a0b6b1c0edf879ad9b11b1ff5dd618872ca85da7800c4836901e25c6ab6f4/base.pt"

# Download small model (~244 MB)
wget -O ~/.cache/whisper/small.pt \
    "https://openaipublic.azureedge.net/main/whisper/models/9ecf779972d90ba49c06d968637d720dd632c55bbf19d441fb42bf17a411e794/small.pt"

# Download medium model (~769 MB)
wget -O ~/.cache/whisper/medium.pt \
    "https://openaipublic.azureedge.net/main/whisper/models/345ae4da62f9b3d59415adc60127b97c714f32e89e936602e85993674d08dcb1/medium.pt"

# Download large model (~1550 MB)
wget -O ~/.cache/whisper/large.pt \
    "https://openaipublic.azureedge.net/main/whisper/models/e4b87e7e0bf463eb8e6956e646f1e277e901512310def2c24bf0e11bd3e28e9f/large.pt"

# Download turbo model (~809 MB)
wget -O ~/.cache/whisper/turbo.pt \
    "https://openaipublic.azureedge.net/main/whisper/models/e58f5b52382a8cbe8bf401df4f7bf50c65b97a5bcae07987d05ae192c1c1af4c/turbo.pt"
```

## Docker/Container Setup

For containerized deployments, pre-download models in your Dockerfile:

```dockerfile
# Pre-download models during build
RUN python scripts/download_models.py base

# Or copy pre-downloaded models
COPY models/whisper/*.pt /root/.cache/whisper/
```

## CI/CD Setup

For GitHub Actions or other CI systems, cache the models:

```yaml
- name: Cache Whisper models
  uses: actions/cache@v3
  with:
    path: ~/.cache/whisper
    key: whisper-models-${{ hashFiles('scripts/download_models.py') }}

- name: Download models
  run: python scripts/download_models.py base small
```

## Offline Usage

For air-gapped environments:

1. Download models on an internet-connected machine:
   ```bash
   python scripts/download_models.py all
   tar -czf whisper-models.tar.gz ~/.cache/whisper/
   ```

2. Transfer `whisper-models.tar.gz` to offline machine

3. Extract to cache directory:
   ```bash
   mkdir -p ~/.cache/whisper
   tar -xzf whisper-models.tar.gz -C ~/
   ```

## Troubleshooting

### Slow Downloads

- Use `wget` instead of Python download for better stability:
  ```bash
  wget -c -O ~/.cache/whisper/base.pt <url>
  ```

- Use mirror/CDN if available in your region

### Corrupted Downloads

Delete and re-download:
```bash
rm ~/.cache/whisper/base.pt
python scripts/download_models.py base
```

### Verify Model Integrity

Check file sizes match expected:
```bash
ls -lh ~/.cache/whisper/
```

Expected sizes:
- tiny.pt: ~39 MB
- base.pt: ~74 MB
- small.pt: ~244 MB
- medium.pt: ~769 MB
- large.pt: ~1550 MB
- turbo.pt: ~809 MB

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `XDG_CACHE_HOME` | Cache directory base | `~/.cache` |
| `WHISPER_MODEL` | Default model name | `base` |

## See Also

- [README](https://github.com/ZhaofanQiu/video_cut_skill/blob/main/README.md) - Installation and quick start
- [API Reference](api/index.md)
- [Whisper GitHub](https://github.com/openai/whisper)
