#!/usr/bin/env python3
"""
Whisper Model Pre-download Script

This script allows users to pre-download Whisper models to avoid waiting during runtime.

Usage:
    python download_models.py [model_name]
    
    model_name: tiny, base, small, medium, large, turbo, or all (default: all)

Examples:
    python download_models.py tiny      # Download only tiny model
    python download_models.py all       # Download all models
    
Models will be saved to: ~/.cache/whisper/ (or $XDG_CACHE_HOME/whisper/)
"""

import os
import sys
import whisper
import argparse
from pathlib import Path

# Model information
MODELS = {
    "tiny": {
        "size": "~39 MB",
        "description": "Fastest, lowest accuracy. Good for testing.",
        "url": "https://openaipublic.azureedge.net/main/whisper/models/65147644a518d12f04e32d6f3b26facc3f8dd46e5390956a9424a650c0ce22b9/tiny.pt",
    },
    "base": {
        "size": "~74 MB", 
        "description": "Fast, moderate accuracy. Good for general use.",
        "url": "https://openaipublic.azureedge.net/main/whisper/models/ed3a0b6b1c0edf879ad9b11b1ff5dd618872ca85da7800c4836901e25c6ab6f4/base.pt",
    },
    "small": {
        "size": "~244 MB",
        "description": "Balanced speed and accuracy.",
        "url": "https://openaipublic.azureedge.net/main/whisper/models/9ecf779972d90ba49c06d968637d720dd632c55bbf19d441fb42bf17a411e794/small.pt",
    },
    "medium": {
        "size": "~769 MB",
        "description": "Slower, high accuracy.",
        "url": "https://openaipublic.azureedge.net/main/whisper/models/345ae4da62f9b3d59415adc60127b97c714f32e89e936602e85993674d08dcb1/medium.pt",
    },
    "large": {
        "size": "~1550 MB",
        "description": "Slowest, highest accuracy (multilingual).",
        "url": "https://openaipublic.azureedge.net/main/whisper/models/e4b87e7e0bf463eb8e6956e646f1e277e901512310def2c24bf0e11bd3e28e9f/large.pt",
    },
    "turbo": {
        "size": "~809 MB",
        "description": "Fast transcription with large-v3 accuracy.",
        "url": "https://openaipublic.azureedge.net/main/whisper/models/e58f5b52382a8cbe8bf401df4f7bf50c65b97a5bcae07987d05ae192c1c1af4c/turbo.pt",
    },
}

def get_cache_dir():
    """Get Whisper cache directory."""
    cache_dir = os.environ.get("XDG_CACHE_HOME", os.path.expanduser("~/.cache"))
    return Path(cache_dir) / "whisper"

def download_model(model_name: str) -> bool:
    """Download a specific Whisper model."""
    if model_name not in MODELS:
        print(f"❌ Unknown model: {model_name}")
        print(f"Available models: {', '.join(MODELS.keys())}")
        return False
    
    info = MODELS[model_name]
    cache_dir = get_cache_dir()
    model_path = cache_dir / f"{model_name}.pt"
    
    print(f"\n📥 Downloading model: {model_name}")
    print(f"   Size: {info['size']}")
    print(f"   Description: {info['description']}")
    print(f"   Cache location: {model_path}")
    
    if model_path.exists():
        size_mb = model_path.stat().st_size / (1024 * 1024)
        print(f"   ⚠️  Model already exists ({size_mb:.1f} MB)")
        return True
    
    try:
        # Use whisper's load_model to trigger download
        print(f"   Downloading... (this may take a while)")
        model = whisper.load_model(model_name, download_root=str(cache_dir))
        print(f"   ✅ Download complete!")
        return True
    except Exception as e:
        print(f"   ❌ Download failed: {e}")
        return False

def list_downloaded_models():
    """List all downloaded models."""
    cache_dir = get_cache_dir()
    
    print(f"\n📂 Cache directory: {cache_dir}")
    print("\nDownloaded models:")
    
    found = False
    for model_name in MODELS.keys():
        model_path = cache_dir / f"{model_name}.pt"
        if model_path.exists():
            size_mb = model_path.stat().st_size / (1024 * 1024)
            print(f"   ✅ {model_name:10} ({size_mb:.1f} MB)")
            found = True
        else:
            print(f"   ❌ {model_name:10} (not downloaded)")
    
    if not found:
        print("   No models downloaded yet.")
    
    return found

def manual_download_instructions():
    """Print manual download instructions."""
    print("\n" + "="*70)
    print("MANUAL DOWNLOAD INSTRUCTIONS")
    print("="*70)
    print("""
If automatic download fails, you can manually download models:

1. Create cache directory:
   mkdir -p ~/.cache/whisper

2. Download model files using wget or curl:
""")
    
    for name, info in MODELS.items():
        print(f"   # {name} - {info['size']}")
        print(f"   wget -O ~/.cache/whisper/{name}.pt \\")
        print(f"       \"{info['url']}\"")
        print()
    
    print("3. Verify downloads:")
    print("   ls -lh ~/.cache/whisper/")
    print("\n" + "="*70)

def main():
    parser = argparse.ArgumentParser(
        description="Pre-download Whisper models for video_cut_skill"
    )
    parser.add_argument(
        "model",
        nargs="?",
        default="all",
        choices=list(MODELS.keys()) + ["all"],
        help="Model to download (default: all)"
    )
    parser.add_argument(
        "--list", "-l",
        action="store_true",
        help="List downloaded models"
    )
    parser.add_argument(
        "--manual",
        action="store_true",
        help="Show manual download instructions"
    )
    
    args = parser.parse_args()
    
    if args.list:
        list_downloaded_models()
        return
    
    if args.manual:
        manual_download_instructions()
        return
    
    # Show current status
    print("="*70)
    print("Whisper Model Downloader")
    print("="*70)
    print(f"\nCache directory: {get_cache_dir()}")
    
    # Download requested model(s)
    if args.model == "all":
        print("\n📦 Downloading all models...")
        success_count = 0
        for model_name in MODELS.keys():
            if download_model(model_name):
                success_count += 1
        
        print(f"\n{'='*70}")
        print(f"Downloaded {success_count}/{len(MODELS)} models")
        print(f"{'='*70}")
    else:
        download_model(args.model)
    
    # Show final status
    print("\nCurrent status:")
    list_downloaded_models()

if __name__ == "__main__":
    main()
