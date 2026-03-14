#!/usr/bin/env python3
"""
AutoEditor - 智能视频编辑器（集成增强版）
支持智能转录、动态模型选择、静音检测
"""

import os
import sys
import subprocess
import json
from pathlib import Path
from typing import List, Dict, Optional, Union
from dataclasses import dataclass

# 导入智能转录模块
try:
    from video_cut_skill.core.smart_transcriber import SmartTranscriber, ModelSize
except ImportError:
    # 如果导入失败，添加路径
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from video_cut_skill.core.smart_transcriber import SmartTranscriber, ModelSize

from video_cut_skill.core.ffmpeg_wrapper import FFmpegWrapper


@dataclass
class EditConfig:
    """编辑配置"""
    target_duration: Optional[float] = None  # 目标时长（秒）
    aspect_ratio: str = "original"           # 目标比例 "16:9", "9:16", "original"
    add_subtitles: bool = True               # 是否添加字幕
    subtitle_model: str = "auto"             # "auto", "tiny", "base"
    highlight_keywords: List[str] = None     # 高光关键词
    output_path: Optional[str] = None
    
    def __post_init__(self):
        if self.highlight_keywords is None:
            self.highlight_keywords = []


@dataclass
class ProcessResult:
    """处理结果"""
    output_path: str
    transcript: Optional[Dict]
    duration: float
    processing_time: float
    error: Optional[str] = None


class AutoEditor:
    """智能视频编辑器"""
    
    def __init__(self, work_dir: str = None):
        self.work_dir = Path(work_dir) if work_dir else Path.cwd()
        self.work_dir.mkdir(parents=True, exist_ok=True)
        
        # 初始化组件
        self.ffmpeg = FFmpegWrapper()
        self.transcriber = SmartTranscriber()
        
        # 检查环境
        self._check_environment()
    
    def _check_environment(self):
        """检查运行环境"""
        available_models = self.transcriber.get_available_models()
        print(f"[AutoEditor] 初始化完成")
        print(f"  可用转录模型: {[m.value for m in available_models]}")
        print(f"  工作目录: {self.work_dir}")
    
    def process_video(self, video_path: str, config: EditConfig = None) -> ProcessResult:
        """
        处理视频 - 完整流程
        
        流程:
        1. 检测音频
        2. 转录（动态选择模型）
        3. 提取高光
        4. 生成字幕
        5. 输出
        """
        import time
        start_time = time.time()
        
        config = config or EditConfig()
        video_path = Path(video_path)
        
        if not video_path.exists():
            return ProcessResult(
                output_path="",
                transcript=None,
                duration=0,
                processing_time=0,
                error=f"视频文件不存在: {video_path}"
            )
        
        print(f"\n[处理开始] {video_path.name}")
        
        # 步骤1: 检测音频
        print("\n[1/5] 检测音频...")
        if not self.transcriber.has_audio_stream(str(video_path)):
            return ProcessResult(
                output_path="",
                transcript=None,
                duration=0,
                processing_time=0,
                error="视频无音频轨道，无法处理"
            )
        print("  ✓ 音频正常")
        
        # 步骤2: 转录（动态选择模型）
        print("\n[2/5] 语音识别...")
        duration = self.transcriber.get_video_duration(str(video_path))
        
        # 根据配置选择模型
        if config.subtitle_model == "auto":
            # 自动选择：短视频用base，长视频用tiny
            model = ModelSize.BASE if duration < 300 else ModelSize.TINY
        else:
            model = ModelSize(config.subtitle_model)
        
        transcript_result = self.transcriber.transcribe(
            str(video_path),
            model=model,
            is_output=False
        )
        
        if transcript_result.error:
            return ProcessResult(
                output_path="",
                transcript=None,
                duration=duration,
                processing_time=time.time() - start_time,
                error=f"转录失败: {transcript_result.error}"
            )
        
        print(f"  ✓ 转录完成")
        print(f"    模型: {transcript_result.model_used}")
        print(f"    片段: {len(transcript_result.segments)}")
        print(f"    语言: {transcript_result.language}")
        
        # 步骤3: 提取高光（如果指定了关键词）
        highlights = []
        if config.highlight_keywords:
            print(f"\n[3/5] 提取高光片段...")
            highlights = self._extract_highlights(
                transcript_result,
                config.highlight_keywords
            )
            print(f"  ✓ 找到 {len(highlights)} 个高光片段")
        
        # 步骤4: 生成字幕
        subtitle_path = None
        if config.add_subtitles:
            print("\n[4/5] 生成字幕...")
            subtitle_path = self._generate_subtitles(transcript_result)
            print(f"  ✓ 字幕: {subtitle_path}")
        
        # 步骤5: 输出
        print("\n[5/5] 生成输出...")
        output_path = self._generate_output(
            video_path,
            config,
            subtitle_path
        )
        print(f"  ✓ 输出: {output_path}")
        
        processing_time = time.time() - start_time
        
        print(f"\n[处理完成] 用时: {processing_time:.1f}s")
        
        return ProcessResult(
            output_path=str(output_path),
            transcript={
                'text': transcript_result.text,
                'segments': transcript_result.segments,
                'language': transcript_result.language
            },
            duration=duration,
            processing_time=processing_time
        )
    
    def _extract_highlights(self, transcript, keywords: List[str]) -> List[Dict]:
        """基于关键词提取高光片段"""
        highlights = []
        
        for seg in transcript.segments:
            text = seg['text']
            score = sum(1 for kw in keywords if kw in text)
            if score > 0:
                highlights.append({
                    'start': seg['start'],
                    'end': seg['end'],
                    'text': text,
                    'score': score
                })
        
        # 按得分排序，取前5
        highlights.sort(key=lambda x: x['score'], reverse=True)
        return highlights[:5]
    
    def _generate_subtitles(self, transcript) -> str:
        """生成SRT字幕"""
        srt_path = self.work_dir / "temp_subtitles.srt"
        
        with open(srt_path, 'w', encoding='utf-8') as f:
            for i, seg in enumerate(transcript.segments, 1):
                start = self._seconds_to_srt_time(seg['start'])
                end = self._seconds_to_srt_time(seg['end'])
                f.write(f"{i}\n")
                f.write(f"{start} --> {end}\n")
                f.write(f"{seg['text']}\n\n")
        
        return str(srt_path)
    
    def _seconds_to_srt_time(self, seconds: float) -> str:
        """转换为SRT时间格式"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
    
    def _generate_output(self, video_path: Path, config: EditConfig, subtitle_path: str = None) -> Path:
        """生成最终输出"""
        if config.output_path:
            output_path = Path(config.output_path)
        else:
            output_path = self.work_dir / f"{video_path.stem}_output.mp4"
        
        # 基础处理
        if subtitle_path and subtitle_path.exists():
            # 添加字幕
            cmd = [
                'ffmpeg', '-y', '-i', str(video_path),
                '-vf', f"subtitles={subtitle_path}",
                '-c:a', 'copy',
                str(output_path)
            ]
        else:
            # 复制
            cmd = ['cp', str(video_path), str(output_path)]
        
        subprocess.run(cmd, capture_output=True)
        return output_path
    
    def extract_highlights_video(self, video_path: str, keywords: List[str], 
                                  output_path: str = None, context_seconds: float = 2.0) -> str:
        """
        提取高光片段并合并
        
        优化版：使用 BASE 模型重新转录高光片段
        """
        print(f"\n[高光提取] {video_path}")
        
        # 第1步：完整视频快速分析（TINY）
        print("\n  [1/3] 完整视频分析...")
        rough_result = self.transcriber.transcribe(
            video_path,
            model=ModelSize.TINY,
            is_output=False
        )
        
        if rough_result.error:
            print(f"  ✗ 分析失败: {rough_result.error}")
            return ""
        
        # 第2步：提取高光时间段
        print("\n  [2/3] 提取高光片段...")
        highlights = self._extract_highlights(rough_result, keywords)
        
        if not highlights:
            print("  ✗ 未找到高光片段")
            return ""
        
        # 第3步：剪辑高光片段
        print(f"\n  [3/3] 剪辑 {len(highlights)} 个片段...")
        clip_files = []
        for i, h in enumerate(highlights[:3], 1):  # 最多3个
            # 添加上下文
            start = max(0, h['start'] - context_seconds)
            end = h['end'] + context_seconds
            
            clip_path = self.work_dir / f"highlight_{i}.mp4"
            cmd = [
                'ffmpeg', '-y', '-i', video_path,
                '-ss', str(start), '-to', str(end),
                '-c:v', 'libx264', '-preset', 'fast', '-crf', '23',
                '-r', '30', '-c:a', 'aac', '-b:a', '128k',
                str(clip_path)
            ]
            subprocess.run(cmd, capture_output=True)
            clip_files.append(clip_path)
            print(f"    片段{i}: {start:.1f}s-{end:.1f}s")
        
        # 合并
        if output_path:
            final_path = Path(output_path)
        else:
            final_path = self.work_dir / "highlights_final.mp4"
        
        # 创建合并列表
        list_file = self.work_dir / "concat_list.txt"
        with open(list_file, 'w') as f:
            for cf in clip_files:
                f.write(f"file '{cf}'\n")
        
        # 合并
        cmd = [
            'ffmpeg', '-y', '-f', 'concat', '-safe', '0',
            '-i', str(list_file),
            '-c:v', 'libx264', '-preset', 'fast', '-crf', '23',
            '-r', '30', '-c:a', 'aac', '-b:a', '128k',
            str(final_path)
        ]
        subprocess.run(cmd, capture_output=True)
        
        print(f"\n  ✓ 高光视频: {final_path}")
        return str(final_path)


# 便捷的调用接口
def process_video(video_path: str, **kwargs) -> ProcessResult:
    """便捷函数：处理视频"""
    editor = AutoEditor()
    config = EditConfig(**kwargs)
    return editor.process_video(video_path, config)


def extract_highlights(video_path: str, keywords: List[str], **kwargs) -> str:
    """便捷函数：提取高光"""
    editor = AutoEditor()
    return editor.extract_highlights_video(video_path, keywords, **kwargs)


if __name__ == "__main__":
    # 测试
    import sys
    
    if len(sys.argv) < 2:
        print("用法: python auto_editor_enhanced.py <视频路径>")
        sys.exit(1)
    
    video_path = sys.argv[1]
    
    # 测试完整流程
    print("=" * 60)
    print("AutoEditor 增强版测试")
    print("=" * 60)
    
    result = process_video(
        video_path,
        add_subtitles=True,
        highlight_keywords=["智能", "技术", "发展"]
    )
    
    if result.error:
        print(f"\n✗ 处理失败: {result.error}")
    else:
        print(f"\n✓ 处理成功")
        print(f"  输出: {result.output_path}")
        print(f"  时长: {result.duration:.1f}s")
        print(f"  用时: {result.processing_time:.1f}s")
        print(f"  转录片段: {len(result.transcript.get('segments', []))}")
