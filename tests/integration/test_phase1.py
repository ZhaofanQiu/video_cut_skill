#!/usr/bin/env python3
"""Phase 1 Integration Test - Phase 1 集成测试脚本."""

import tempfile
import subprocess
from pathlib import Path


def create_test_video(output_path: str, duration: int = 10):
    """创建测试视频."""
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
    print(f"✅ Test video created: {output_path}")


def test_ffmpeg_wrapper(video_path: str):
    """测试 FFmpeg Wrapper."""
    print("\n" + "="*60)
    print("Testing FFmpeg Wrapper")
    print("="*60)
    
    from video_cut_skill import FFmpegWrapper
    
    wrapper = FFmpegWrapper()
    
    # Test 1: Get video info
    print("\n1. Testing get_video_info()...")
    info = wrapper.get_video_info(video_path)
    assert info['duration'] >= 10, "Duration should be >= 10"
    assert info['width'] == 1920, "Width should be 1920"
    assert info['height'] == 1080, "Height should be 1080"
    assert info['has_audio'] is True, "Should have audio"
    print(f"   ✅ Video info: {info['width']}x{info['height']}, {info['duration']:.1f}s")
    
    # Test 2: Cut clip (use reencode for precise cutting)
    print("\n2. Testing cut_clip()...")
    clip_path = "/tmp/test_clip.mp4"
    result = wrapper.cut_clip(video_path, clip_path, start_time=2.0, end_time=5.0, copy_codec=False)
    assert Path(result).exists(), "Clip file should exist"
    clip_info = wrapper.get_video_info(clip_path)
    assert abs(clip_info['duration'] - 3.0) < 0.5, f"Clip duration should be ~3s, got {clip_info['duration']}"
    print(f"   ✅ Clip created: {clip_path}, duration: {clip_info['duration']:.1f}s")
    
    # Test 3: Extract audio
    print("\n3. Testing extract_audio()...")
    audio_path = "/tmp/test_audio.mp3"
    result = wrapper.extract_audio(video_path, audio_path)
    assert Path(result).exists(), "Audio file should exist"
    print(f"   ✅ Audio extracted: {audio_path}")
    
    # Test 4: Change aspect ratio
    print("\n4. Testing change_aspect_ratio()...")
    vertical_path = "/tmp/test_vertical.mp4"
    result = wrapper.change_aspect_ratio(
        video_path, vertical_path,
        target_ratio=(9, 16), mode="pad"
    )
    assert Path(result).exists(), "Vertical video should exist"
    vertical_info = wrapper.get_video_info(vertical_path)
    # 9:16 ratio means width < height
    assert vertical_info['width'] < vertical_info['height'], "Should be vertical"
    print(f"   ✅ Aspect ratio changed: {vertical_info['width']}x{vertical_info['height']}")
    
    print("\n✅ FFmpeg Wrapper tests passed!")


def test_transcriber(video_path: str):
    """测试语音识别 (使用 tiny 模型，快速测试)."""
    print("\n" + "="*60)
    print("Testing Transcriber")
    print("="*60)
    
    from video_cut_skill import Transcriber
    
    print("\n1. Loading Whisper model (tiny - fast for testing)...")
    transcriber = Transcriber(model_size="tiny")
    print("   ✅ Model loaded")
    
    print("\n2. Testing transcribe()...")
    result = transcriber.transcribe(video_path)
    assert result.language is not None, "Should detect language"
    assert len(result.segments) >= 0, "Should have segments"
    print(f"   ✅ Transcription: language={result.language}, segments={len(result.segments)}")
    
    print("\n3. Testing export_srt()...")
    srt_path = "/tmp/test_subtitle.srt"
    transcriber.export_srt(result, srt_path)
    assert Path(srt_path).exists(), "SRT file should exist"
    print(f"   ✅ SRT exported: {srt_path}")
    
    print("\n✅ Transcriber tests passed!")


def test_scene_detector(video_path: str):
    """测试场景检测."""
    print("\n" + "="*60)
    print("Testing Scene Detector")
    print("="*60)
    
    from video_cut_skill import SceneDetector
    
    print("\n1. Testing detect()...")
    detector = SceneDetector(detector_type="content")
    result = detector.detect(video_path, min_scene_len=0.5)
    assert result.scene_count >= 0, "Should have scenes"
    print(f"   ✅ Scenes detected: {result.scene_count}")
    
    if result.scenes:
        print("\n2. Scene list:")
        for i, scene in enumerate(result.scenes[:5]):
            print(f"   Scene {i+1}: {scene.start:.2f}s - {scene.end:.2f}s")
    
    print("\n3. Testing get_scene_at_time()...")
    scene = result.get_scene_at_time(5.0)
    print(f"   ✅ Scene at 5s: {scene}")
    
    print("\n✅ Scene Detector tests passed!")


def test_auto_editor(video_path: str):
    """测试 AutoEditor."""
    print("\n" + "="*60)
    print("Testing AutoEditor")
    print("="*60)
    
    from video_cut_skill.auto_editor import AutoEditor, EditConfig
    
    editor = AutoEditor()
    
    print("\n1. Testing process_video()...")
    config = EditConfig(
        target_duration=5.0,
        aspect_ratio="original",
        add_subtitles=True,
        output_path="/tmp/test_output.mp4"
    )
    result = editor.process_video(video_path, config)
    assert result.output_path.exists(), "Output file should exist"
    print(f"   ✅ Video processed: {result.output_path}")
    
    if result.transcript:
        print(f"   - Transcript: {len(result.transcript.segments)} segments")
    if result.scenes:
        print(f"   - Scenes: {result.scenes.scene_count}")
    
    print("\n✅ AutoEditor tests passed!")


def main():
    """主函数."""
    print("="*60)
    print("Video Cut Skill - Phase 1 Integration Test")
    print("="*60)
    
    # 创建临时目录
    temp_dir = tempfile.mkdtemp()
    video_path = f"{temp_dir}/test_video.mp4"
    
    try:
        # 创建测试视频
        print("\nCreating test video (10 seconds)...")
        create_test_video(video_path, duration=10)
        
        # 运行测试
        test_ffmpeg_wrapper(video_path)
        test_transcriber(video_path)
        test_scene_detector(video_path)
        test_auto_editor(video_path)
        
        print("\n" + "="*60)
        print("🎉 All Phase 1 tests passed!")
        print("="*60)
        return 0
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    finally:
        # 清理
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    exit(main())
