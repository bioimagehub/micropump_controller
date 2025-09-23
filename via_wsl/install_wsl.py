#!/usr/bin/env python3
"""
WSL Installation Script
Handles automatic installation of WSL itself.
Designed to be run with admin privileges via run_as_admin.bat
"""

import subprocess
import time
import sys
import argparse


def check_wsl_available() -> bool:
    """Check if WSL is installed and working."""
    try:
        result = subprocess.run([
            "wsl", "--status"
        ], capture_output=True, text=True, check=False, timeout=5)
        
        if result.returncode != 0:
            print("❌ WSL not available")
            return False
        
        print("✅ WSL is available")
        return True
        
    except subprocess.TimeoutExpired:
        print("❌ WSL status check timed out")
        return False
    except Exception as e:
        print(f"❌ WSL check failed: {e}")
        return False


def install_wsl() -> bool:
    """Install WSL using the wsl --install command."""
    try:
        print("🔒 Installing WSL...")
        
        # Install WSL
        install_cmd = ["wsl", "--install"]
        
        print(f"Running: {' '.join(install_cmd)}")
        result = subprocess.run(install_cmd, check=False, timeout=300)  # 5 minute timeout
        
        if result.returncode == 0:
            print("✅ WSL installation command completed")
            print("⚠️  WSL installation may require a system reboot to complete")
            print("🔄 Checking if WSL is now available...")
            
            # Give a moment for installation to register
            time.sleep(5)
            
            # Check if WSL is now available
            if check_wsl_available():
                print("✅ WSL is now available!")
                return True
            else:
                print("⚠️  WSL installation initiated but not yet available")
                print("💡 You may need to reboot your system for WSL to be fully activated")
                return False
        else:
            print(f"❌ WSL installation failed with exit code: {result.returncode}")
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ WSL installation timed out")
        return False
    except Exception as e:
        print(f"❌ Failed to install WSL: {e}")
        return False


def main():
    """Main WSL installation function."""
    parser = argparse.ArgumentParser(description='Install WSL with admin privileges')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be done without actually installing')
    
    args = parser.parse_args()
    
    print("🔧 WSL Installer")
    print("=" * 50)
    
    # Check if WSL is already available
    if check_wsl_available():
        print("✅ WSL is already installed and working!")
        return 0
    
    if args.dry_run:
        print("🔍 DRY RUN - Would install WSL using 'wsl --install'")
        return 0
    
    # Install WSL
    print("🎯 Installing WSL...")
    
    if install_wsl():
        print("\n🎉 SUCCESS! WSL installation completed!")
        if not check_wsl_available():
            print("⚠️  Note: You may need to reboot your system for WSL to be fully activated")
        return 0
    else:
        print("\n❌ FAILED! WSL installation failed.")
        return 1


if __name__ == "__main__":
    try:
        exit_code = main()
        print(f"\nExiting with code: {exit_code}")
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n🛑 Installation cancelled by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        sys.exit(1)