#!/usr/bin/env python3
"""
智能转录模块 - 支持动态模型选择和静音检测
"""

import subprocess
import json
import os
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum

class ModelSize(Enum):
    """Whisper模型大小
    
    注意：当前环境仅支持 TINY 和 BASE 模型
    SMALL/MEDIUM/LARGE 需要 2GB+/5GB+/10GB+ 内存，当前环境 4GB 不足
    未来将通过云端 API 支持高质量模型
    """
    TINY = "tiny"      # ~39M, 最快, 准确度低, 内存~1GB
    BASE = "base"      # ~74M, 平衡, 内存~1GB
    # 以下模型当前环境不支持，预留用于云端转录
    # SMALL = "small"    # ~244M, 较好准确度, 内存~2GB
    # MEDIUM = "medium"  # ~769M, 高准确度, 内存~5GB
    # LARGE = "large"    # ~1550M, 最高准确度, 内存~10GB

@dataclass
class TranscriptResult:
    """转录结果"""
    text: str
    segments: List[Dict]
    language: str
    duration: float
    model_used: str
    processing_time: float
    error: Optional[str] = None

class SmartTranscriber:
    """智能转录器"""
    
    # 模型特性配置
    # 注意：当前环境仅支持 TINY 和 BASE
    MODEL_CONFIG = {
        ModelSize.TINY: {
            'speed': 10,      # 相对速度
            'accuracy': 3,    # 准确度评分 1-10
            'memory_gb': 1,   # 内存需求
            'best_for': '快速预览、长视频初筛',
            'available': True  # 当前环境可用
        },
        ModelSize.BASE: {
            'speed': 7,
            'accuracy': 6,
            'memory_gb': 1,
            'best_for': '常规转录、短视频、输出片段',
            'available': True  # 当前环境可用
        },
        # 以下模型当前环境不支持，预留用于云端转录
        # ModelSize.SMALL: {
        #     'speed': 4,
        #     'accuracy': 7,
        #     'memory_gb': 2,
        #     'best_for': '高质量输出视频（需云端）',
        #     'available': False
        # },
        # ModelSize.MEDIUM: {
        #     'speed': 2,
        #     'accuracy': 9,
        #     'memory_gb': 5,
        #     'best_for': '重要内容精准转录（需云端）',
        #     'available': False
        # },
        # ModelSize.LARGE: {
        #     'speed': 1,
        #     'accuracy': 10,
        #     'memory_gb': 10,
        #     'best_for': '专业级转录（需云端）',
        #     'available': False
        # }
    }
    
    def __init__(self, cache_dir: str = None):
        """初始化智能转录器.

        Args:
            cache_dir: Whisper 模型缓存目录，默认使用 ~/.cache/whisper
        """
        self.cache_dir = cache_dir or os.path.expanduser("~/.cache/whisper")
        
    def has_audio_stream(self, video_path: str) -> bool:
        """检测视频是否有音频轨道"""
        try:
            cmd = [
                "ffprobe", "-v", "error",
                "-select_streams", "a:0",
                "-show_entries", "stream=codec_type",
                "-of", "json",
                video_path,
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            data = json.loads(result.stdout)
            return len(data.get('streams', [])) > 0
        except:
            return False
    
    def get_video_duration(self, video_path: str) -> float:
        """获取视频时长（秒）"""
        try:
            cmd = [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "json",
                video_path,
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            return float(json.loads(result.stdout)['format']['duration'])
        except:
            return 0.0
    
    def select_model(self, video_path: str, is_output: bool = False) -> ModelSize:
        """
        动态选择模型（适配当前环境：仅支持 tiny/base）
        
        本地环境策略：
        1. 输出视频（高光片段）：使用 BASE（最高本地质量）
        2. 完整长视频（>3分钟）：使用 TINY（快速分析）
        3. 完整短视频（<3分钟）：使用 BASE（高精度）
        
        未来云端策略：
        - 输出视频可使用 SMALL/MEDIUM/LARGE 高质量模型
        """
        duration = self.get_video_duration(video_path)
        
        if is_output:
            # 输出视频使用最高本地质量模型
            print(f"[策略] 输出视频 {duration:.1f}s，使用 BASE 模型（本地最高质量）")
            print(f"[提示] 如需更高质量，请使用云端转录 API")
            return ModelSize.BASE
        else:
            # 完整视频用于分析
            if duration > 180:  # > 3分钟
                print(f"[策略] 完整视频 {duration:.1f}s (>3分钟)，使用 TINY 模型（快速分析）")
                return ModelSize.TINY
            else:  # < 3分钟
                print(f"[策略] 完整视频 {duration:.1f}s (<3分钟)，使用 BASE 模型（高精度）")
                return ModelSize.BASE
    
    def transcribe(self, 
                   video_path: str, 
                   model: ModelSize = None,
                   language: str = "Chinese",
                   is_output: bool = False) -> TranscriptResult:
        """
        智能转录
        
        Args:
            video_path: 视频路径
            model: 指定模型（None则自动选择）
            language: 语言
            is_output: 是否为输出视频（影响模型选择策略）
        """
        import time
        start_time = time.time()
        
        # 1. 检查音频
        if not self.has_audio_stream(video_path):
            return TranscriptResult(
                text="",
                segments=[],
                language=language,
                duration=0,
                model_used="none",
                processing_time=0,
                error="【无音频】该视频没有音频轨道，无法进行语音识别。请检查：\n"
                      "  1. 视频是否包含声音\n"
                      "  2. 视频文件是否损坏\n"
                      "  3. 尝试使用其他视频文件"
            )
        
        # 2. 选择模型
        if model is None:
            model = self.select_model(video_path, is_output)
        
        # 3. 执行转录
        output_dir = os.path.dirname(video_path) or "."
        base_name = os.path.splitext(os.path.basename(video_path))[0]

        cmd = [
            "whisper", video_path,
            "--model", model.value,
            "--language", language,
            "--output_format", "json",
            "--output_dir", output_dir,
        ]

        print(f"[转录] 使用模型: {model.value}")
        print(f"[转录] 命令: {' '.join(cmd)}")

        result = subprocess.run(cmd, capture_output=True, text=True)
        
        # 4. 读取结果
        json_path = os.path.join(output_dir, f"{base_name}.json")
        if os.path.exists(json_path):
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            processing_time = time.time() - start_time
            
            return TranscriptResult(
                text=data.get('text', ''),
                segments=data.get('segments', []),
                language=data.get('language', language),
                duration=self.get_video_duration(video_path),
                model_used=model.value,
                processing_time=processing_time,
                error=None
            )
        else:
            return TranscriptResult(
                text="",
                segments=[],
                language=language,
                duration=0,
                model_used=model.value,
                processing_time=time.time() - start_time,
                error=f"转录失败: {result.stderr[:200]}"
            )
    
    def refine_transcript(self, 
                         video_path: str, 
                         rough_transcript: TranscriptResult,
                         use_cloud: bool = False) -> TranscriptResult:
        """
        精修转录：使用更高质量模型重新转录精彩片段
        
        本地环境：使用 BASE 模型重新转录
        云端模式（use_cloud=True）：使用云端 API 获取高质量转录
        
        Args:
            video_path: 输出视频路径
            rough_transcript: 粗略转录结果
            use_cloud: 是否使用云端转录（需要配置 API）
        """
        if use_cloud:
            return self._cloud_transcribe(video_path)
        else:
            print(f"\n[精修] 使用 BASE 模型重新转录输出视频...")
            print("[提示] 如需云端高质量转录，请设置 use_cloud=True")
            return self.transcribe(video_path, model=ModelSize.BASE, is_output=True)
    
    def _cloud_transcribe(self, video_path: str) -> TranscriptResult:
        """
        云端转录接口（预留）
        
        未来实现：
        - 调用 OpenAI Whisper API
        - 或调用阿里云/腾讯云语音识别 API
        - 支持 large-v3 等高质量模型
        
        Returns:
            TranscriptResult: 高质量转录结果
        """
        raise NotImplementedError(
            "云端转录功能尚未实现。\n"
            "未来支持：\n"
            "  - OpenAI Whisper API\n"
            "  - 阿里云语音识别\n"
            "  - 腾讯云语音识别"
        )
    
    def get_available_models(self) -> List[ModelSize]:
        """获取当前环境可用的模型列表"""
        return [m for m in ModelSize if self.MODEL_CONFIG.get(m, {}).get('available', False)]
    
    def check_model_availability(self, model: ModelSize) -> bool:
        """检查指定模型是否可用"""
        config = self.MODEL_CONFIG.get(model, {})
        available = config.get('available', False)
        return bool(available)


# 使用示例
if __name__ == "__main__":
    transcriber = SmartTranscriber()
    
    print("=" * 60)
    print("智能转录模块 - 本地环境（仅支持 tiny/base）")
    print("=" * 60)
    print()
    print(f"当前环境可用模型: {[m.value for m in transcriber.get_available_models()]}")
    print("提示: SMALL/MEDIUM/LARGE 模型需要云端支持")
    print()
    
    # 示例1: 静音视频检测
    print("-" * 60)
    print("示例1: 静音视频检测")
    print("-" * 60)
    
    test_silent = "/root/.openclaw/workspace/test3_silent.mp4"
    if os.path.exists(test_silent):
        result = transcriber.transcribe(test_silent)
        if result.error:
            print(f"✓ 正确检测到静音视频: {result.error}")
        else:
            print(f"✗ 应该检测到静音视频")
    else:
        print("跳过（测试文件不存在）")
    
    # 示例2: 完整视频（使用 TINY 快速分析）
    print()
    print("-" * 60)
    print("示例2: 完整视频（自动选择 TINY 模型）")
    print("-" * 60)
    
    test_full = "/root/.openclaw/workspace/test3.mp4"
    if os.path.exists(test_full):
        result = transcriber.transcribe(test_full, is_output=False)
        if not result.error:
            print(f"✓ 转录成功")
            print(f"  模型: {result.model_used}")
            print(f"  时长: {result.duration:.1f}s")
            print(f"  用时: {result.processing_time:.1f}s")
            print(f"  片段: {len(result.segments)}")
    else:
        print("跳过（测试文件不存在）")
    
    # 示例3: 输出视频（使用 BASE 高质量）
    print()
    print("-" * 60)
    print("示例3: 输出高光片段（使用 BASE 模型）")
    print("-" * 60)
    
    test_output = "/root/.openclaw/workspace/test3_30s.mp4"
    if os.path.exists(test_output):
        result = transcriber.transcribe(test_output, is_output=True)
        if not result.error:
            print(f"✓ 转录成功")
            print(f"  模型: {result.model_used}")
            print(f"  时长: {result.duration:.1f}s")
            print(f"  用时: {result.processing_time:.1f}s")
            print(f"  片段: {len(result.segments)}")
            print(f"\n前50字: {result.text[:50]}...")
    else:
        print("跳过（测试文件不存在）")
    
    # 示例4: 云端转录提示
    print()
    print("-" * 60)
    print("示例4: 云端高质量转录（预留接口）")
    print("-" * 60)
    print("未来可通过以下方式使用云端转录:")
    print("  result = transcriber.refine_transcript(video, use_cloud=True)")
    print()
    print("支持的云端服务:")
    print("  - OpenAI Whisper API")
    print("  - 阿里云语音识别")
    print("  - 腾讯云语音识别")
    print()
    print("云端转录优势:")
    print("  ✓ 支持 large-v3 等高质量模型")
    print("  ✓ 不占用本地内存")
    print("  ✓ 支持多语言和方言")
