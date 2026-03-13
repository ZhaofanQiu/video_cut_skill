#!/usr/bin/env python3
"""Feishu File Downloader - 飞书文件下载工具.

用于下载用户通过飞书发送的文件.
"""

import os
import json
import requests
from pathlib import Path
from typing import Optional

# 飞书 API 配置
# 这些应该从环境变量或配置文件读取
FEISHU_APP_ID = os.environ.get("FEISHU_APP_ID", "")
FEISHU_APP_SECRET = os.environ.get("FEISHU_APP_SECRET", "")


def get_tenant_access_token() -> Optional[str]:
    """获取飞书 tenant_access_token.
    
    Returns:
        访问令牌或 None
    """
    if not FEISHU_APP_ID or not FEISHU_APP_SECRET:
        print("❌ 错误: 未配置 FEISHU_APP_ID 或 FEISHU_APP_SECRET")
        return None
    
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    headers = {"Content-Type": "application/json"}
    data = {
        "app_id": FEISHU_APP_ID,
        "app_secret": FEISHU_APP_SECRET,
    }
    
    try:
        response = requests.post(url, headers=headers, json=data)
        result = response.json()
        
        if result.get("code") == 0:
            return result.get("tenant_access_token")
        else:
            print(f"❌ 获取 token 失败: {result}")
            return None
    except Exception as e:
        print(f"❌ 请求失败: {e}")
        return None


def download_file_from_key(
    file_key: str,
    output_path: str,
    token: Optional[str] = None,
) -> bool:
    """使用文件 key 下载文件.
    
    Args:
        file_key: 飞书文件 key
        output_path: 保存路径
        token: 访问令牌 (可选)
        
    Returns:
        是否成功
    """
    if not token:
        token = get_tenant_access_token()
        if not token:
            return False
    
    # 获取文件下载 URL
    url = f"https://open.feishu.cn/open-apis/drive/v1/medias/batch_get_tmp_download_url"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    
    # 这里 file_key 可能是 file 或 media 类型
    # 尝试 media 类型
    data = {
        "file_tokens": [file_key],
    }
    
    try:
        response = requests.post(url, headers=headers, json=data)
        result = response.json()
        
        print(f"API Response: {json.dumps(result, indent=2, ensure_ascii=False)}")
        
        if result.get("code") == 0:
            download_urls = result.get("data", {}).get("tmp_download_urls", [])
            if download_urls:
                download_url = download_urls[0].get("tmp_download_url")
                if download_url:
                    # 下载文件
                    print(f"⬇️  下载文件: {download_url[:50]}...")
                    file_response = requests.get(download_url, stream=True)
                    
                    with open(output_path, 'wb') as f:
                        for chunk in file_response.iter_content(chunk_size=8192):
                            f.write(chunk)
                    
                    print(f"✅ 文件已保存: {output_path}")
                    return True
            
            print("❌ 未获取到下载链接")
            return False
        else:
            print(f"❌ API 错误: {result.get('msg')}")
            return False
            
    except Exception as e:
        print(f"❌ 下载失败: {e}")
        return False


def parse_feishu_file_url(url: str) -> Optional[str]:
    """从飞书文件 URL 中提取 file_key.
    
    Args:
        url: 飞书文件 URL
        
    Returns:
        file_key 或 None
    """
    # 尝试从各种飞书 URL 格式中提取 file_key
    import re
    
    patterns = [
        r'file_key=([^&]+)',
        r'/file/([^/?]+)',
        r'/media/([^/?]+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    return None


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python feishu_file_downloader.py <file_key_or_url> [output_path]")
        print("\n示例:")
        print("  python feishu_file_downloader.py file_v3_xxx")
        print("  python feishu_file_downloader.py 'https://...file_key=xxx' /tmp/video.mp4")
        sys.exit(1)
    
    input_str = sys.argv[1]
    output = sys.argv[2] if len(sys.argv) > 2 else "/tmp/downloaded_file"
    
    # 判断输入是 file_key 还是完整 URL
    if input_str.startswith("http"):
        file_key = parse_feishu_file_url(input_str)
        if not file_key:
            print("❌ 无法从 URL 提取 file_key")
            sys.exit(1)
    else:
        file_key = input_str
    
    print(f"📎 File Key: {file_key}")
    print(f"💾 Output: {output}")
    
    success = download_file_from_key(file_key, output)
    sys.exit(0 if success else 1)
