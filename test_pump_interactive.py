#!/usr/bin/env python3
"""
Interactive pump controller - allows manual testing of specific frequencies and amplitudes.
Type commands like: F100, A150, MR, bon, boff
"""

import time
from test_pump_windows_native import BartelsPumpController

def interactive_mode():
    """Interactive pump control."""
    pump = BartelsPumpController()
    
    try:
        if not pump.connect():
            print("❌ Failed to connect to pump")
            return
        
        print("✅ Connected to Bartels pump!")
        print("\n🎛️  Interactive Mode")
        print("Commands:")
        print("  F### - Set frequency (F050 = 50Hz, F100 = 100Hz)")
        print("  A### - Set amplitude (A100 = 100Vpp, A150 = 150Vpp)")
        print("  MR   - Rectangular waveform")
        print("  MS   - Sine waveform")
        print("  bon  - Turn pump ON")
        print("  boff - Turn pump OFF")
        print("  ?    - Get status")
        print("  quit - Exit")
        print("\nExample: F100 → A100 → MR → bon → (listen) → boff")
        print("=" * 50)
        
        while True:
            try:
                cmd = input("\nPump> ").strip()
                
                if cmd.lower() in ['quit', 'exit', 'q']:
                    break
                elif cmd == '?':
                    print("Sending status request...")
                    pump.send_command("")  # Empty command = status request
                elif cmd:
                    result = pump.send_command(cmd)
                    if result:
                        print(f"✅ Command sent: {cmd}")
                    else:
                        print(f"❌ Command failed: {cmd}")
                        
            except KeyboardInterrupt:
                print("\n\n🔴 Stopping pump...")
                pump.send_command("boff")
                break
            except EOFError:
                break
        
        print("\n👋 Exiting interactive mode...")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        pump.send_command("boff")  # Ensure pump is off
        pump.disconnect()

if __name__ == "__main__":
    interactive_mode()
