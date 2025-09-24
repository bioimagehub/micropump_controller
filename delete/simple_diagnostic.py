#!/usr/bin/env python3
"""
Simple diagnostic: Compare working driver vs Windows API
"""

import serial
import time
import sys
import os

# Add src directory for imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from pump import PumpController
from delete.resolve_ports import find_pump_port_by_vid_pid

def test_working_vs_api():
    """Compare working driver vs Windows API."""
    
    # Find pump
    pump_port = find_pump_port_by_vid_pid(0x0403, 0xB4C0)
    print(f"🔍 Testing pump on: {pump_port}")
    
    print("\\n📍 TEST 1: WORKING DRIVER")
    print("=" * 30)
    
    # Test working driver
    try:
        pump = PumpController(pump_port)
        print("✅ Working driver connected")
        
        print("🔧 Configuring pump with working driver...")
        pump.set_waveform("rectangle")
        pump.set_frequency(100)
        pump.set_voltage(100)
        
        print("▶️  Starting pump...")
        pump.start()
        
        print("🎧 LISTEN: Do you hear the pump? (y/n): ", end="")
        working_response = input().lower().strip()
        
        pump.stop()
        pump.close()
        
        if working_response in ['y', 'yes']:
            print("✅ Working driver: SUCCESS")
            working_success = True
        else:
            print("❌ Working driver: FAILED")
            working_success = False
            
    except Exception as e:
        print(f"❌ Working driver error: {e}")
        working_success = False
    
    print("\\n📍 TEST 2: DIRECT PYSERIAL")
    print("=" * 30)
    
    # Test direct pyserial (same as working driver but manual)
    try:
        with serial.Serial(pump_port, 9600, timeout=2) as ser:
            print("✅ Direct serial connected")
            
            print("🔧 Sending commands via pyserial...")
            commands = ["MR\\r", "F100\\r", "A100\\r", "bon\\r"]
            
            for cmd in commands:
                cmd_bytes = cmd.encode('utf-8')
                ser.write(cmd_bytes)
                print(f"   Sent: {cmd} ({len(cmd_bytes)} bytes)")
                time.sleep(0.2)
            
            print("🎧 LISTEN: Do you hear the pump? (y/n): ", end="")
            serial_response = input().lower().strip()
            
            # Stop pump
            ser.write(b'boff\\r')
            print("   Sent: boff")
            
            if serial_response in ['y', 'yes']:
                print("✅ Direct serial: SUCCESS")
                serial_success = True
            else:
                print("❌ Direct serial: FAILED") 
                serial_success = False
                
    except Exception as e:
        print(f"❌ Direct serial error: {e}")
        serial_success = False
    
    print("\\n📊 RESULTS ANALYSIS")
    print("=" * 25)
    print(f"Working driver: {'✅ SUCCESS' if working_success else '❌ FAILED'}")
    print(f"Direct serial:  {'✅ SUCCESS' if serial_success else '❌ FAILED'}")
    
    if working_success and not serial_success:
        print("\\n🤔 ANALYSIS: Working driver succeeds but direct serial fails")
        print("💡 The working driver likely does additional setup/configuration")
        print("🔧 Need to investigate what the PumpController._send_command() actually does")
        
    elif not working_success:
        print("\\n⚠️  WARNING: Even working driver failed!")
        print("💡 Check pump connections and power")
        
    elif working_success and serial_success:
        print("\\n✅ BREAKTHROUGH: Direct serial communication works!")
        print("💡 The Windows API approach might have wrong serial settings")
        
    else:
        print("\\n❌ Both approaches failed")
        print("💡 Hardware or connection issue")

if __name__ == "__main__":
    test_working_vs_api()