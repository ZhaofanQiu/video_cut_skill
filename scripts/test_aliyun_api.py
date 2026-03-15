#!/usr/bin/env python3
"""Test script for Aliyun API connectivity and file upload."""

import os
import sys
import tempfile

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../src"))

from video_cut_skill.clients.aliyun_client import AliyunClient
from video_cut_skill.core.file_upload import AliyunFileUploader
from video_cut_skill.exceptions import VideoCutSkillError


def create_test_audio() -> str:
    """Create a test audio file."""
    # Create a simple test audio file using FFmpeg
    test_file = tempfile.mktemp(suffix=".wav")
    
    # Generate a 5-second silent audio file
    cmd = f"ffmpeg -f lavfi -i anullsrc=r=16000:cl=mono -t 5 -acodec pcm_s16le {test_file} -y 2>/dev/null"
    result = os.system(cmd)
    
    if result != 0:
        print("❌ 无法创建测试音频文件，请确保已安装FFmpeg")
        sys.exit(1)
    
    return test_file


def test_api_key() -> bool:
    """Test if API key is configured."""
    api_key = os.getenv("DASHSCOPE_API_KEY")
    
    print("=" * 60)
    print("测试1: API Key配置检查")
    print("=" * 60)
    
    if not api_key:
        print("❌ DASHSCOPE_API_KEY 环境变量未设置")
        print("   请设置环境变量：export DASHSCOPE_API_KEY=your_api_key")
        return False
    
    masked_key = api_key[:8] + "..." + api_key[-4:] if len(api_key) > 12 else "***"
    print(f"✓ API Key已配置: {masked_key}")
    return True


def test_llm_connection() -> bool:
    """Test LLM API connection."""
    print("\n" + "=" * 60)
    print("测试2: LLM API连通性测试")
    print("=" * 60)
    
    try:
        client = AliyunClient()
        
        # Simple test prompt
        response = client.chat_completion(
            messages=[{"role": "user", "content": "你好，请回复'测试成功'"}],
            temperature=0.1,
        )
        
        if response and "测试" in response:
            print(f"✓ LLM API连接成功")
            print(f"  响应: {response[:50]}...")
            return True
        else:
            print(f"⚠ LLM API返回意外响应: {response}")
            return False
            
    except Exception as e:
        print(f"❌ LLM API连接失败: {e}")
        return False


def test_file_upload() -> bool:
    """Test file upload functionality."""
    print("\n" + "=" * 60)
    print("测试3: 文件上传测试")
    print("=" * 60)
    
    test_file = None
    try:
        # Create test audio file
        print("创建测试音频文件...")
        test_file = create_test_audio()
        print(f"✓ 测试文件已创建: {test_file}")
        
        # Try to upload
        uploader = AliyunFileUploader()
        print("上传文件到DashScope...")
        url = uploader.upload(test_file)
        
        if url and (url.startswith("http://") or url.startswith("https://")):
            print(f"✓ 文件上传成功")
            print(f"  URL: {url[:80]}...")
            return True
        else:
            print(f"❌ 上传返回无效URL: {url}")
            return False
            
    except Exception as e:
        print(f"❌ 文件上传失败: {e}")
        return False
    finally:
        # Cleanup
        if test_file and os.path.exists(test_file):
            os.unlink(test_file)


def test_transcription() -> bool:
    """Test transcription API."""
    print("\n" + "=" * 60)
    print("测试4: 语音转录API测试")
    print("=" * 60)
    
    test_file = None
    try:
        # Create test audio file
        print("创建测试音频文件...")
        test_file = create_test_audio()
        
        client = AliyunClient()
        
        print("调用Paraformer转录API（这可能需要30-60秒）...")
        result = client.transcribe(test_file, language_hints=["zh"])
        
        if result and result.full_text is not None:
            print(f"✓ 转录API调用成功")
            print(f"  音频时长: {result.duration_ms}ms")
            print(f"  句子数: {len(result.sentences)}")
            if result.sentences:
                print(f"  示例文本: {result.sentences[0].text[:50]}...")
            return True
        else:
            print("❌ 转录结果为空")
            return False
            
    except Exception as e:
        print(f"❌ 转录API调用失败: {e}")
        return False
    finally:
        if test_file and os.path.exists(test_file):
            os.unlink(test_file)


def main():
    """Run all tests."""
    print("\n" + "🎬 Video Cut Skill - 阿里云API连通性测试".center(60))
    print()
    
    results = []
    
    # Test 1: API Key
    results.append(("API Key配置", test_api_key()))
    
    # If API key is not set, stop here
    if not results[0][1]:
        print("\n" + "=" * 60)
        print("测试中止：请先配置API Key")
        print("=" * 60)
        sys.exit(1)
    
    # Test 2: LLM Connection
    results.append(("LLM API连通性", test_llm_connection()))
    
    # Test 3: File Upload
    results.append(("文件上传", test_file_upload()))
    
    # Test 4: Transcription (optional, takes longer)
    print("\n" + "=" * 60)
    print("是否测试语音转录API？(需要30-60秒) [y/N]:", end=" ")
    choice = input().strip().lower()
    if choice == "y":
        results.append(("语音转录API", test_transcription()))
    else:
        print("跳过转录API测试")
    
    # Summary
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    
    for name, passed in results:
        status = "✓ 通过" if passed else "❌ 失败"
        print(f"{name}: {status}")
    
    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)
    
    print("-" * 60)
    print(f"总计: {passed_count}/{total_count} 项测试通过")
    
    if passed_count == total_count:
        print("\n🎉 所有测试通过！阿里云API配置正确。")
        return 0
    else:
        print("\n⚠️ 部分测试失败，请检查配置。")
        return 1


if __name__ == "__main__":
    sys.exit(main())
