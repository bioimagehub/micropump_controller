"""
Build standalone .exe for airgapped microscope PC.

Requires: pip install pyinstaller
Usage: python build_standalone.py
"""

import subprocess
import sys
from pathlib import Path


def build_exe() -> None:
    """Build standalone executable"""
    
    print("Building standalone executable for microscope PC...")
    print("This will create: dist/microscope_audio_test.exe")
    print()
    
    # Check if PyInstaller is available
    try:
        subprocess.run(
            ["pyinstaller", "--version"],
            capture_output=True,
            check=True
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("✗ PyInstaller not found")
        print("Install with: pip install pyinstaller")
        return
    
    # PyInstaller command
    cmd = [
        "pyinstaller",
        "--onefile",  # Single executable
        "--console",  # Keep console window
        "--name", "microscope_audio_test",
        "--add-data", "audio_protocol.py;.",  # Bundle audio_protocol.py
        "--clean",
        "microscope_audio_test.py"
    ]
    
    try:
        print("Running PyInstaller...")
        subprocess.run(cmd, check=True)
        
        exe_path = Path("dist/microscope_audio_test.exe")
        if exe_path.exists():
            print(f"\n✓ Build successful!")
            print(f"  Executable: {exe_path.absolute()}")
            print(f"  Size: {exe_path.stat().st_size / 1024 / 1024:.1f} MB")
            print()
            print("=" * 70)
            print("Transfer to microscope PC:")
            print("=" * 70)
            print("  1. Copy dist/microscope_audio_test.exe to USB stick")
            print("  2. Run on microscope PC (double-click)")
            print("  3. Follow on-screen instructions")
            print()
            print("Alternative (if Python installed on microscope PC):")
            print("  1. Copy both files to USB:")
            print("     - audio_protocol.py")
            print("     - microscope_audio_test.py")
            print("  2. Install dependencies: pip install -r requirements.txt")
            print("  3. Run: python microscope_audio_test.py")
        else:
            print("✗ Build completed but .exe not found")
            
    except subprocess.CalledProcessError as e:
        print(f"✗ Build failed: {e}")
        print("\nMake sure PyInstaller is installed: pip install pyinstaller")


if __name__ == "__main__":
    build_exe()
