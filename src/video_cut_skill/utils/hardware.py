"""Hardware detection utilities - 硬件检测工具."""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class HardwareInfo:
    """硬件信息检测类."""

    _cuda_available: Optional[bool] = None
    _cuda_device_count: Optional[int] = None
    _cuda_device_name: Optional[str] = None

    @classmethod
    def check_cuda(cls) -> bool:
        """检查CUDA是否可用.

        Returns:
            bool: CUDA是否可用
        """
        if cls._cuda_available is not None:
            return cls._cuda_available

        try:
            import torch

            cls._cuda_available = torch.cuda.is_available()
            if cls._cuda_available:
                cls._cuda_device_count = torch.cuda.device_count()
                cls._cuda_device_name = torch.cuda.get_device_name(0)
                logger.info(f"CUDA available: {cls._cuda_device_count} device(s), " f"using {cls._cuda_device_name}")
            else:
                logger.info("CUDA not available")
        except ImportError:
            logger.debug("PyTorch not installed, CUDA unavailable")
            cls._cuda_available = False
        except Exception as e:
            logger.warning(f"Error checking CUDA: {e}")
            cls._cuda_available = False

        return cls._cuda_available

    @classmethod
    def get_optimal_device(cls, preferred: str = "auto") -> str:
        """获取最优计算设备.

        Args:
            preferred: 首选设备 ("auto", "cuda", "cpu")

        Returns:
            str: 实际使用的设备 ("cuda" 或 "cpu")
        """
        if preferred == "cpu":
            logger.info("Using CPU (user requested)")
            return "cpu"

        if preferred in ("auto", "cuda"):
            if cls.check_cuda():
                logger.info("Using CUDA for GPU acceleration")
                return "cuda"
            else:
                if preferred == "cuda":
                    logger.warning("CUDA requested but not available, falling back to CPU")
                else:
                    logger.info("CUDA not available, using CPU")

        return "cpu"

    @classmethod
    def get_device_info(cls) -> dict:
        """获取设备信息.

        Returns:
            dict: 设备信息字典
        """
        cuda_available = cls.check_cuda()

        info = {
            "cuda_available": cuda_available,
            "device": "cuda" if cuda_available else "cpu",
        }

        if cuda_available:
            info["cuda_device_count"] = cls._cuda_device_count
            info["cuda_device_name"] = cls._cuda_device_name

        return info


def get_optimal_device(preferred: str = "auto") -> str:
    """获取最优计算设备的便捷函数.

    Args:
        preferred: 首选设备 ("auto", "cuda", "cpu")

    Returns:
        str: 实际使用的设备
    """
    return HardwareInfo.get_optimal_device(preferred)
