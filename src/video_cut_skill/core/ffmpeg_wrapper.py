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
            raise FFmpegError(f"FFmpeg not found at {self.ffmpeg_path}. " "Please install FFmpeg first.") from e

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
                    logger.warning(f"Extracted audio duration mismatch. " f"Expected: {audio_duration:.2f}s, " f"Got: {output_duration:.2f}s")

            logger.info(f"Audio extracted to: {output_path} " f"(duration: {output_duration:.2f}s)")
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
            stream = ffmpeg.output(video, audio, str(output_path), vcodec="libx264", acodec="aac", audio_bitrate="128k")
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
                stream = (
                    stream.filter(
                        "pad",
                        width=f"ih*{target_ratio[0]}/{target_ratio[1]}",
                        height="ih",
                        x="(ow-iw)/2",
                        y=0,
                        color=pad_color,
                    )
                    if orig_ratio < target_ratio_val
                    else stream.filter(
                        "pad",
                        width="iw",
                        height=f"iw*{target_ratio[1]}/{target_ratio[0]}",
                        x=0,
                        y="(oh-ih)/2",
                        color=pad_color,
                    )
                )

            elif mode == "crop":
                # 裁剪中心区域
                stream = (
                    stream.filter(
                        "crop",
                        width=f"ih*{target_ratio[0]}/{target_ratio[1]}",
                        height="ih",
                    )
                    if orig_ratio > target_ratio_val
                    else stream.filter(
                        "crop",
                        width="iw",
                        height=f"iw*{target_ratio[1]}/{target_ratio[0]}",
                    )
                )

            stream = ffmpeg.output(stream, str(output_path))
            ffmpeg.run(stream, cmd=self.ffmpeg_path, overwrite_output=True, quiet=True)

            logger.info(f"Aspect ratio changed video saved to: {output_path}")
            return Path(output_path)
        except ffmpeg.Error as e:
            error_msg = e.stderr.decode("utf-8") if e.stderr else str(e)
            raise FFmpegError(f"Failed to change aspect ratio: {error_msg}") from e

    def overlay_video(
        self,
        base_video: Union[str, Path],
        overlay_video: Union[str, Path],
        output_path: Union[str, Path],
        position: str = "right_bottom",
        scale: float = 0.25,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
        margin: int = 20,
    ) -> Path:
        """画中画 (PIP) 效果 - 将视频叠加到另一个视频上.

        Args:
            base_video: 基础视频路径（主视频）
            overlay_video: 叠加视频路径（小视频）
            output_path: 输出路径
            position: 叠加位置，可选:
                - "left_top": 左上
                - "right_top": 右上
                - "left_bottom": 左下
                - "right_bottom": 右下 (默认)
                - "center": 居中
            scale: 叠加视频缩放比例 (相对于基础视频的宽度)，默认 0.25 (25%)
            start_time: 叠加开始时间（秒），默认从0开始
            end_time: 叠加结束时间（秒），默认到叠加视频结束
            margin: 距离边缘的边距（像素），默认20

        Returns:
            输出视频路径

        Example:
            # 右上角显示小视频
            wrapper.overlay_video(
                "main.mp4",
                "inset.mp4",
                "output.mp4",
                position="right_top",
                scale=0.3,
                start_time=5.0,
                end_time=15.0
            )
        """
        base_video = str(base_video)
        overlay_video = str(overlay_video)
        output_path = str(output_path)

        try:
            # 获取基础视频信息
            base_info = self.get_video_info(base_video)
            base_width = base_info["width"]
            base_height = base_info["height"]

            # 计算叠加视频尺寸
            overlay_width = int(base_width * scale)
            overlay_height = -1  # 保持宽高比

            # 读取输入
            base = ffmpeg.input(base_video)
            overlay_input = ffmpeg.input(overlay_video)

            # 获取基础视频信息以检查是否有音频
            base_probe = self.probe(base_video)
            base_has_audio = any(s.get("codec_type") == "audio" for s in base_probe.get("streams", []))

            # 获取叠加视频的实际高度（用于计算位置）
            overlay_info = self.get_video_info(overlay_video)
            overlay_orig_width = overlay_info["width"]
            overlay_orig_height = overlay_info["height"]
            overlay_new_height = int(overlay_orig_height * (overlay_width / overlay_orig_width))

            # 获取叠加视频信息以检查是否有音频
            overlay_probe = self.probe(overlay_video)
            overlay_has_audio = any(s.get("codec_type") == "audio" for s in overlay_probe.get("streams", []))

            # 处理时间范围
            overlay_video_stream = overlay_input.video
            if start_time is not None or end_time is not None:
                if start_time is not None:
                    overlay_video_stream = overlay_video_stream.filter("trim", start=start_time)
                if end_time is not None:
                    duration = end_time - (start_time or 0)
                    overlay_video_stream = overlay_video_stream.filter("trim", duration=duration)
                overlay_video_stream = overlay_video_stream.filter("setpts", "PTS-STARTPTS")

            # 缩放叠加视频
            overlay_scaled = overlay_video_stream.filter("scale", overlay_width, overlay_height)

            # 计算位置坐标
            if position == "left_top":
                x = margin
                y = margin
            elif position == "right_top":
                x = base_width - overlay_width - margin
                y = margin
            elif position == "left_bottom":
                x = margin
                y = base_height - overlay_new_height - margin
            elif position == "right_bottom":
                x = base_width - overlay_width - margin
                y = base_height - overlay_new_height - margin
            elif position == "center":
                x = (base_width - overlay_width) // 2
                y = (base_height - overlay_new_height) // 2
            else:
                raise ValueError(f"Invalid position: {position}. " f"Use: left_top, right_top, left_bottom, right_bottom, center")

            # 使用 filter_complex 进行叠加
            stream = ffmpeg.filter(
                [base.video, overlay_scaled],
                "overlay",
                x=x,
                y=y,
                shortest=1,
            )

            # 处理音频
            if base_has_audio and overlay_has_audio:
                overlay_audio = overlay_input.audio
                if start_time is not None or end_time is not None:
                    if start_time is not None:
                        overlay_audio = overlay_audio.filter("atrim", start=start_time)
                    if end_time is not None:
                        duration = end_time - (start_time or 0)
                        overlay_audio = overlay_audio.filter("atrim", duration=duration)
                    overlay_audio = overlay_audio.filter("asetpts", "PTS-STARTPTS")
                # 叠加视频的音量调低一些
                overlay_audio = overlay_audio.filter("volume", 0.7)
                audio = ffmpeg.filter([base.audio, overlay_audio], "amix", inputs=2, duration="first")
                stream = ffmpeg.output(stream, audio, output_path, vcodec="libx264", acodec="aac")
            elif base_has_audio:
                stream = ffmpeg.output(stream, base.audio, output_path, vcodec="libx264", acodec="aac")
            elif overlay_has_audio:
                stream = ffmpeg.output(stream, overlay_input.audio, output_path, vcodec="libx264", acodec="aac")
            else:
                stream = ffmpeg.output(stream, output_path, vcodec="libx264")

            ffmpeg.run(stream, cmd=self.ffmpeg_path, overwrite_output=True, quiet=True)

            logger.info(f"PIP video saved to: {output_path} (position: {position}, scale: {scale})")
            return Path(output_path)

        except ffmpeg.Error as e:
            error_msg = e.stderr.decode("utf-8") if e.stderr else str(e)
            raise FFmpegError(f"Failed to overlay video: {error_msg}") from e

    def merge_videos_side_by_side(
        self,
        left_video: Union[str, Path],
        right_video: Union[str, Path],
        output_path: Union[str, Path],
        mode: str = "fit",
    ) -> Path:
        """左右拼接两个视频（画中画的一种变体）.

        Args:
            left_video: 左侧视频路径
            right_video: 右侧视频路径
            output_path: 输出路径
            mode: 调整模式 (fit-适应, fill-填充, stretch-拉伸)

        Returns:
            输出视频路径
        """
        left_video = str(left_video)
        right_video = str(right_video)
        output_path = str(output_path)

        try:
            # 获取视频信息
            left_info = self.get_video_info(left_video)
            right_info = self.get_video_info(right_video)

            left_height = left_info["height"]
            right_height = right_info["height"]

            # 确定输出尺寸（取两个视频的最大高度）
            target_height = max(left_height, right_height)
            target_width = target_height * 2  # 左右各占一半

            # 读取输入
            left = ffmpeg.input(left_video)
            right = ffmpeg.input(right_video)

            if mode == "fit":
                # 缩放并保持比例，确保尺寸为偶数
                target_width_half = (target_width // 2) // 2 * 2
                target_height = target_height // 2 * 2
                left = left.filter("scale", target_width_half, target_height, force_original_aspect_ratio="decrease")
                left = left.filter("scale", "trunc(iw/2)*2", "trunc(ih/2)*2")
                right = right.filter("scale", target_width_half, target_height, force_original_aspect_ratio="decrease")
                right = right.filter("scale", "trunc(iw/2)*2", "trunc(ih/2)*2")
            elif mode == "stretch":
                # 拉伸填充，确保尺寸为偶数
                target_width_half = (target_width // 2) // 2 * 2
                target_height = target_height // 2 * 2
                left = left.filter("scale", target_width_half, target_height)
                right = right.filter("scale", target_width_half, target_height)
            elif mode == "fill":
                # 裁剪填充
                left = left.filter("scale", target_width // 2, target_height, force_original_aspect_ratio="increase")
                left = left.filter("crop", (target_width // 2) // 2 * 2, target_height // 2 * 2)
                right = right.filter("scale", target_width // 2, target_height, force_original_aspect_ratio="increase")
                right = right.filter("crop", (target_width // 2) // 2 * 2, target_height // 2 * 2)

            # 水平拼接
            video = ffmpeg.filter([left, right], "hstack", inputs=2)

            # 处理音频
            left_probe = self.probe(left_video)
            left_has_audio = any(s.get("codec_type") == "audio" for s in left_probe.get("streams", []))
            right_probe = self.probe(right_video)
            right_has_audio = any(s.get("codec_type") == "audio" for s in right_probe.get("streams", []))

            if left_has_audio and right_has_audio:
                audio = ffmpeg.filter([left.audio, right.audio], "amix", inputs=2, duration="first")
                stream = ffmpeg.output(video, audio, output_path, vcodec="libx264", acodec="aac")
            elif left_has_audio:
                stream = ffmpeg.output(video, left.audio, output_path, vcodec="libx264", acodec="aac")
            elif right_has_audio:
                stream = ffmpeg.output(video, right.audio, output_path, vcodec="libx264", acodec="aac")
            else:
                stream = ffmpeg.output(video, output_path, vcodec="libx264")

            ffmpeg.run(stream, cmd=self.ffmpeg_path, overwrite_output=True, quiet=True)

            logger.info(f"Side-by-side video saved to: {output_path}")
            return Path(output_path)

        except ffmpeg.Error as e:
            error_msg = e.stderr.decode("utf-8") if e.stderr else str(e)
            raise FFmpegError(f"Failed to merge videos side by side: {error_msg}") from e

    def stack_videos_vertical(
        self,
        top_video: Union[str, Path],
        bottom_video: Union[str, Path],
        output_path: Union[str, Path],
        mode: str = "fit",
    ) -> Path:
        """上下堆叠两个视频（画中画的一种变体）.

        Args:
            top_video: 上方视频路径
            bottom_video: 下方视频路径
            output_path: 输出路径
            mode: 调整模式 (fit-适应, fill-填充, stretch-拉伸)

        Returns:
            输出视频路径
        """
        top_video = str(top_video)
        bottom_video = str(bottom_video)
        output_path = str(output_path)

        try:
            # 获取视频信息
            top_info = self.get_video_info(top_video)
            bottom_info = self.get_video_info(bottom_video)

            top_width = top_info["width"]
            bottom_width = bottom_info["width"]

            # 确定输出尺寸（取两个视频的最大宽度）
            target_width = max(top_width, bottom_width)
            target_height = target_width  # 上下各占一半

            # 读取输入
            top = ffmpeg.input(top_video)
            bottom = ffmpeg.input(bottom_video)

            if mode == "fit":
                # 缩放并保持比例，确保尺寸为偶数
                target_width = target_width // 2 * 2
                target_height_half = (target_height // 2) // 2 * 2
                top = top.filter("scale", target_width, target_height_half, force_original_aspect_ratio="decrease")
                top = top.filter("scale", "trunc(iw/2)*2", "trunc(ih/2)*2")
                bottom = bottom.filter("scale", target_width, target_height_half, force_original_aspect_ratio="decrease")
                bottom = bottom.filter("scale", "trunc(iw/2)*2", "trunc(ih/2)*2")
            elif mode == "stretch":
                # 拉伸填充，确保尺寸为偶数
                target_width = target_width // 2 * 2
                target_height_half = (target_height // 2) // 2 * 2
                top = top.filter("scale", target_width, target_height_half)
                bottom = bottom.filter("scale", target_width, target_height_half)
            elif mode == "fill":
                # 裁剪填充
                top = top.filter("scale", target_width, target_height // 2, force_original_aspect_ratio="increase")
                top = top.filter("crop", target_width // 2 * 2, (target_height // 2) // 2 * 2)
                bottom = bottom.filter("scale", target_width, target_height // 2, force_original_aspect_ratio="increase")
                bottom = bottom.filter("crop", target_width // 2 * 2, (target_height // 2) // 2 * 2)

            # 垂直拼接
            video = ffmpeg.filter([top, bottom], "vstack", inputs=2)

            # 处理音频
            top_probe = self.probe(top_video)
            top_has_audio = any(s.get("codec_type") == "audio" for s in top_probe.get("streams", []))
            bottom_probe = self.probe(bottom_video)
            bottom_has_audio = any(s.get("codec_type") == "audio" for s in bottom_probe.get("streams", []))

            if top_has_audio and bottom_has_audio:
                audio = ffmpeg.filter([top.audio, bottom.audio], "amix", inputs=2, duration="first")
                stream = ffmpeg.output(video, audio, output_path, vcodec="libx264", acodec="aac")
            elif top_has_audio:
                stream = ffmpeg.output(video, top.audio, output_path, vcodec="libx264", acodec="aac")
            elif bottom_has_audio:
                stream = ffmpeg.output(video, bottom.audio, output_path, vcodec="libx264", acodec="aac")
            else:
                stream = ffmpeg.output(video, output_path, vcodec="libx264")

            ffmpeg.run(stream, cmd=self.ffmpeg_path, overwrite_output=True, quiet=True)

            logger.info(f"Stacked video saved to: {output_path}")
            return Path(output_path)

        except ffmpeg.Error as e:
            error_msg = e.stderr.decode("utf-8") if e.stderr else str(e)
            raise FFmpegError(f"Failed to stack videos vertically: {error_msg}") from e
