#!/usr/bin/env python3
"""Test 9 - 测试 Whisper base 模型和修复后的字幕功能."""

import sys
from pathlib import Path

# 添加 video_cut_skill 到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from video_cut_skill.auto_editor import AutoEditor, EditConfig

def test9():
    """测试9: 使用 base 模型处理视频."""
    print("="*60)
    print("Test 9 - Whisper base model + subtitle fix")
    print("="*60)
    
    # 使用已有的视频
    video_path = "/tmp/test3_video.mp4"
    
    if not Path(video_path).exists():
        print(f"❌ Video not found: {video_path}")
        print("Using alternative video...")
        # 尝试其他可用视频
        alternatives = [
            "/tmp/test3_auto_output.mp4",
            "/root/.openclaw/workspace/test_video.mp4",
        ]
        for alt in alternatives:
            if Path(alt).exists():
                video_path = alt
                print(f"✅ Using: {video_path}")
                break
        else:
            print("❌ No video found!")
            return 1
    
    print(f"\n🎬 Processing: {video_path}")
    
    # 创建 AutoEditor，使用 base 模型
    editor = AutoEditor()
    
    config = EditConfig(
        target_duration=30,  # 只处理前30秒
        add_subtitles=True,
        whisper_model="base",  # 明确使用 base 模型
        output_path="/tmp/test9_output.mp4"
    )
    
    try:
        result = editor.process_video(video_path, config)
        print(f"\n✅ Test 9 passed!")
        print(f"   Output: {result.output_path}")
        
        if result.transcript:
            print(f"   Language: {result.transcript.language}")
            print(f"   Segments: {len(result.transcript.segments)}")
        
        # 复制一份带 .bin 后缀的用于飞书发送
        import shutil
        feishu_path = Path("/tmp/test9_output_subtitled.mp4.bin")
        if Path(result.output_path).exists():
            shutil.copy(result.output_path, str(feishu_path).replace('.bin', ''))
            # 如果有字幕版本，复制那个
            subtitled = Path(result.output_path).parent / f"{Path(result.output_path).stem}_subtitled{Path(result.output_path).suffix}"
            if subtitled.exists():
                shutil.copy(subtitled, feishu_path)
                print(f"   Feishu ready: {feishu_path}")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Test 9 failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(test9())
