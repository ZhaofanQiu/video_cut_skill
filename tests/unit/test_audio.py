"""Tests for audio module."""

import subprocess
from unittest.mock import MagicMock, patch

import pytest

from video_cut_skill.audio import AudioAnalyzer, AudioEnhancer


class TestAudioEnhancer:
    """AudioEnhancer tests."""

    @pytest.fixture
    def enhancer(self):
        """Create enhancer with mocked ffmpeg."""
        mock_ffmpeg = MagicMock()
        return AudioEnhancer(ffmpeg=mock_ffmpeg)

    @pytest.fixture
    def temp_audio(self, tmp_path):
        """Create temporary audio file."""
        audio_file = tmp_path / "test_audio.mp4"
        audio_file.write_text("fake audio")
        return audio_file

    def test_initialization_default(self):
        """Test default initialization creates FFmpeg wrapper."""
        with patch("video_cut_skill.audio.FFmpegWrapper") as mock_ffmpeg_class:
            mock_ffmpeg = MagicMock()
            mock_ffmpeg_class.return_value = mock_ffmpeg
            enhancer = AudioEnhancer()
            assert enhancer.ffmpeg is not None

    def test_initialization_with_custom_ffmpeg(self):
        """Test initialization with custom ffmpeg."""
        mock_ffmpeg = MagicMock()
        enhancer = AudioEnhancer(ffmpeg=mock_ffmpeg)
        assert enhancer.ffmpeg == mock_ffmpeg

    @patch("subprocess.run")
    def test_normalize_lufs_success(self, mock_run, enhancer, temp_audio, tmp_path):
        """Test successful LUFS normalization."""
        mock_run.return_value = MagicMock(returncode=0, stderr="")
        output_path = tmp_path / "output.mp4"

        result = enhancer.normalize_lufs(temp_audio, output_path, target_lufs=-16.0)

        assert result == output_path
        mock_run.assert_called_once()
        # Check that ffmpeg command was called
        call_args = mock_run.call_args
        assert call_args[0][0][0] == "ffmpeg"
        assert "-i" in call_args[0][0]
        assert "loudnorm" in " ".join(call_args[0][0])

    @patch("subprocess.run")
    def test_normalize_lufs_default_params(self, mock_run, enhancer, temp_audio, tmp_path):
        """Test normalization with default parameters."""
        mock_run.return_value = MagicMock(returncode=0, stderr="")
        output_path = tmp_path / "output.mp4"

        enhancer.normalize_lufs(temp_audio, output_path)

        call_args = mock_run.call_args
        cmd_str = " ".join(call_args[0][0])
        assert "I=-14" in cmd_str  # Default target LUFS
        assert "TP=-1" in cmd_str  # Default true peak

    @patch("subprocess.run")
    def test_normalize_lufs_failure(self, mock_run, enhancer, temp_audio, tmp_path):
        """Test normalization failure handling."""
        mock_run.side_effect = subprocess.CalledProcessError(1, "ffmpeg", stderr="Error: invalid input")
        output_path = tmp_path / "output.mp4"

        with pytest.raises(subprocess.CalledProcessError):
            enhancer.normalize_lufs(temp_audio, output_path)

    @patch("subprocess.run")
    def test_reduce_noise_success(self, mock_run, enhancer, temp_audio, tmp_path):
        """Test successful noise reduction."""
        mock_run.return_value = MagicMock(returncode=0, stderr="")
        output_path = tmp_path / "output.mp4"

        result = enhancer.reduce_noise(temp_audio, output_path, noise_reduction_db=15.0)

        assert result == output_path
        mock_run.assert_called_once()
        call_args = mock_run.call_args
        assert "afftdn" in " ".join(call_args[0][0])
        assert "nr=15" in " ".join(call_args[0][0])

    @patch("subprocess.run")
    def test_reduce_noise_default_params(self, mock_run, enhancer, temp_audio, tmp_path):
        """Test noise reduction with default parameters."""
        mock_run.return_value = MagicMock(returncode=0, stderr="")
        output_path = tmp_path / "output.mp4"

        enhancer.reduce_noise(temp_audio, output_path)

        call_args = mock_run.call_args
        cmd_str = " ".join(call_args[0][0])
        assert "nr=12" in cmd_str  # Default 12 dB

    @patch("subprocess.run")
    def test_reduce_noise_failure(self, mock_run, enhancer, temp_audio, tmp_path):
        """Test noise reduction failure handling."""
        mock_run.side_effect = subprocess.CalledProcessError(1, "ffmpeg", stderr="Error: processing failed")
        output_path = tmp_path / "output.mp4"

        with pytest.raises(subprocess.CalledProcessError):
            enhancer.reduce_noise(temp_audio, output_path)

    @patch("subprocess.run")
    def test_extract_and_enhance_normalize_only(self, mock_run, enhancer, temp_audio, tmp_path):
        """Test extract with only normalization."""
        mock_run.return_value = MagicMock(returncode=0, stderr="")
        output_path = tmp_path / "output.wav"

        result = enhancer.extract_and_enhance(
            temp_audio,
            output_path,
            normalize=True,
            noise_reduction=False,
        )

        assert result == output_path
        mock_run.assert_called_once()
        call_args = mock_run.call_args
        cmd_str = " ".join(call_args[0][0])
        assert "loudnorm" in cmd_str
        assert "afftdn" not in cmd_str  # No noise reduction

    @patch("subprocess.run")
    def test_extract_and_enhance_noise_only(self, mock_run, enhancer, temp_audio, tmp_path):
        """Test extract with only noise reduction."""
        mock_run.return_value = MagicMock(returncode=0, stderr="")
        output_path = tmp_path / "output.wav"

        result = enhancer.extract_and_enhance(
            temp_audio,
            output_path,
            normalize=False,
            noise_reduction=True,
        )

        assert result == output_path
        mock_run.assert_called_once()
        call_args = mock_run.call_args
        cmd_str = " ".join(call_args[0][0])
        assert "afftdn" in cmd_str
        assert "loudnorm" not in cmd_str  # No normalization

    @patch("subprocess.run")
    def test_extract_and_enhance_both(self, mock_run, enhancer, temp_audio, tmp_path):
        """Test extract with both enhancements."""
        mock_run.return_value = MagicMock(returncode=0, stderr="")
        output_path = tmp_path / "output.wav"

        result = enhancer.extract_and_enhance(
            temp_audio,
            output_path,
            normalize=True,
            noise_reduction=True,
        )

        assert result == output_path
        mock_run.assert_called_once()
        call_args = mock_run.call_args
        cmd_str = " ".join(call_args[0][0])
        assert "afftdn" in cmd_str
        assert "loudnorm" in cmd_str

    def test_extract_and_enhance_no_filters(self, enhancer, temp_audio, tmp_path):
        """Test extract without any enhancement."""
        output_path = tmp_path / "output.wav"
        enhancer.ffmpeg.extract_audio.return_value = output_path

        result = enhancer.extract_and_enhance(
            temp_audio,
            output_path,
            normalize=False,
            noise_reduction=False,
        )

        # Should call extract_audio directly, not subprocess
        enhancer.ffmpeg.extract_audio.assert_called_once_with(temp_audio, output_path)
        assert result == output_path

    @patch("subprocess.run")
    def test_extract_and_enhance_failure(self, mock_run, enhancer, temp_audio, tmp_path):
        """Test extract and enhance failure handling."""
        mock_run.side_effect = subprocess.CalledProcessError(1, "ffmpeg", stderr="Error: extraction failed")
        output_path = tmp_path / "output.wav"

        with pytest.raises(subprocess.CalledProcessError):
            enhancer.extract_and_enhance(temp_audio, output_path, normalize=True)


class TestAudioAnalyzer:
    """AudioAnalyzer tests."""

    @pytest.fixture
    def analyzer(self):
        """Create analyzer instance."""
        return AudioAnalyzer()

    @pytest.fixture
    def temp_audio(self, tmp_path):
        """Create temporary audio file."""
        audio_file = tmp_path / "test_audio.wav"
        audio_file.write_text("fake audio")
        return audio_file

    @patch("subprocess.run")
    def test_detect_silence_success(self, mock_run, analyzer, temp_audio):
        """Test successful silence detection."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stderr="""
            [silencedetect @ 0x...] silence_start: 1.5
            [silencedetect @ 0x...] silence_end: 2.5
            [silencedetect @ 0x...] silence_start: 5.0
            [silencedetect @ 0x...] silence_end: 6.0
            """,
        )

        silences = analyzer.detect_silence(temp_audio)

        assert len(silences) == 2
        assert silences[0] == (1.5, 2.5)
        assert silences[1] == (5.0, 6.0)

    @patch("subprocess.run")
    def test_detect_silence_default_params(self, mock_run, analyzer, temp_audio):
        """Test silence detection with default parameters."""
        mock_run.return_value = MagicMock(returncode=0, stderr="")

        analyzer.detect_silence(temp_audio)

        call_args = mock_run.call_args
        cmd_str = " ".join(call_args[0][0])
        assert "silencedetect" in cmd_str
        assert "noise=-50" in cmd_str  # Default threshold (may be -50 or -50.0)
        assert "d=0.5" in cmd_str  # Default duration

    @patch("subprocess.run")
    def test_detect_silence_custom_params(self, mock_run, analyzer, temp_audio):
        """Test silence detection with custom parameters."""
        mock_run.return_value = MagicMock(returncode=0, stderr="")

        analyzer.detect_silence(
            temp_audio,
            silence_threshold=-40.0,
            min_silence_duration=1.0,
        )

        call_args = mock_run.call_args
        cmd_str = " ".join(call_args[0][0])
        assert "noise=-40" in cmd_str
        assert "d=1.0" in cmd_str

    @patch("subprocess.run")
    def test_detect_silence_no_silences(self, mock_run, analyzer, temp_audio):
        """Test silence detection with no silences found."""
        mock_run.return_value = MagicMock(returncode=0, stderr="")

        silences = analyzer.detect_silence(temp_audio)

        assert silences == []

    @patch("subprocess.run")
    def test_get_audio_info_success(self, mock_run, analyzer, temp_audio):
        """Test successful audio info retrieval."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='{"streams": [{"codec_type": "audio", "codec_name": "aac", "sample_rate": "48000", "channels": 2}]}',
        )

        info = analyzer.get_audio_info(temp_audio)

        assert isinstance(info, dict)
        assert "codec" in info
        assert "sample_rate" in info
        assert "channels" in info

    @patch("subprocess.run")
    def test_get_audio_info_no_audio_stream(self, mock_run, analyzer, temp_audio):
        """Test audio info when no audio stream exists."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='{"streams": [{"codec_type": "video"}]}',
        )

        info = analyzer.get_audio_info(temp_audio)

        assert info == {}

    @patch("subprocess.run")
    def test_get_audio_info_with_video_stream(self, mock_run, analyzer, temp_audio):
        """Test audio info filters out video streams."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='{"streams": [{"codec_type": "video"}, {"codec_type": "audio", "codec_name": "aac"}]}',
        )

        info = analyzer.get_audio_info(temp_audio)

        assert "codec" in info
