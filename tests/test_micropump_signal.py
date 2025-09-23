#!/usr/bin/env python3
"""Simple micropump test script with three-tier fallback strategy."""

import argparse
import subprocess
import sys
import time
from pathlib import Path

# Import pump classes
sys.path.append(str(Path(__file__).parent.parent / "src"))
from pump_win import Pump_win
from pump_wsl import Pump_wsl

def check_wsl_fast():
    """Fast WSL check without triggering installation prompts."""
    try:
        # Use --status to check if WSL is installed
        result = subprocess.run(["wsl", "--status"], 
                              capture_output=True, text=True, check=False)
        if result.returncode != 0:
            return False, "WSL not installed"
        
        # List distributions
        list_result = subprocess.run(["wsl", "-l", "-q"], 
                                   capture_output=True, text=True, check=False)
        if list_result.returncode != 0:
            return False, "Could not list WSL distributions"
        
        distros = [line.strip() for line in list_result.stdout.strip().split('\n') if line.strip()]
        return True, distros
        
    except Exception as e:
        return False, f"WSL check error: {e}"

def try_windows_pump():
    """Try to initialize Windows pump."""
    print("🪟 Trying Windows COM port connection...")
    try:
        pump = Pump_win()
        if pump.initialize():
            print(f"✅ Windows pump initialized successfully")
            return pump
        else:
            print(f"❌ Windows pump failed: {pump.get_error_details()}")
            print(f"💡 {pump.get_suggested_fix()}")
            return None
    except Exception as e:
        print(f"❌ Windows pump error: {e}")
        return None

def try_wsl_pump(distro="Alpine"):
    """Try to initialize WSL pump."""
    print(f"🐧 Trying WSL connection ({distro})...")
    try:
        pump = Pump_wsl(distro=distro)
        if pump.initialize():
            print(f"✅ WSL pump initialized successfully")
            return pump
        else:
            print(f"❌ WSL pump failed: {pump.get_error_details()}")
            print(f"💡 {pump.get_suggested_fix()}")
            return None
    except Exception as e:
        print(f"❌ WSL pump error: {e}")
        return None

def test_and_exit(pump, args):
    """Test pump with specified parameters and exit."""
    print(f"\n🧪 Testing pump signal...")
    print(f"   Duration: {args.duration}s")
    print(f"   Frequency: {args.frequency}Hz") 
    print(f"   Voltage: {args.voltage}Vpp")
    print(f"   Waveform: {args.waveform}")
    
    try:
        if pump.test_signal(args.duration, args.frequency, args.voltage, args.waveform):
            print("\n🎉 SUCCESS!")
            print("✅ Micropump test completed successfully!")
            pump.close()
            return True
        else:
            print(f"\n❌ Test failed: {pump.get_last_error()}")
            pump.close()
            return False
    except Exception as e:
        print(f"\n❌ Test error: {e}")
        pump.close()
        return False

def run_admin_setup():
    """Run admin setup."""
    print("Running admin setup...")
    
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    admin_batch = project_root / "via_wsl" / "run_as_admin.bat"
    
    if not admin_batch.exists():
        print(f"Admin batch not found: {admin_batch}")
        return False
    
    try:
        result = subprocess.run([
            str(admin_batch), "attach_micropump.py"
        ], cwd=admin_batch.parent, check=False)
        return result.returncode == 0
    except Exception as e:
        print(f"Admin setup failed: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Smart micropump test with automatic fallback")
    parser.add_argument("--distro", default="Alpine", help="WSL distribution to use")
    parser.add_argument("--duration", type=float, default=1.0, help="Test pulse duration in seconds")
    parser.add_argument("--frequency", type=int, default=100, help="Frequency in Hz")
    parser.add_argument("--voltage", type=int, default=100, help="Voltage in Vpp")
    parser.add_argument("--waveform", default="RECT", help="Waveform (RECT, SINE)")
    parser.add_argument("--skip-windows", action="store_true", help="Skip Windows COM port attempt")
    parser.add_argument("--skip-setup", action="store_true", help="Skip admin setup if WSL fails")
    args = parser.parse_args()
    
    print("🔬 Smart Micropump Test")
    print("=" * 40)
    print(f"Strategy: Windows → WSL → Setup+Retry")
    print(f"Test params: {args.duration}s, {args.frequency}Hz, {args.voltage}Vpp, {args.waveform}")
    print("=" * 40)
    
    # TIER 1: Try Windows native first (fastest)
    if not args.skip_windows:
        pump = try_windows_pump()
        if pump:
            if test_and_exit(pump, args):
                sys.exit(0)
    
    # TIER 2: Try WSL
    pump = try_wsl_pump(args.distro)
    if pump:
        if test_and_exit(pump, args):
            sys.exit(0)
    
    # TIER 3: Run admin setup and retry WSL
    if not args.skip_setup:
        print("\n🔒 Both Windows and WSL failed. Running admin setup...")
        if run_admin_setup():
            print("🔄 Retrying WSL after admin setup...")
            time.sleep(3)  # Give devices time to be ready
            
            pump = try_wsl_pump(args.distro)
            if pump:
                if test_and_exit(pump, args):
                    sys.exit(0)
    
    # All methods failed
    print("\n❌ ALL PUMP INITIALIZATION METHODS FAILED")
    print("💡 Manual troubleshooting steps:")
    print("   1. Check if micropump is connected via USB")
    print("   2. Verify pump power is on")
    print("   3. Check Device Manager for COM ports")
    print("   4. Try running as administrator")
    print("   5. Install/reinstall FTDI drivers")
    sys.exit(1)


if __name__ == "__main__":
    main()
