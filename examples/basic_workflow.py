#!/usr/bin/env python3
"""Basic workflow example - 基础工作流示例."""

import tempfile
from pathlib import Path


def create_test_video(output_path: str, duration: int = 30):
    """创建测试视频."""
    import subprocess
    
    cmd = [
        "ffmpeg",
        "-f", "lavfi",
        "-i", f"testsrc=duration={duration}:size=1920x1080:rate=30",
        "-f", "lavfi",
        "-i", f"sine=frequency=1000:duration={duration}",
        "-pix_fmt", "yuv420p",
        "-y",
        output_path,
    ]
    
    subprocess.run(cmd, capture_output=True, check=True)
    print(f"Test video created: {output_path}")


def test_ffmpeg_wrapper(video_path: str):
    """测试 FFmpeg 封装."""
    print("\n=== Testing FFmpeg Wrapper ===")
    
    from video_cut_skill.core import FFmpegWrapper
    
    wrapper = FFmpegWrapper()
    
    # 获取视频信息
    print("\n1. Getting video info...")
    info = wrapper.get_video_info(video_path)
    print(f"   Duration: {info['duration']:.2f}s")
    print(f"   Resolution: {info['width']}x{info['height']}")
    print(f"   FPS: {info['fps']}")
    print(f"   Has audio: {info['has_audio']}")
    
    # 剪辑视频
    print("\n2. Cutting clip (5-10s)...")
    clip_path = "/tmp/test_clip.mp4"
    wrapper.cut_clip(video_path, clip_path, start_time=5.0, end_time=10.0)
    print(f"   Clip saved: {clip_path}")
    
    # 提取音频
    print("\n3. Extracting audio...")
    audio_path = "/tmp/test_audio.mp3"
    wrapper.extract_audio(video_path, audio_path)
    print(f"   Audio saved: {audio_path}")
    
    # 转换宽高比
    print("\n4. Converting aspect ratio to 9:16...")
    vertical_path = "/tmp/test_vertical.mp4"
    wrapper.change_aspect_ratio(
        video_path,
        vertical_path,
        target_ratio=(9, 16),
        mode="pad",
    )
    print(f"   Vertical video saved: {vertical_path}")
    
    print("\n✅ FFmpeg wrapper tests passed!")
    return clip_path


def test_transcriber(video_path: str):
    """测试语音识别."""
    print("\n=== Testing Transcriber ===")
    
    from video_cut_skill.ai import Transcriber
    
    # 使用 tiny 模型进行测试（快）
    print("\n1. Loading Whisper model (tiny)...")
    transcriber = Transcriber(model_size="tiny")
    
    print("\n2. Transcribing video...")
    result = transcriber.transcribe(video_path)
    
    print(f"   Language: {result.language}")
    print(f"   Duration: {result.duration:.2f}s")
    print(f"   Segments: {len(result.segments)}")
    
    if result.text:
        print(f"   Text preview: {result.text[:100]}...")
    
    # 导出字幕
    print("\n3. Exporting SRT subtitle...")
    srt_path = "/tmp/test_subtitle.srt"
    transcriber.export_srt(result, srt_path)
    print(f"   SRT saved: {srt_path}")
    
    print("\n✅ Transcriber tests passed!")
    return result


def test_scene_detector(video_path: str):
    """测试场景检测."""
    print("\n=== Testing Scene Detector ===")
    
    from video_cut_skill.ai import SceneDetector
    
    print("\n1. Detecting scenes...")
    detector = SceneDetector(detector_type="content")
    result = detector.detect(video_path, min_scene_len=1.0)
    
    print(f"   Total scenes: {result.scene_count}")
    print(f"   Video duration: {result.total_duration:.2f}s")
    
    if result.scenes:
        print("\n2. Scene list (first 5):")
        for i, scene in enumerate(result.scenes[:5]):
            print(f"   Scene {i+1}: {scene.start:.2f}s - {scene.end:.2f}s "
                  f"(duration: {scene.duration:.2f}s)")
    
    print("\n✅ Scene detector tests passed!")
    return result


def main():
    """主函数."""
    print("=" * 60)
    print("Video Cut Skill - Basic Workflow Test")
    print("=" * 60)
    
    # 创建临时目录
    temp_dir = tempfile.mkdtemp()
    video_path = f"{temp_dir}/test_video.mp4"
    
    try:
        # 创建测试视频
        print("\nCreating test video...")
        create_test_video(video_path, duration=30)
        
        # 测试 FFmpeg
        test_ffmpeg_wrapper(video_path)
        
        # 测试语音识别
        test_transcriber(video_path)
        
        # 测试场景检测
        test_scene_detector(video_path)
        
        print("\n" + "=" * 60)
        print("🎉 All tests passed!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    finally:
        # 清理
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    return 0


if __name__ == "__main__":
    exit(main())
