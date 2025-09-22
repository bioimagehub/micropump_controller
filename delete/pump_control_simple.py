#!/usr/bin/env python3
"""
Plug-and-Play Bartels Micropump Controller

Simple, one-command interface for controlling Bartels micropumps on Windows.
No drivers required! Uses direct USB communication.

Usage:
    python pump_control_simple.py pulse 10      # 10-second pulse
    python pump_control_simple.py pulse 5       # 5-second pulse  
    python pump_control_simple.py on            # Turn on (manual off)
    python pump_control_simple.py off           # Turn off
    python pump_control_simple.py status        # Check connection
"""

import sys
import time
import argparse
from test_pump_windows_native import BartelsPumpController


def main():
    parser = argparse.ArgumentParser(description="Bartels Micropump Controller")
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Pulse command
    pulse_parser = subparsers.add_parser('pulse', help='Send pulse for specified duration')
    pulse_parser.add_argument('duration', type=int, help='Pulse duration in seconds')
    pulse_parser.add_argument('--freq', type=int, default=100, help='Frequency in Hz (default: 100)')
    pulse_parser.add_argument('--amp', type=int, default=150, help='Amplitude in Vpp (default: 150)')
    
    # On/Off commands
    subparsers.add_parser('on', help='Turn pump on')
    subparsers.add_parser('off', help='Turn pump off')
    subparsers.add_parser('status', help='Check pump connection status')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    print("🔌 Connecting to Bartels pump...")
    pump = BartelsPumpController()
    
    try:
        if not pump.connect():
            print("❌ Failed to connect to pump")
            print("\n💡 Troubleshooting:")
            print("   1. Ensure pump is plugged into USB port")
            print("   2. Try different USB port") 
            print("   3. Install drivers: hardware\\drivers\\install_unsigned_bartels_drivers.bat")
            return 1
        
        print("✅ Connected successfully!")
        
        if args.command == 'pulse':
            duration = args.duration
            print(f"🌊 Starting {duration}s pulse (F={args.freq}Hz, A={args.amp}Vpp)...")
            
            # Setup commands with proper timing (200ms between commands)
            pump.send_command(f"F{args.freq}")
            time.sleep(0.2)
            pump.send_command(f"A{args.amp}")
            time.sleep(0.2)
            pump.send_command("MR")  # Rectangular wave
            time.sleep(0.2)
            pump.send_command("bon")  # Turn on
            time.sleep(0.2)
            
            # Progress indicator
            for i in range(duration):
                print(f"⏱️  {i+1}/{duration}s", end='\r')
                time.sleep(1)
            
            pump.send_command("boff")  # Correct stop command
            print(f"\n✅ Pulse completed!")
            
        elif args.command == 'on':
            print("🔛 Turning pump ON...")
            pump.send_command("F100")
            time.sleep(0.2)
            pump.send_command("A150")
            time.sleep(0.2)
            pump.send_command("MR")
            time.sleep(0.2)
            pump.send_command("bon")
            print("✅ Pump is ON. Use 'off' command to stop.")
            
        elif args.command == 'off':
            print("🔴 Turning pump OFF...")
            pump.send_command("boff")  # Correct stop command
            print("✅ Pump is OFF.")
            
        elif args.command == 'status':
            print("✅ Pump connection is working!")
            pump.send_command("")  # Status query
            
        return 0
        
    except KeyboardInterrupt:
        print("\n🛑 Interrupted! Turning pump off...")
        pump.send_command("bof")
        return 0
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1
        
    finally:
        pump.disconnect()


if __name__ == "__main__":
    sys.exit(main())
