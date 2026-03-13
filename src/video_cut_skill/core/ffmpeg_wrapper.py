"""FFmpeg wrapper for video processing."""

import logging
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import ffmpeg

logger = logging.getLogger(__name__)


class FFmpegError(Exception):
    """FFmpeg 操作错误."""
    pass


class FFmpegWrapper:
    """FFmpeg 封装类.
    
    提供高层 API 用于视频处理操作.
    """
    
    def __init__(self, ffmpeg_path: str = "ffmpeg", ffprobe_path: str = "ffprobe"):
        """初始化 FFmpeg 封装.
        
        Args:
            ffmpeg_path: ffmpeg 可执行文件路径
            ffprobe_path: ffprobe 可执行文件路径
        """
        self.ffmpeg_path = ffmpeg_path
        self.ffprobe_path = ffprobe_path
        self._check_installation()
    
    def _check_installation(self) -> None:
        """检查 FFmpeg 是否已安装."""
        try:
            result = subprocess.run(
                [self.ffmpeg_path, "-version"],
                capture_output=True,
                text=True,
                check=True,
            )
            version_line = result.stdout.split("\n")[0]
            logger.info(f"FFmpeg found: {version_line}")
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            raise FFmpegError(
                f"FFmpeg not found at {self.ffmpeg_path}. "
                "Please install FFmpeg first."
            ) from e
    
    def probe(self, video_path: Union[str, Path]) -> Dict[str, Any]:
        """获取视频元数据.
        
        Args:
            video_path: 视频文件路径
            
        Returns:
            视频元数据字典
            
        Raises:
            FFmpegError: 探测失败
        """
        video_path = str(video_path)
        try:
            return ffmpeg.probe(video_path, cmd=self.ffprobe_path)
        except ffmpeg.Error as e:
            error_msg = e.stderr.decode("utf-8") if e.stderr else str(e)
            raise FFmpegError(f"Failed to probe video: {error_msg}") from e
    
    def get_video_info(self, video_path: Union[str, Path]) -> Dict[str, Any]:
        """获取视频信息摘要.
        
        Args:
            video_path: 视频文件路径
            
        Returns:
            视频信息字典，包含:
            - duration: 时长（秒）
            - width: 宽度
            - height: 高度
            - fps: 帧率
            - bitrate: 比特率
            - codec: 编码格式
            - has_audio: 是否有音频
        """
        probe_data = self.probe(video_path)
        video_stream = next(
            (s for s in probe_data["streams"] if s["codec_type"] == "video"),
            None,
        )
        audio_stream = next(
            (s for s in probe_data["streams"] if s["codec_type"] == "audio"),
            None,
        )
        
        if not video_stream:
            raise FFmpegError("No video stream found")
        
        # 解析帧率
        fps_str = video_stream.get("r_frame_rate", "0/1")
        if "/" in fps_str:
            num, den = map(int, fps_str.split("/"))
            fps = num / den if den != 0 else 0
        else:
            fps = float(fps_str)
        
        return {
            "duration": float(probe_data["format"].get("duration", 0)),
            "width": int(video_stream.get("width", 0)),
            "height": int(video_stream.get("height", 0)),
            "fps": fps,
            "bitrate": int(probe_data["format"].get("bit_rate", 0)),
            "codec": video_stream.get("codec_name", "unknown"),
            "has_audio": audio_stream is not None,
        }
    
    def cut_clip(
        self,
        input_path: Union[str, Path],
        output_path: Union[str, Path],
        start_time: float,
        end_time: float,
        copy_codec: bool = True,
    ) -> Path:
        """剪辑视频片段.
        
        Args:
            input_path: 输入视频路径
            output_path: 输出视频路径
            start_time: 开始时间（秒）
            end_time: 结束时间（秒）
            copy_codec: 是否直接复制编码（更快但可能有精度问题）
            
        Returns:
            输出文件路径
        """
        input_path = str(input_path)
        output_path = str(output_path)
        duration = end_time - start_time
        
        try:
            stream = ffmpeg.input(input_path, ss=start_time, t=duration)
            
            if copy_codec:
                stream = ffmpeg.output(
                    stream,
                    output_path,
                    c="copy",
                    avoid_negative_ts="make_zero",
                )
            else:
                stream = ffmpeg.output(stream, output_path)
            
            ffmpeg.run(stream, cmd=self.ffmpeg_path, overwrite_output=True, quiet=True)
            logger.info(f"Cut clip saved to: {output_path}")
            return Path(output_path)
            
        except ffmpeg.Error as e:
            error_msg = e.stderr.decode("utf-8") if e.stderr else str(e)
            raise FFmpegError(f"Failed to cut clip: {error_msg}") from e
    
    def concatenate_clips(
        self,
        clip_paths: List[Union[str, Path]],
        output_path: Union[str, Path],
        reencode: bool = False,
    ) -> Path:
        """拼接多个视频片段.
        
        Args:
            clip_paths: 视频片段路径列表
            output_path: 输出路径
            reencode: 是否重新编码（如果片段格式不一致需要设为 True）
            
        Returns:
            输出文件路径
        """
        if not clip_paths:
            raise FFmpegError("No clips provided for concatenation")
        
        output_path = str(output_path)
        
        try:
            if reencode:
                # 使用 filter_complex 进行拼接
                inputs = [ffmpeg.input(str(p)) for p in clip_paths]
                stream = ffmpeg.concat(*inputs, v=1, a=1)
                stream = ffmpeg.output(stream, output_path)
            else:
                # 使用 concat demuxer（更快，但需要相同格式）
                # 创建临时文件列表
                with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
                    for clip_path in clip_paths:
                        f.write(f"file '{Path(clip_path).resolve()}'\n")
                    concat_file = f.name
                
                try:
                    stream = ffmpeg.input(concat_file, format="concat", safe=0)
                    stream = ffmpeg.output(stream, output_path, c="copy")
                    ffmpeg.run(stream, cmd=self.ffmpeg_path, overwrite_output=True, quiet=True)
                finally:
                    os.unlink(concat_file)
            
            logger.info(f"Concatenated video saved to: {output_path}")
            return Path(output_path)
            
        except ffmpeg.Error as e:
            error_msg = e.stderr.decode("utf-8") if e.stderr else str(e)
            raise FFmpegError(f"Failed to concatenate clips: {error_msg}") from e
    
    def extract_audio(
        self,
        video_path: Union[str, Path],
        output_path: Union[str, Path],
        format: str = "mp3",
        bitrate: str = "192k",
    ) -> Path:
        """提取音频.
        
        Args:
            video_path: 视频路径
            output_path: 输出音频路径
            format: 音频格式
            bitrate: 音频比特率
            
        Returns:
            输出音频路径
        """
        try:
            stream = ffmpeg.input(str(video_path))
            stream = ffmpeg.output(
                stream,
                str(output_path),
                vn=None,  # 禁用视频
                acodec="libmp3lame" if format == "mp3" else "aac",
                audio_bitrate=bitrate,
            )
            ffmpeg.run(stream, cmd=self.ffmpeg_path, overwrite_output=True, quiet=True)
            logger.info(f"Audio extracted to: {output_path}")
            return Path(output_path)
        except ffmpeg.Error as e:
            error_msg = e.stderr.decode("utf-8") if e.stderr else str(e)
            raise FFmpegError(f"Failed to extract audio: {error_msg}") from e
    
    def add_subtitle(
        self,
        video_path: Union[str, Path],
        subtitle_path: Union[str, Path],
        output_path: Union[str, Path],
        style: Optional[Dict[str, str]] = None,
    ) -> Path:
        """添加字幕到视频.
        
        Args:
            video_path: 视频路径
            subtitle_path: 字幕文件路径 (SRT/ASS)
            output_path: 输出路径
            style: 字幕样式（ASS 格式时有效）
            
        Returns:
            输出视频路径
        """
        try:
            video = ffmpeg.input(str(video_path))
            
            # 构建字幕滤镜参数
            sub_params = {"filename": str(subtitle_path)}
            if style and str(subtitle_path).endswith(".ass"):
                # ASS 样式参数
                pass  # ffmpeg-python 会自动处理
            
            video = video.filter("subtitles", **sub_params)
            stream = ffmpeg.output(video, str(output_path))
            ffmpeg.run(stream, cmd=self.ffmpeg_path, overwrite_output=True, quiet=True)
            
            logger.info(f"Video with subtitles saved to: {output_path}")
            return Path(output_path)
        except ffmpeg.Error as e:
            error_msg = e.stderr.decode("utf-8") if e.stderr else str(e)
            raise FFmpegError(f"Failed to add subtitle: {error_msg}") from e
    
    def resize_video(
        self,
        video_path: Union[str, Path],
        output_path: Union[str, Path],
        width: Optional[int] = None,
        height: Optional[int] = None,
        mode: str = "fit",  # fit, fill, stretch
    ) -> Path:
        """调整视频尺寸.
        
        Args:
            video_path: 视频路径
            output_path: 输出路径
            width: 目标宽度
            height: 目标高度
            mode: 调整模式 (fit-适应, fill-填充, stretch-拉伸)
            
        Returns:
            输出视频路径
        """
        try:
            stream = ffmpeg.input(str(video_path))
            
            if mode == "stretch":
                stream = stream.filter("scale", width=width, height=height)
            elif mode == "fit":
                # 保持比例适应目标尺寸
                stream = stream.filter(
                    "scale",
                    width=width or -1,
                    height=height or -1,
                    force_original_aspect_ratio="decrease",
                )
            elif mode == "fill":
                # 保持比例填充，可能裁剪
                stream = stream.filter(
                    "scale",
                    width=width or -1,
                    height=height or -1,
                    force_original_aspect_ratio="increase",
                )
                stream = stream.filter("crop", width, height)
            
            stream = ffmpeg.output(stream, str(output_path))
            ffmpeg.run(stream, cmd=self.ffmpeg_path, overwrite_output=True, quiet=True)
            
            logger.info(f"Resized video saved to: {output_path}")
            return Path(output_path)
        except ffmpeg.Error as e:
            error_msg = e.stderr.decode("utf-8") if e.stderr else str(e)
            raise FFmpegError(f"Failed to resize video: {error_msg}") from e
    
    def change_aspect_ratio(
        self,
        video_path: Union[str, Path],
        output_path: Union[str, Path],
        target_ratio: Tuple[int, int],
        mode: str = "pad",  # pad, crop, stretch
        pad_color: str = "black",
    ) -> Path:
        """改变视频宽高比.
        
        Args:
            video_path: 视频路径
            output_path: 输出路径
            target_ratio: 目标宽高比 (width, height)，如 (9, 16)
            mode: 调整模式 (pad-填充, crop-裁剪, stretch-拉伸)
            pad_color: 填充颜色
            
        Returns:
            输出视频路径
        """
        try:
            # 获取原始视频信息
            info = self.get_video_info(video_path)
            orig_width, orig_height = info["width"], info["height"]
            orig_ratio = orig_width / orig_height
            target_ratio_val = target_ratio[0] / target_ratio[1]
            
            stream = ffmpeg.input(str(video_path))
            
            if mode == "stretch":
                # 计算目标尺寸
                if orig_ratio > target_ratio_val:
                    new_width = int(orig_height * target_ratio_val)
                    new_height = orig_height
                else:
                    new_width = orig_width
                    new_height = int(orig_width / target_ratio_val)
                stream = stream.filter("scale", new_width, new_height)
                
            elif mode == "pad":
                # 添加填充保持比例
                stream = stream.filter(
                    "pad",
                    width=f"ih*{target_ratio[0]}/{target_ratio[1]}",
                    height="ih",
                    x="(ow-iw)/2",
                    y=0,
                    color=pad_color,
                ) if orig_ratio < target_ratio_val else stream.filter(
                    "pad",
                    width="iw",
                    height=f"iw*{target_ratio[1]}/{target_ratio[0]}",
                    x=0,
                    y="(oh-ih)/2",
                    color=pad_color,
                )
                
            elif mode == "crop":
                # 裁剪中心区域
                stream = stream.filter(
                    "crop",
                    width=f"ih*{target_ratio[0]}/{target_ratio[1]}",
                    height="ih",
                ) if orig_ratio > target_ratio_val else stream.filter(
                    "crop",
                    width="iw",
                    height=f"iw*{target_ratio[1]}/{target_ratio[0]}",
                )
            
            stream = ffmpeg.output(stream, str(output_path))
            ffmpeg.run(stream, cmd=self.ffmpeg_path, overwrite_output=True, quiet=True)
            
            logger.info(f"Aspect ratio changed video saved to: {output_path}")
            return Path(output_path)
        except ffmpeg.Error as e:
            error_msg = e.stderr.decode("utf-8") if e.stderr else str(e)
            raise FFmpegError(f"Failed to change aspect ratio: {error_msg}") from e
