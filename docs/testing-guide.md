# 测试指南

## 环境准备

### 1. 创建虚拟环境

```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
```

### 2. 安装依赖

```bash
pip install -e "."
```

### 3. 验证 FFmpeg

```bash
ffmpeg -version
```

## 运行测试

### 单元测试

```bash
# 运行所有单元测试
pytest tests/unit/ -v

# 运行特定模块测试
pytest tests/unit/test_ffmpeg_wrapper.py -v
pytest tests/unit/test_transcriber.py -v
pytest tests/unit/test_scene_detector.py -v

# 运行带覆盖率报告
pytest tests/unit/ --cov=video_cut_skill --cov-report=html
```

### 集成测试

需要准备测试视频文件：

```bash
# 创建测试数据目录
mkdir -p tests/fixtures

# 放置测试视频（例如）
# tests/fixtures/sample.mp4
```

## 功能测试示例

### 1. FFmpeg 功能测试

```python
from video_cut_skill.core import FFmpegWrapper

wrapper = FFmpegWrapper()

# 测试视频信息获取
info = wrapper.get_video_info("tests/fixtures/sample.mp4")
print(f"Duration: {info['duration']}")
print(f"Resolution: {info['width']}x{info['height']}")

# 测试剪辑
wrapper.cut_clip(
    "tests/fixtures/sample.mp4",
    "/tmp/clip.mp4",
    start_time=5.0,
    end_time=10.0,
)

# 测试音频提取
wrapper.extract_audio(
    "tests/fixtures/sample.mp4",
    "/tmp/audio.mp3",
)
```

### 2. 语音识别测试

```python
from video_cut_skill.ai import Transcriber

transcriber = Transcriber(model_size="tiny")  # 使用小模型测试

# 转录
result = transcriber.transcribe("tests/fixtures/sample.mp4")
print(f"Text: {result.text}")
print(f"Language: {result.language}")

# 导出字幕
transcriber.export_srt(result, "/tmp/subtitles.srt")
```

### 3. 场景检测测试

```python
from video_cut_skill.ai import SceneDetector

detector = SceneDetector(detector_type="content")

# 检测场景
result = detector.detect("tests/fixtures/sample.mp4")
print(f"Found {result.scene_count} scenes")

for i, scene in enumerate(result.scenes[:5]):
    print(f"Scene {i+1}: {scene.start:.2f}s - {scene.end:.2f}s")
```

## 完整流程测试

运行示例脚本：

```bash
python examples/basic_workflow.py
```

## 测试视频生成

如果没有测试视频，可以用 FFmpeg 生成：

```bash
# 生成 30 秒测试视频
ffmpeg -f lavfi -i testsrc=duration=30:size=1920x1080:rate=30 \
       -f lavfi -i sine=frequency=1000:duration=30 \
       -pix_fmt yuv420p tests/fixtures/sample.mp4 -y
```

## 常见问题

### 1. FFmpeg 未找到

```bash
# Ubuntu/Debian
sudo apt install ffmpeg

# macOS
brew install ffmpeg
```

### 2. Whisper 模型下载失败

模型会自动下载到 `~/.cache/whisper/`。如果下载失败，可以手动下载：

```bash
# 使用 wget 下载模型
wget https://openaipublic.azureedge.net/main/whisper/models/ed3a0b6b1c0edf879ad9b11b1ff5a0e6ab5cc91e20.../base.pt \
     -O ~/.cache/whisper/base.pt
```

### 3. CUDA 不可用

如果没有 GPU，Whisper 会自动使用 CPU。可以通过设置设备：

```python
transcriber = Transcriber(model_size="base", device="cpu")
```
