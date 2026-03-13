# Video Cut Skill Documentation

## Quick Links

- [GitHub Repository](https://github.com/ZhaofanQiu/video_cut_skill)
- [API Reference](api/)
- [Tutorials](tutorials/)

## Features

- **AI-Powered Editing**: Intelligent clip selection and pacing
- **Motion Graphics**: Programmatic animation generation
- **Multi-Platform**: Support for TikTok, YouTube, Bilibili, etc.
- **Professional Quality**: Advanced transitions and effects

## Installation

```bash
pip install video-cut-skill
```

## Quick Start

```python
from video_cut_skill import AutoEditor, EditIntent

editor = AutoEditor()
result = editor.auto_edit(
    video_path="input.mp4",
    intent=EditIntent(
        target_duration=60,
        aspect_ratio="9:16",
        style="modern"
    )
)
```
