# TOOLS.md - Local Notes

Skills define _how_ tools work. This file is for _your_ specifics — the stuff that's unique to your setup.

## What Goes Here

Things like:

- Camera names and locations
- SSH hosts and aliases
- Preferred voices for TTS
- Speaker/room names
- Device nicknames
- Anything environment-specific

## Examples

```markdown
### Cameras

- living-room → Main area, 180° wide angle
- front-door → Entrance, motion-triggered

### SSH

- home-server → 192.168.1.100, user: admin

### TTS

- Preferred voice: "Nova" (warm, slightly British)
- Default speaker: Kitchen HomePod
```

## Why Separate?

Skills are shared. Your setup is yours. Keeping them apart means you can update skills without losing your notes, and share skills without leaking your infrastructure.

---

Add whatever helps you do your job. This is your cheat sheet.

---

## Bug Fixes Log

### 2026-03-14: Audio Loss in Subtitled Videos

**Problem**: `add_subtitle()` method in `ffmpeg_wrapper.py` was only processing video stream, causing audio to be lost in output videos.

**Root Cause**: The FFmpeg command was only filtering video stream without passing audio stream through.

**Solution**: Updated `add_subtitle()` to handle both video and audio streams:
- Split input into video and audio streams
- Apply subtitle filter to video stream
- Combine both streams in output with proper codecs

**Code Change** (in `src/video_cut_skill/core/ffmpeg_wrapper.py`):
```python
# Before - only video stream
video = ffmpeg.input(str(video_path))
video = video.filter("subtitles", **sub_params)
stream = ffmpeg.output(video, str(output_path))

# After - video + audio streams
input_stream = ffmpeg.input(str(video_path))
video = input_stream.video
audio = input_stream.audio
video = video.filter("subtitles", **sub_params)
stream = ffmpeg.output(video, audio, str(output_path),
                       vcodec="libx264",
                       acodec="aac",
                       audio_bitrate="128k")
```

**Verification**: Test 9 confirmed that output videos now contain both video and audio tracks.

---

## Feishu File Transfer Notes

### Issue: MP4 Files Not Received

**Problem**: When sending `.mp4` video files via Feishu, the recipient does not receive them. However, `.mp3` audio files work fine.

**Root Cause**: Feishu has restrictions on `.mp4` file extensions in direct messages.

**Solution**: Change file extension to `.bin` (or other non-video extension) before sending.

### Workaround

```bash
# Rename MP4 to BIN before sending
cp video.mp4 video.bin

# Send video.bin via Feishu
# Recipient should rename back to .mp4 after download
```

### Testing

- ✅ `.mp3` - Works
- ❌ `.mp4` - Blocked
- ✅ `.bin` - Works (must rename after download)

### Notes

- This is a Feishu platform limitation, not a code issue
- Consider implementing automatic extension renaming for Feishu channel
- Document this for users in deployment guides
