#!/usr/bin/env python3
"""
WSL Distribution Installation Script
Handles automatic installation of WSL distributions with fallback logic.
Designed to be run with admin privileges via run_as_admin.bat
"""

import subprocess
import time
import sys
import argparse
from pathlib import Path


def check_wsl_distro_available(distro: str) -> bool:
    """Check if the specified WSL distribution is available."""
    try:
        result = subprocess.run([
            "wsl", "-l", "-q"
        ], capture_output=True, text=True, check=False, timeout=5)
        
        if result.returncode != 0:
            print("❌ Could not list WSL distributions")
            return False
        
        available_distros = [line.strip().replace('*', '') for line in result.stdout.strip().split('\n') if line.strip()]
        
        if distro not in available_distros:
            print(f"❌ WSL distribution '{distro}' not found")
            print(f"   Available: {available_distros}")
            return False
        
        print(f"✅ WSL distribution '{distro}' is available")
        return True
        
    except subprocess.TimeoutExpired:
        print("❌ WSL distribution check timed out")
        return False
    except Exception as e:
        print(f"❌ WSL distribution check failed: {e}")
        return False


def install_wsl_distribution(distro: str) -> bool:
    """Install a specific WSL distribution."""
    try:
        print(f"🔒 Installing WSL distribution '{distro}'...")
        
        # Install the distribution
        install_cmd = ["wsl", "--install", "-d", distro]
        
        print(f"Running: {' '.join(install_cmd)}")
        result = subprocess.run(install_cmd, check=False, timeout=600)  # 10 minute timeout
        
        if result.returncode == 0:
            print(f"✅ {distro} installation command completed")
            print("🔄 Checking if distribution is now available...")
            
            # Give time for distribution to install and register
            time.sleep(10)
            
            # Check if distro is now available
            if check_wsl_distro_available(distro):
                print(f"✅ WSL distribution '{distro}' is now available!")
                return True
            else:
                print(f"⚠️  Distribution installation may still be in progress")
                
                # Try a few more times with increasing delays
                for attempt in range(3):
                    print(f"🔄 Waiting for distribution to be ready (attempt {attempt + 1}/3)...")
                    time.sleep(15)
                    if check_wsl_distro_available(distro):
                        print(f"✅ WSL distribution '{distro}' is now ready!")
                        return True
                
                print(f"❌ Distribution '{distro}' installation did not complete in expected time")
                return False
        else:
            print(f"❌ Distribution '{distro}' installation failed with exit code: {result.returncode}")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"❌ Distribution '{distro}' installation timed out")
        return False
    except Exception as e:
        print(f"❌ Failed to install distribution '{distro}': {e}")
        return False


def save_successful_distro_to_env(distro: str) -> bool:
    """Save successfully installed WSL distribution to .env file."""
    try:
        # Find project root (.env should be one level up from via_wsl)
        project_root = Path(__file__).parent.parent
        env_file = project_root / ".env"
        
        print(f"📝 Saving successful installation to: {env_file}")
        
        # Read existing .env content
        env_lines = []
        wsl_distro_found = False
        
        if env_file.exists():
            with open(env_file, 'r') as f:
                env_lines = f.readlines()
            
            # Update existing WSL_DISTRO line or mark if found
            for i, line in enumerate(env_lines):
                if line.strip().startswith('WSL_DISTRO=') and not line.strip().startswith('#'):
                    env_lines[i] = f"WSL_DISTRO={distro}\n"
                    wsl_distro_found = True
                    break
        
        # Add WSL_DISTRO if not found
        if not wsl_distro_found:
            if env_lines and not env_lines[-1].endswith('\n'):
                env_lines.append('\n')
            env_lines.append(f"# WSL distribution successfully installed and verified\n")
            env_lines.append(f"WSL_DISTRO={distro}\n")
        
        # Write back to .env file
        with open(env_file, 'w') as f:
            f.writelines(env_lines)
        
        print(f"✅ Saved WSL distribution to .env: {distro}")
        return True
        
    except Exception as e:
        print(f"⚠️  Failed to save WSL distribution to .env: {e}")
        return False


def main():
    """Main installation function with fallback logic."""
    parser = argparse.ArgumentParser(description='Install WSL distribution with fallback')
    parser.add_argument('--distro', default='Debian', 
                       help='Primary WSL distribution to install (default: Debian)')
    parser.add_argument('--fallbacks', nargs='*', 
                       default=['Ubuntu-24.04', 'Ubuntu'],
                       help='Fallback distributions to try if primary fails')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be done without actually installing')
    
    args = parser.parse_args()
    
    print("🔧 WSL Distribution Installer")
    print("=" * 50)
    
    # Build list of distributions to try
    if args.distro not in args.fallbacks:
        distros_to_try = [args.distro] + args.fallbacks
    else:
        # Start from current distro in the fallback chain
        start_index = args.fallbacks.index(args.distro)
        distros_to_try = args.fallbacks[start_index:]
    
    print(f"📋 Will try distributions in order: {' → '.join(distros_to_try)}")
    
    if args.dry_run:
        print("🔍 DRY RUN - No actual installation will be performed")
        return 0
    
    successful_distro = None
    
    for distro in distros_to_try:
        print(f"\n🎯 Attempting to install: {distro}")
        
        # Check if already installed
        if check_wsl_distro_available(distro):
            print(f"✅ Distribution '{distro}' is already available!")
            successful_distro = distro
            break
        
        # Try to install
        if install_wsl_distribution(distro):
            successful_distro = distro
            break
        else:
            print(f"❌ Failed to install '{distro}', trying next fallback...")
            continue
    
    if successful_distro:
        print(f"\n🎉 SUCCESS! WSL distribution '{successful_distro}' is ready!")
        
        # Save to .env file
        if save_successful_distro_to_env(successful_distro):
            print("✅ Configuration saved to .env file")
        
        return 0  # Success
    else:
        print(f"\n❌ FAILED! Could not install any WSL distribution.")
        print(f"   Tried: {', '.join(distros_to_try)}")
        return 1  # Failure


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