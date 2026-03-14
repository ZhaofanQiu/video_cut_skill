"""Tests for audio module."""

import subprocess
from unittest.mock import MagicMock, patch

import pytest

from video_cut_skill.audio import AudioAnalyzer, AudioEnhancer
from video_cut_skill.core.ffmpeg_wrapper import FFmpegWrapper


class TestAudioEnhancer:
    """AudioEnhancer tests."""

    @pytest.fixture
    def temp_dir(self, tmp_path):
        """Temporary directory for test files."""
        return tmp_path

    @pytest.fixture
    def enhancer(self):
        """AudioEnhancer instance."""
        return AudioEnhancer()

    @pytest.fixture
    def sample_video(self, temp_dir):
        """Create a sample video file for testing."""
        video_path = temp_dir / "sample.mp4"
        video_path.write_text("fake video content")
        return video_path

    def test_initialization_default(self):
        """Test initialization with default FFmpeg."""
        enhancer = AudioEnhancer()
        assert enhancer.ffmpeg is not None
        assert isinstance(enhancer.ffmpeg, FFmpegWrapper)

    def test_initialization_custom_ffmpeg(self):
        """Test initialization with custom FFmpeg wrapper."""
        mock_ffmpeg = MagicMock(spec=FFmpegWrapper)
        enhancer = AudioEnhancer(ffmpeg=mock_ffmpeg)
        assert enhancer.ffmpeg == mock_ffmpeg

    @patch("subprocess.run")
    def test_normalize_lufs_success(self, mock_run, enhancer, sample_video, temp_dir):
        """Test successful LUFS normalization."""
        mock_run.return_value = MagicMock(returncode=0, stderr="")

        output_path = temp_dir / "output.mp4"
        result = enhancer.normalize_lufs(sample_video, output_path, target_lufs=-16.0)

        assert result == output_path
        mock_run.assert_called_once()

        # Check that ffmpeg command was called
        call_args = mock_run.call_args
        assert call_args[0][0][0] == "ffmpeg"
        assert "-i" in call_args[0][0]
        assert "loudnorm" in " ".join(call_args[0][0])

    @patch("subprocess.run")
    def test_normalize_lufs_default_params(self, mock_run, enhancer, sample_video, temp_dir):
        """Test LUFS normalization with default parameters."""
        mock_run.return_value = MagicMock(returncode=0, stderr="")

        output_path = temp_dir / "output.mp4"
        enhancer.normalize_lufs(sample_video, output_path)

        call_args = mock_run.call_args[0][0]
        # Check default LUFS value (-14)
        cmd_str = " ".join(call_args)
        assert "I=-14" in cmd_str
        assert "TP=-1" in cmd_str

    @patch("subprocess.run")
    def test_normalize_lufs_failure(self, mock_run, enhancer, sample_video, temp_dir):
        """Test LUFS normalization failure."""
        mock_run.side_effect = subprocess.CalledProcessError(
            returncode=1,
            cmd=["ffmpeg"],
            stderr="FFmpeg error: invalid input",
        )

        output_path = temp_dir / "output.mp4"
        with pytest.raises(subprocess.CalledProcessError):
            enhancer.normalize_lufs(sample_video, output_path)

    @patch("subprocess.run")
    def test_reduce_noise_success(self, mock_run, enhancer, sample_video, temp_dir):
        """Test successful noise reduction."""
        mock_run.return_value = MagicMock(returncode=0, stderr="")

        output_path = temp_dir / "output.mp4"
        result = enhancer.reduce_noise(sample_video, output_path, noise_reduction_db=15.0)

        assert result == output_path
        mock_run.assert_called_once()

        # Check afftdn filter is used
        cmd_str = " ".join(mock_run.call_args[0][0])
        assert "afftdn" in cmd_str
        assert "nr=15.0" in cmd_str

    @patch("subprocess.run")
    def test_reduce_noise_default_intensity(self, mock_run, enhancer, sample_video, temp_dir):
        """Test noise reduction with default intensity."""
        mock_run.return_value = MagicMock(returncode=0, stderr="")

        output_path = temp_dir / "output.mp4"
        enhancer.reduce_noise(sample_video, output_path)

        cmd_str = " ".join(mock_run.call_args[0][0])
        # Default is 12.0 dB
        assert "nr=12.0" in cmd_str

    @patch("subprocess.run")
    def test_extract_and_enhance_both_filters(self, mock_run, enhancer, sample_video, temp_dir):
        """Test extract with both normalization and noise reduction."""
        mock_run.return_value = MagicMock(returncode=0, stderr="")

        output_path = temp_dir / "output.wav"
        result = enhancer.extract_and_enhance(
            sample_video,
            output_path,
            normalize=True,
            noise_reduction=True,
        )

        assert result == output_path
        cmd_str = " ".join(mock_run.call_args[0][0])
        # Both filters should be in the chain
        assert "afftdn" in cmd_str
        assert "loudnorm" in cmd_str

    @patch("subprocess.run")
    def test_extract_and_enhance_no_filters(self, mock_run, enhancer, sample_video, temp_dir):
        """Test extract without any enhancement."""
        mock_ffmpeg = MagicMock(spec=FFmpegWrapper)
        mock_ffmpeg.extract_audio.return_value = temp_dir / "output.wav"
        enhancer.ffmpeg = mock_ffmpeg

        output_path = temp_dir / "output.wav"
        result = enhancer.extract_and_enhance(
            sample_video,
            output_path,
            normalize=False,
            noise_reduction=False,
        )

        # Should call extract_audio directly, not subprocess
        mock_ffmpeg.extract_audio.assert_called_once_with(sample_video, output_path)
        mock_run.assert_not_called()
        assert result == output_path

    @patch("subprocess.run")
    def test_extract_and_enhance_only_normalize(self, mock_run, enhancer, sample_video, temp_dir):
        """Test extract with only normalization."""
        mock_run.return_value = MagicMock(returncode=0, stderr="")

        output_path = temp_dir / "output.wav"
        enhancer.extract_and_enhance(
            sample_video,
            output_path,
            normalize=True,
            noise_reduction=False,
        )

        cmd_str = " ".join(mock_run.call_args[0][0])
        assert "loudnorm" in cmd_str
        assert "afftdn" not in cmd_str

    @patch("subprocess.run")
    def test_extract_and_enhance_failure(self, mock_run, enhancer, sample_video, temp_dir):
        """Test extract_and_enhance failure."""
        mock_run.side_effect = subprocess.CalledProcessError(
            returncode=1,
            cmd=["ffmpeg"],
            stderr="Processing failed",
        )

        output_path = temp_dir / "output.wav"
        with pytest.raises(subprocess.CalledProcessError):
            enhancer.extract_and_enhance(sample_video, output_path, normalize=True)


class TestAudioAnalyzer:
    """AudioAnalyzer tests."""

    @pytest.fixture
    def temp_dir(self, tmp_path):
        """Temporary directory."""
        return tmp_path

    @pytest.fixture
    def analyzer(self):
        """AudioAnalyzer instance."""
        return AudioAnalyzer()

    @pytest.fixture
    def sample_audio(self, temp_dir):
        """Sample audio file."""
        audio_path = temp_dir / "sample.wav"
        audio_path.write_text("fake audio")
        return audio_path

    def test_initialization(self):
        """Test AudioAnalyzer initialization."""
        analyzer = AudioAnalyzer()
        assert analyzer is not None

    @patch("subprocess.run")
    def test_detect_silence_success(self, mock_run, analyzer, sample_audio):
        """Test successful silence detection."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stderr="""
            [silencedetect @ 0x7f8b0c0] silence_start: 1.5
            [silencedetect @ 0x7f8b0c0] silence_end: 2.5
            [silencedetect @ 0x7f8b0c0] silence_start: 5.0
            [silencedetect @ 0x7f8b0c0] silence_end: 6.0
            """,
        )

        silences = analyzer.detect_silence(sample_audio)

        assert len(silences) == 2
        assert silences[0] == (1.5, 2.5)
        assert silences[1] == (5.0, 6.0)

    @patch("subprocess.run")
    def test_detect_silence_no_silence(self, mock_run, analyzer, sample_audio):
        """Test silence detection with no silence found."""
        mock_run.return_value = MagicMock(returncode=0, stderr="")

        silences = analyzer.detect_silence(sample_audio)

        assert silences == []

    @patch("subprocess.run")
    def test_detect_silence_custom_threshold(self, mock_run, analyzer, sample_audio):
        """Test silence detection with custom threshold."""
        mock_run.return_value = MagicMock(returncode=0, stderr="")

        analyzer.detect_silence(sample_audio, silence_threshold=-40.0, min_silence_duration=1.0)

        cmd = mock_run.call_args[0][0]
        cmd_str = " ".join(cmd)
        assert "silencedetect=noise=-40.0dB:d=1.0" in cmd_str

    @patch("subprocess.run")
    def test_detect_silence_unmatched_end(self, mock_run, analyzer, sample_audio):
        """Test silence detection with unmatched silence_end."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stderr="""
            [silencedetect @ 0x7f8b0c0] silence_start: 1.5
            No matching end
            """,
        )

        silences = analyzer.detect_silence(sample_audio)

        # Unmatched silence_start should not be included
        assert silences == []

    @patch("subprocess.run")
    def test_get_audio_info_success(self, mock_run, analyzer, sample_audio):
        """Test successful audio info retrieval."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="""
            {
                "streams": [
                    {
                        "codec_type": "audio",
                        "codec_name": "aac",
                        "sample_rate": "48000",
                        "channels": 2,
                        "duration": "120.5",
                        "bit_rate": "128000"
                    }
                ]
            }
            """,
        )

        info = analyzer.get_audio_info(sample_audio)

        assert info["codec"] == "aac"
        assert info["sample_rate"] == 48000
        assert info["channels"] == 2
        assert info["duration"] == 120.5
        assert info["bit_rate"] == 128000

    @patch("subprocess.run")
    def test_get_audio_info_no_audio_stream(self, mock_run, analyzer, sample_audio):
        """Test audio info with no audio stream."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="""
            {
                "streams": [
                    {
                        "codec_type": "video",
                        "codec_name": "h264"
                    }
                ]
            }
            """,
        )

        info = analyzer.get_audio_info(sample_audio)

        assert info == {}

    @patch("subprocess.run")
    def test_get_audio_info_empty_streams(self, mock_run, analyzer, sample_audio):
        """Test audio info with empty streams."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='{"streams": []}',
        )

        info = analyzer.get_audio_info(sample_audio)

        assert info == {}

    @patch("subprocess.run")
    def test_get_audio_info_missing_fields(self, mock_run, analyzer, sample_audio):
        """Test audio info with missing optional fields."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="""
            {
                "streams": [
                    {
                        "codec_type": "audio",
                        "codec_name": "mp3"
                    }
                ]
            }
            """,
        )

        info = analyzer.get_audio_info(sample_audio)

        assert info["codec"] == "mp3"
        assert info["sample_rate"] == 0
        assert info["duration"] == 0.0
        assert info["bit_rate"] == 0
