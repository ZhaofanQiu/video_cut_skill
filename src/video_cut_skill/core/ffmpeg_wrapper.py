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
        copy_codec: bool = False,  # 默认改为 False，确保精确剪辑
    ) -> Path:
        """剪辑视频片段.
        
        Args:
            input_path: 输入视频路径
            output_path: 输出视频路径
            start_time: 开始时间（秒）
            end_time: 结束时间（秒）
            copy_codec: 是否直接复制编码
                - True: 更快，但可能因关键帧对齐导致时长偏差
                - False: 重新编码，更精确但较慢（默认）
            
        Returns:
            输出文件路径
            
        Note:
            当 copy_codec=True 时，由于视频编码使用关键帧（I-frame），
            剪辑的起止时间会自动对齐到最近的关键帧，可能导致：
            - 实际剪辑时长比预期稍长（多包含几帧）
            - 剪辑起始时间可能比指定时间稍早
            
            如需精确剪辑，请使用 copy_codec=False（默认）
            
        Example:
            # 精确剪辑（推荐）
            wrapper.cut_clip("input.mp4", "output.mp4", 10, 20)  # reencode 模式
            
            # 快速剪辑（可能有轻微偏差）
            wrapper.cut_clip("input.mp4", "output.mp4", 10, 20, copy_codec=True)
        """
        input_path = str(input_path)
        output_path = str(output_path)
        duration = end_time - start_time
        
        if duration <= 0:
            raise ValueError(f"Invalid duration: {duration}. end_time must be > start_time")
        
        try:
            if copy_codec:
                # 快速模式：复制编码，但可能有关键帧对齐问题
                stream = ffmpeg.input(input_path, ss=start_time, t=duration)
                stream = ffmpeg.output(
                    stream,
                    output_path,
                    c="copy",
                    avoid_negative_ts="make_zero",
                )
                logger.info(f"Cutting clip (fast copy mode): {start_time}s - {end_time}s")
            else:
                # 精确模式：重新编码，确保时间精确
                stream = ffmpeg.input(input_path, ss=start_time, t=duration)
                stream = ffmpeg.output(
                    stream,
                    output_path,
                    vcodec="libx264",
                    acodec="aac",
                    video_bitrate="2M",
                    audio_bitrate="128k",
                    pix_fmt="yuv420p",
                    avoid_negative_ts="make_zero",
                )
                logger.info(f"Cutting clip (precise reencode mode): {start_time}s - {end_time}s")
            
            ffmpeg.run(stream, cmd=self.ffmpeg_path, overwrite_output=True, quiet=True)
            
            # 验证输出文件
            if not Path(output_path).exists():
                raise FFmpegError("Clip creation failed: output file not created")
            
            # 获取实际剪辑时长
            output_info = self.get_video_info(output_path)
            actual_duration = output_info.get("duration", 0)
            expected_duration = end_time - start_time
            duration_diff = abs(actual_duration - expected_duration)
            
            if duration_diff > 1.0:
                logger.warning(
                    f"Clip duration mismatch. Expected: {expected_duration:.2f}s, "
                    f"Actual: {actual_duration:.2f}s, Diff: {duration_diff:.2f}s. "
                    f"Use copy_codec=False for precise cutting."
                )
            
            logger.info(f"Clip saved: {output_path} (duration: {actual_duration:.2f}s)")
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
            
        Raises:
            FFmpegError: 提取失败或音频流损坏
            VideoIntegrityError: 视频文件完整性检查失败
        """
        video_path = Path(video_path)
        output_path = Path(output_path)
        
        # 1. 检查视频文件是否存在
        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")
        
        try:
            # 2. 获取视频和音频流信息，检查完整性
            probe_data = self.probe(video_path)
            video_duration = None
            audio_duration = None
            
            for stream in probe_data.get("streams", []):
                if stream.get("codec_type") == "video":
                    video_duration = float(stream.get("duration", 0))
                elif stream.get("codec_type") == "audio":
                    audio_duration = float(stream.get("duration", 0))
            
            # 3. 检查音频流是否存在
            if audio_duration is None:
                raise FFmpegError(f"No audio stream found in video: {video_path}")
            
            # 4. 检查音频流完整性（与视频流时长对比）
            if video_duration and audio_duration > 0:
                duration_diff = abs(video_duration - audio_duration)
                if duration_diff > 5.0:  # 允许5秒误差
                    logger.warning(
                        f"Audio stream may be corrupted. "
                        f"Video duration: {video_duration:.2f}s, "
                        f"Audio duration: {audio_duration:.2f}s, "
                        f"Difference: {duration_diff:.2f}s"
                    )
                    # 不抛出错误，但记录警告，继续尝试提取
            
            # 5. 提取音频
            stream = ffmpeg.input(str(video_path))
            stream = ffmpeg.output(
                stream,
                str(output_path),
                vn=None,  # 禁用视频
                acodec="libmp3lame" if format == "mp3" else "aac",
                audio_bitrate=bitrate,
            )
            ffmpeg.run(stream, cmd=self.ffmpeg_path, overwrite_output=True, quiet=True)
            
            # 6. 验证输出音频
            if not output_path.exists():
                raise FFmpegError("Audio extraction failed: output file not created")
            
            output_info = self.probe(output_path)
            output_duration = float(output_info.get("format", {}).get("duration", 0))
            
            # 7. 检查输出音频完整性
            if audio_duration > 0 and output_duration > 0:
                output_diff = abs(audio_duration - output_duration)
                if output_diff > 1.0:  # 输出与原始音频流差异超过1秒
                    logger.warning(
                        f"Extracted audio duration mismatch. "
                        f"Expected: {audio_duration:.2f}s, "
                        f"Got: {output_duration:.2f}s"
                    )
            
            logger.info(f"Audio extracted to: {output_path} "
                       f"(duration: {output_duration:.2f}s)")
            return output_path
            
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
            # 同时输入视频和音频流
            input_stream = ffmpeg.input(str(video_path))
            video = input_stream.video
            audio = input_stream.audio
            
            # 构建字幕滤镜参数
            sub_params = {"filename": str(subtitle_path)}
            if style and str(subtitle_path).endswith(".ass"):
                # ASS 样式参数
                pass  # ffmpeg-python 会自动处理
            
            # 给视频添加字幕滤镜
            video = video.filter("subtitles", **sub_params)
            
            # 合并视频和音频输出
            stream = ffmpeg.output(video, audio, str(output_path),
                                   vcodec="libx264",
                                   acodec="aac",
                                   audio_bitrate="128k")
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
