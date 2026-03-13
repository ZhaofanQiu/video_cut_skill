# Quick Start

## Basic Usage

### 1. Video Processing with FFmpeg

```python
from video_cut_skill import FFmpegWrapper

wrapper = FFmpegWrapper()

# Get video info
info = wrapper.get_video_info("input.mp4")
print(f"Duration: {info['duration']}s")
print(f"Resolution: {info['width']}x{info['height']}")

# Cut a clip
wrapper.cut_clip(
    "input.mp4",
    "clip.mp4",
    start_time=10.0,
    end_time=20.0,
)

# Extract audio
wrapper.extract_audio("input.mp4", "audio.mp3")

# Add subtitles
wrapper.add_subtitle("input.mp4", "subtitles.srt", "output.mp4")

# Change aspect ratio
wrapper.change_aspect_ratio(
    "input.mp4",
    "vertical.mp4",
    target_ratio=(9, 16),
    mode="pad",
)
```

### 2. Speech Recognition

```python
from video_cut_skill import Transcriber

transcriber = Transcriber(model_size="base")

# Transcribe video
result = transcriber.transcribe("video.mp4")

print(f"Text: {result.text}")
print(f"Language: {result.language}")

# Export subtitles
transcriber.export_srt(result, "subtitles.srt")
transcriber.export_ass(result, "subtitles.ass")

# Search keywords
matches = transcriber.detect_keywords(result, ["important", "key point"])
```

### 3. Scene Detection

```python
from video_cut_skill import SceneDetector

detector = SceneDetector(detector_type="content")

# Detect scenes
result = detector.detect("video.mp4")

print(f"Found {result.scene_count} scenes")

for scene in result.scenes:
    print(f"Scene: {scene.start:.2f}s - {scene.end:.2f}s")

# Split video by scenes
detector.split_video(
    "video.mp4",
    result.scenes,
    output_dir="scenes/",
)
```

### 4. Auto Editor

```python
from video_cut_skill.auto_editor import AutoEditor, EditConfig

editor = AutoEditor()

# Process video
result = editor.process_video(
    "input.mp4",
    EditConfig(
        target_duration=60,
        aspect_ratio="9:16",
        add_subtitles=True,
    ),
)

print(f"Output: {result.output_path}")

# Cut by scenes
clips = editor.cut_by_scenes("input.mp4", "output_dir/")

# Extract highlights
editor.extract_highlights(
    "input.mp4",
    keywords=["summary", "conclusion"],
    output_path="highlights.mp4",
)
```

## Next Steps

- Read the [API Reference](api/index.md)
- Check the [Testing Guide](testing-guide.md)
- See [Phase 1 Log](development/phase1-log.md) for implementation details
