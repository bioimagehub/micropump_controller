#!/usr/bin/env python3
"""Quick test of pump classes."""

import sys
from pathlib import Path

# Add src directory to path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

def test_pump_win():
    """Test Windows pump class."""
    print("=== Testing Pump_win ===")
    try:
        import pump_win
        pump = pump_win.Pump_win()
        
        result = pump.initialize()
        print(f"Initialize result: {result}")
        
        if not result:
            print(f"Error: {pump.get_error_details()}")
            print(f"Suggested fix: {pump.get_suggested_fix()}")
        else:
            print("✅ Pump initialized!")
            
        pump.close()
        return result
        
    except Exception as e:
        print(f"❌ Pump_win error: {e}")
        return False

def test_pump_wsl():
    """Test WSL pump class."""
    print("\n=== Testing Pump_wsl ===")
    try:
        import pump_wsl
        pump = pump_wsl.Pump_wsl()
        
        result = pump.initialize()
        print(f"Initialize result: {result}")
        
        if not result:
            print(f"Error: {pump.get_error_details()}")
            print(f"Suggested fix: {pump.get_suggested_fix()}")
        else:
            print("✅ WSL pump initialized!")
            
        pump.close()
        return result
        
    except Exception as e:
        print(f"❌ Pump_wsl error: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Quick Pump Test")
    print("=" * 30)
    
    win_ok = test_pump_win()
    wsl_ok = test_pump_wsl()
    
    print(f"\n📊 Results:")
    print(f"Windows pump: {'✅' if win_ok else '❌'}")
    print(f"WSL pump: {'✅' if wsl_ok else '❌'}")
    
    if win_ok or wsl_ok:
        print("🎉 At least one pump method is working!")
    else:
        print("⚠️  Both pump methods failed (expected without hardware)")