# Troubleshooting Guide

This guide covers common issues and their solutions when using `video_cut_skill`.

## Table of Contents

1. [Audio Extraction Issues](#audio-extraction-issues)
2. [Video Cutting Issues](#video-cutting-issues)
3. [Feishu File Transfer Issues](#feishu-file-transfer-issues)
4. [Model Download Issues](#model-download-issues)

---

## Audio Extraction Issues

### Problem: Extracted Audio Duration Mismatch

**Symptom**: 
- Video duration is 464s, but extracted audio is only 247s
- Audio file is significantly shorter than expected

**Root Cause**:
The video file's audio stream is corrupted or incomplete. This can happen when:
- Video file was not fully downloaded
- Network interruption during download
- Source file itself is damaged

**Error Signs**:
```
[mov,mp4,m4a,3gp,3g2,mj2] stream 1, offset 0x8f9d9a: partial file
[aac @ ...] decode_band_types: Input buffer exhausted before END element found
```

**Solution**:

1. **Verify Video Integrity** before extraction:
```python
from video_cut_skill import FFmpegWrapper

wrapper = FFmpegWrapper()
info = wrapper.get_video_info("video.mp4")

# Check if video and audio durations match
probe_data = wrapper.probe("video.mp4")
video_duration = None
audio_duration = None

for stream in probe_data.get("streams", []):
    if stream.get("codec_type") == "video":
        video_duration = float(stream.get("duration", 0))
    elif stream.get("codec_type") == "audio":
        audio_duration = float(stream.get("duration", 0))

if video_duration and audio_duration:
    diff = abs(video_duration - audio_duration)
    if diff > 5.0:
        print(f"Warning: Audio stream may be corrupted (diff: {diff:.2f}s)")
```

2. **Re-download the video file** if corruption is detected

3. **The updated `extract_audio()` method** now includes automatic integrity checks and will log warnings if audio stream issues are detected.

---

## Video Cutting Issues

### Problem: Clip Duration Longer Than Expected

**Symptom**:
- Expected 15s clip, but got 19s
- Clip starts earlier or ends later than specified

**Root Cause**:
Video codecs use keyframes (I-frames) for efficient compression. When using `copy_codec=True`, FFmpeg must align cut points to the nearest keyframe, which can cause:
- Start time to shift to the previous keyframe (earlier)
- End time to shift to the next keyframe (later)
- Resulting in longer duration than requested

**Example**:
```python
# With copy_codec=True (fast mode)
wrapper.cut_clip("input.mp4", "output.mp4", 60, 75, copy_codec=True)
# Expected: 15s clip
# Actual: 19.32s (includes extra frames to next keyframe)
```

**Solution**:

1. **Use Precise Mode** (default now):
```python
from video_cut_skill import FFmpegWrapper

wrapper = FFmpegWrapper()

# Recommended: Precise mode (re-encodes for accuracy)
wrapper.cut_clip("input.mp4", "output.mp4", 60, 75)  # copy_codec=False (default)
```

2. **Use Fast Mode Only When**:
   - You need maximum speed
   - Precise duration is not critical
   - Video will be further processed

```python
# Fast mode (may have duration deviation)
wrapper.cut_clip("input.mp4", "output.mp4", 60, 75, copy_codec=True)
```

3. **Verify Clip Duration** after cutting:
```python
output_info = wrapper.get_video_info("output.mp4")
actual_duration = output_info["duration"]
expected_duration = 15.0

if abs(actual_duration - expected_duration) > 1.0:
    print(f"Duration mismatch: expected {expected_duration}s, got {actual_duration}s")
```

### Keyframe Explanation

Video compression uses three frame types:
- **I-frame (Keyframe)**: Complete frame, can be decoded independently
- **P-frame**: References previous frames
- **B-frame**: References both previous and future frames

When cutting with `copy_codec=True`, the cut must start at an I-frame because P/B frames cannot be decoded without their reference frames. This causes the shift in timing.

---

## Feishu File Transfer Issues

### Problem: MP4 Videos Not Received

**Symptom**:
- MP4 files sent via Feishu do not arrive
- MP3 audio files work fine
- No error message on sender side

**Root Cause**:
Feishu has file extension restrictions in direct messages. `.mp4` files are blocked while `.mp3` files are allowed.

**Solution**:

1. **Change File Extension** before sending:
```bash
# Rename .mp4 to .bin
cp video.mp4 video.bin

# Send video.bin via Feishu
# Recipient renames back to .mp4 after download
```

2. **In Python Code**:
```python
import shutil
from pathlib import Path

def send_video_feishu(video_path: str) -> str:
    """Prepare video for Feishu transfer by changing extension."""
    video_path = Path(video_path)
    fake_path = video_path.with_suffix('.bin')
    shutil.copy(video_path, fake_path)
    return str(fake_path)

# Usage
fake_file = send_video_feishu("/tmp/output.mp4")
# Send fake_file via Feishu
# Tell recipient to rename .bin back to .mp4
```

3. **Supported vs Blocked Extensions**:

| Extension | Status | Workaround |
|-----------|--------|------------|
| .mp3 | ✅ Works | None needed |
| .mp4 | ❌ Blocked | Use .bin |
| .mov | ❌ Blocked | Use .bin |
| .avi | ❌ Blocked | Use .bin |
| .bin | ✅ Works | None needed |
| .txt | ✅ Works | None needed |

---

## Model Download Issues

### Problem: Whisper Model Download Interrupted

**Symptom**:
- Model download stops at partial progress (e.g., 27%)
- File exists but is incomplete
- SHA256 checksum mismatch

**Root Cause**:
Network instability or timeout during download.

**Solution**:

1. **Use the download script with retry**:
```bash
python scripts/download_models.py tiny
```

2. **Manual download with wget** (more stable):
```bash
mkdir -p ~/.cache/whisper
wget -c -O ~/.cache/whisper/tiny.pt \
    "https://openaipublic.azureedge.net/main/whisper/models/.../tiny.pt"
```

3. **Verify downloaded file**:
```bash
ls -lh ~/.cache/whisper/
# Expected: tiny.pt ~39MB, base.pt ~74MB
```

4. **Clear and re-download if corrupted**:
```bash
rm ~/.cache/whisper/tiny.pt
python scripts/download_models.py tiny
```

---

## General Debugging Tips

### Enable Verbose Logging

```python
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

# Or specifically for video_cut_skill
logging.getLogger('video_cut_skill').setLevel(logging.DEBUG)
```

### Check FFmpeg Version

```bash
ffmpeg -version
ffprobe -version
```

Minimum recommended: FFmpeg 4.0+

### Verify File Integrity

```bash
# Check video file
ffprobe -v error -show_streams video.mp4

# Check for errors
ffmpeg -v error -i video.mp4 -f null - 2>&1
```

---

## Getting Help

If issues persist:

1. Check the [GitHub Issues](https://github.com/ZhaofanQiu/video_cut_skill/issues)
2. Enable debug logging and share logs
3. Include FFmpeg version: `ffmpeg -version`
4. Provide sample code that reproduces the issue
