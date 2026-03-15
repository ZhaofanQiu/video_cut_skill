"""File upload utilities for Aliyun DashScope."""

import os
import time
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

from video_cut_skill.exceptions import VideoCutSkillError


class FileUploadError(VideoCutSkillError):
    """Raised when file upload fails."""

    pass


class AliyunFileUploader:
    """Upload files to Aliyun DashScope temporary storage.
    
    Note: DashScope Files.upload returns file_id which is primarily for
    other DashScope services (like multimodal conversations), not for
    Paraformer transcription API. Paraformer requires publicly accessible URLs.
    
    For transcription, users should either:
    1. Provide a public URL directly
    2. Upload files to OSS/S3 and provide that URL
    """

    def __init__(self, api_key: Optional[str] = None):
        """Initialize file uploader.
        
        Args:
            api_key: DashScope API key. If not provided, reads from
                    DASHSCOPE_API_KEY environment variable.
        """
        self.api_key = api_key or os.getenv("DASHSCOPE_API_KEY")
        if not self.api_key:
            raise ValueError(
                "阿里云API Key未配置。请设置环境变量 DASHSCOPE_API_KEY "
                "或在初始化时传入api_key参数。"
            )

        try:
            import dashscope
            self._dashscope = dashscope
            self._dashscope.api_key = self.api_key
        except ImportError:
            raise ImportError(
                "使用阿里云功能需要安装dashscope：pip install dashscope"
            )

    def upload(self, file_path: str) -> str:
        """Upload a file to DashScope temporary storage.
        
        Note: This uploads to DashScope Files service which returns a file_id.
        The file_id can be used with certain DashScope APIs but NOT with
        Paraformer transcription API. For transcription, you need a public URL.
        
        Args:
            file_path: Path to the file to upload
            
        Returns:
            file_id for use with compatible DashScope APIs
            
        Raises:
            FileUploadError: If upload fails
        """
        path = Path(file_path)
        if not path.exists():
            raise FileUploadError(f"文件不存在：{file_path}")

        # Check if it's already a URL
        if self._is_url(file_path):
            return file_path

        try:
            # Use DashScope Files.upload API
            response = self._dashscope.Files.upload(
                file_path=str(path.absolute()),
                purpose="transcription",
            )
            
            if response.status_code != 200:
                raise FileUploadError(
                    f"上传失败：状态码 {response.status_code}"
                )
            
            # Extract file_id from response
            # Response format: {'uploaded_files': [{'name': '...', 'file_id': '...'}]}
            output = response.output
            
            if isinstance(output, dict):
                uploaded_files = output.get('uploaded_files', [])
                if uploaded_files:
                    file_id = uploaded_files[0].get('file_id')
                    if file_id:
                        return file_id
            
            raise FileUploadError(
                f"上传成功但无法获取文件ID。响应：{output}"
            )

        except FileUploadError:
            raise
        except Exception as e:
            raise FileUploadError(f"文件上传过程中发生错误：{e}") from e

    def _is_url(self, path: str) -> bool:
        """Check if path is already a URL."""
        try:
            result = urlparse(path)
            return result.scheme in ("http", "https")
        except Exception:
            return False


def upload_file_for_transcription(
    file_path: str,
    api_key: Optional[str] = None
) -> str:
    """Convenience function to upload a file.
    
    Note: For Paraformer transcription API, you need a public URL.
    This function uploads to DashScope Files and returns file_id which
    can only be used with compatible APIs.
    
    Args:
        file_path: Path to the audio/video file
        api_key: Optional API key
        
    Returns:
        file_id or URL
    """
    uploader = AliyunFileUploader(api_key)
    return uploader.upload(file_path)
