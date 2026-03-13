"""Audio enhancement module - 音频增强模块."""

import logging
import subprocess
from pathlib import Path
from typing import Union

from video_cut_skill.core.ffmpeg_wrapper import FFmpegWrapper

logger = logging.getLogger(__name__)


class AudioEnhancer:
    """音频增强器.

    提供音频降噪、音量标准化等增强功能.
    """

    def __init__(self, ffmpeg: FFmpegWrapper = None):
        """初始化音频增强器.

        Args:
            ffmpeg: FFmpeg包装器实例
        """
        self.ffmpeg = ffmpeg or FFmpegWrapper()

    def normalize_lufs(
        self,
        input_path: Union[str, Path],
        output_path: Union[str, Path],
        target_lufs: float = -14.0,
        true_peak: float = -1.0,
    ) -> Path:
        """音量标准化 (LUFS).

        使用 FFmpeg 的 loudnorm 滤镜进行音量标准化，
        符合流媒体平台标准 (YouTube/Spotify 使用 -14 LUFS).

        Args:
            input_path: 输入音频/视频路径
            output_path: 输出路径
            target_lufs: 目标响度 (LUFS)，默认 -14
            true_peak: 真实峰值限制 (dB)，默认 -1

        Returns:
            输出文件路径
        """
        input_path = Path(input_path)
        output_path = Path(output_path)

        logger.info(f"Normalizing audio: {input_path} -> {output_path}")
        logger.info(f"Target LUFS: {target_lufs}")

        # 构建 loudnorm 参数
        loudnorm_params = f"loudnorm=I={target_lufs}:TP={true_peak}:LRA=11:" f"print_format=summary"

        cmd = [
            "ffmpeg",
            "-i",
            str(input_path),
            "-af",
            loudnorm_params,
            "-c:v",
            "copy",  # 视频直接复制
            "-ar",
            "48000",  # 采样率
            "-y",
            str(output_path),
        ]

        try:
            subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                text=True,
            )
            logger.info(f"Audio normalized: {output_path}")
            return output_path
        except subprocess.CalledProcessError as e:
            logger.error(f"Normalization failed: {e.stderr}")
            raise

    def reduce_noise(
        self,
        input_path: Union[str, Path],
        output_path: Union[str, Path],
        noise_reduction_db: float = 12.0,
    ) -> Path:
        """简单降噪处理.

        使用 FFmpeg 的 afftdn 滤镜进行频域降噪.
        注意：这适用于简单的背景噪音，对于复杂噪音效果有限.

        Args:
            input_path: 输入音频/视频路径
            output_path: 输出路径
            noise_reduction_db: 降噪强度 (dB)，默认 12

        Returns:
            输出文件路径
        """
        input_path = Path(input_path)
        output_path = Path(output_path)

        logger.info(f"Reducing noise: {input_path} -> {output_path}")

        # 使用 afftdn (FFT domain denoiser)
        # nr 参数控制降噪强度
        afftdn_params = f"afftdn=nr={noise_reduction_db}"

        cmd = [
            "ffmpeg",
            "-i",
            str(input_path),
            "-af",
            afftdn_params,
            "-c:v",
            "copy",
            "-y",
            str(output_path),
        ]

        try:
            subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                text=True,
            )
            logger.info(f"Noise reduced: {output_path}")
            return output_path
        except subprocess.CalledProcessError as e:
            logger.error(f"Noise reduction failed: {e.stderr}")
            raise

    def extract_and_enhance(
        self,
        video_path: Union[str, Path],
        output_path: Union[str, Path],
        normalize: bool = True,
        noise_reduction: bool = False,
    ) -> Path:
        """提取并增强音频.

        从视频中提取音频并应用增强处理.

        Args:
            video_path: 输入视频路径
            output_path: 输出音频路径
            normalize: 是否进行音量标准化
            noise_reduction: 是否进行降噪

        Returns:
            输出音频路径
        """
        video_path = Path(video_path)
        output_path = Path(output_path)

        logger.info(f"Extracting and enhancing audio from: {video_path}")

        # 构建滤镜链
        filters = []

        if noise_reduction:
            filters.append("afftdn=nr=12")

        if normalize:
            filters.append("loudnorm=I=-14:TP=-1:LRA=11")

        if not filters:
            # 无增强，直接提取
            return self.ffmpeg.extract_audio(video_path, output_path)

        # 构建 FFmpeg 命令
        filter_chain = ",".join(filters)

        cmd = [
            "ffmpeg",
            "-i",
            str(video_path),
            "-vn",  # 无视频
            "-af",
            filter_chain,
            "-ar",
            "48000",
            "-ac",
            "2",  # 立体声
            "-y",
            str(output_path),
        ]

        try:
            subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                text=True,
            )
            logger.info(f"Audio extracted and enhanced: {output_path}")
            return output_path
        except subprocess.CalledProcessError as e:
            logger.error(f"Audio enhancement failed: {e.stderr}")
            raise


class AudioAnalyzer:
    """音频分析器.

    提供音频特征分析功能.
    """

    def __init__(self):
        """初始化音频分析器."""
        pass

    def detect_silence(
        self,
        audio_path: Union[str, Path],
        silence_threshold: float = -50.0,
        min_silence_duration: float = 0.5,
    ) -> list:
        """检测静音段落.

        Args:
            audio_path: 音频路径
            silence_threshold: 静音阈值 (dB)，默认 -50
            min_silence_duration: 最小静音时长 (秒)

        Returns:
            静音段落列表 [(start, end), ...]
        """
        import subprocess

        cmd = [
            "ffmpeg",
            "-i",
            str(audio_path),
            "-af",
            f"silencedetect=noise={silence_threshold}dB:d={min_silence_duration}",
            "-f",
            "null",
            "-",
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
        )

        # 解析 silencedetect 输出
        silences = []
        lines = result.stderr.split("\n")
        silence_start = None

        for line in lines:
            if "silence_start:" in line:
                silence_start = float(line.split("silence_start: ")[1].split()[0])
            elif "silence_end:" in line and silence_start is not None:
                silence_end = float(line.split("silence_end: ")[1].split()[0])
                silences.append((silence_start, silence_end))
                silence_start = None

        return silences

    def get_audio_info(self, audio_path: Union[str, Path]) -> dict:
        """获取音频信息.

        Args:
            audio_path: 音频路径

        Returns:
            音频信息字典
        """
        import json
        import subprocess

        cmd = [
            "ffprobe",
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-show_streams",
            str(audio_path),
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
        )

        data = json.loads(result.stdout)

        # 查找音频流
        audio_stream = None
        for stream in data.get("streams", []):
            if stream.get("codec_type") == "audio":
                audio_stream = stream
                break

        if not audio_stream:
            return {}

        return {
            "codec": audio_stream.get("codec_name"),
            "sample_rate": int(audio_stream.get("sample_rate", 0)),
            "channels": audio_stream.get("channels"),
            "duration": float(audio_stream.get("duration", 0)),
            "bit_rate": int(audio_stream.get("bit_rate", 0)),
        }
