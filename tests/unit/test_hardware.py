"""Tests for hardware detection utilities."""

from unittest.mock import patch

from video_cut_skill.utils.hardware import HardwareInfo, get_optimal_device


class TestHardwareInfo:
    """HardwareInfo tests."""

    def setup_method(self):
        """Reset class state before each test."""
        HardwareInfo._cuda_available = None
        HardwareInfo._cuda_device_count = None
        HardwareInfo._cuda_device_name = None

    def test_check_cuda_not_available(self):
        """Test CUDA check when not available."""
        with patch("torch.cuda.is_available", return_value=False):
            result = HardwareInfo.check_cuda()
            assert result is False

    def test_check_cuda_available(self):
        """Test CUDA check when available."""
        with (
            patch("torch.cuda.is_available", return_value=True),
            patch("torch.cuda.device_count", return_value=2),
            patch("torch.cuda.get_device_name", return_value="NVIDIA GTX 1080"),
        ):
            result = HardwareInfo.check_cuda()
            assert result is True
            assert HardwareInfo._cuda_device_count == 2
            assert HardwareInfo._cuda_device_name == "NVIDIA GTX 1080"

    def test_check_cuda_import_error(self):
        """Test CUDA check when torch not installed."""
        with patch("builtins.__import__", side_effect=ImportError("No module named torch")):
            result = HardwareInfo.check_cuda()
            assert result is False

    def test_check_cuda_cached_result(self):
        """Test that CUDA check result is cached."""
        HardwareInfo._cuda_available = True

        with patch("torch.cuda.is_available") as mock_cuda:
            result = HardwareInfo.check_cuda()
            assert result is True
            # Should not call torch.cuda.is_available again
            mock_cuda.assert_not_called()

    def test_get_optimal_device_auto_with_cuda(self):
        """Test get_optimal_device with auto preference and CUDA available."""
        with patch.object(HardwareInfo, "check_cuda", return_value=True):
            result = HardwareInfo.get_optimal_device("auto")
            assert result == "cuda"

    def test_get_optimal_device_auto_without_cuda(self):
        """Test get_optimal_device with auto preference and no CUDA."""
        with patch.object(HardwareInfo, "check_cuda", return_value=False):
            result = HardwareInfo.get_optimal_device("auto")
            assert result == "cpu"

    def test_get_optimal_device_cpu_preferred(self):
        """Test get_optimal_device with CPU preference."""
        result = HardwareInfo.get_optimal_device("cpu")
        assert result == "cpu"

    def test_get_optimal_device_cuda_preferred_available(self):
        """Test get_optimal_device with CUDA preference when available."""
        with patch.object(HardwareInfo, "check_cuda", return_value=True):
            result = HardwareInfo.get_optimal_device("cuda")
            assert result == "cuda"

    def test_get_optimal_device_cuda_preferred_not_available(self):
        """Test get_optimal_device with CUDA preference when not available."""
        with patch.object(HardwareInfo, "check_cuda", return_value=False):
            result = HardwareInfo.get_optimal_device("cuda")
            # Should fall back to CPU
            assert result == "cpu"

    def test_get_device_info_no_cuda(self):
        """Test get_device_info when CUDA not available."""
        with patch.object(HardwareInfo, "check_cuda", return_value=False):
            info = HardwareInfo.get_device_info()

        assert info["cuda_available"] is False
        assert info["device"] == "cpu"
        assert "cuda_device_count" not in info
        assert "cuda_device_name" not in info

    def test_get_device_info_with_cuda(self):
        """Test get_device_info when CUDA available."""
        HardwareInfo._cuda_available = True
        HardwareInfo._cuda_device_count = 1
        HardwareInfo._cuda_device_name = "NVIDIA RTX 3080"

        with patch.object(HardwareInfo, "check_cuda", return_value=True):
            info = HardwareInfo.get_device_info()

        assert info["cuda_available"] is True
        assert info["device"] == "cuda"
        assert info["cuda_device_count"] == 1
        assert info["cuda_device_name"] == "NVIDIA RTX 3080"


class TestGetOptimalDeviceFunction:
    """get_optimal_device function tests."""

    def test_get_optimal_device_function_auto(self):
        """Test get_optimal_device function with auto preference."""
        with patch.object(HardwareInfo, "get_optimal_device", return_value="cuda") as mock_method:
            result = get_optimal_device("auto")
            assert result == "cuda"
            mock_method.assert_called_once_with("auto")

    def test_get_optimal_device_function_cpu(self):
        """Test get_optimal_device function with CPU preference."""
        with patch.object(HardwareInfo, "get_optimal_device", return_value="cpu") as mock_method:
            result = get_optimal_device("cpu")
            assert result == "cpu"
            mock_method.assert_called_once_with("cpu")

    def test_get_optimal_device_function_default(self):
        """Test get_optimal_device function with default parameter."""
        with patch.object(HardwareInfo, "get_optimal_device", return_value="cuda") as mock_method:
            result = get_optimal_device()
            assert result == "cuda"
            mock_method.assert_called_once_with("auto")


class TestHardwareInfoEdgeCases:
    """HardwareInfo edge case tests."""

    def setup_method(self):
        """Reset class state before each test."""
        HardwareInfo._cuda_available = None
        HardwareInfo._cuda_device_count = None
        HardwareInfo._cuda_device_name = None

    def test_check_cuda_exception(self):
        """Test CUDA check when exception occurs."""
        with patch("torch.cuda.is_available", side_effect=Exception("CUDA error")):
            result = HardwareInfo.check_cuda()
            assert result is False

    def test_multiple_devices(self):
        """Test with multiple CUDA devices."""
        with (
            patch("torch.cuda.is_available", return_value=True),
            patch("torch.cuda.device_count", return_value=4),
            patch("torch.cuda.get_device_name", return_value="NVIDIA A100"),
        ):
            HardwareInfo.check_cuda()
            assert HardwareInfo._cuda_device_count == 4

    def test_device_info_consistency(self):
        """Test that device info is consistent."""
        HardwareInfo._cuda_available = True
        HardwareInfo._cuda_device_count = 2
        HardwareInfo._cuda_device_name = "Test GPU"

        with patch.object(HardwareInfo, "check_cuda", return_value=True):
            info = HardwareInfo.get_device_info()

        # If CUDA is available, device should be cuda
        assert info["device"] == "cuda"
        assert info["cuda_device_count"] == 2
