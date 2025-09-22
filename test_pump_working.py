#!/usr/bin/env python3
"""
Working USB pump controller - now that we know communication works!
Test different command formats and sequences.
"""

import time
import usb.core
import usb.util

class WorkingPumpController:
    def __init__(self):
        self.device = None
        self.ep_in = None
        self.ep_out = None
        
    def connect(self):
        """Connect to pump using working USB method."""
        try:
            self.device = usb.core.find(idVendor=0x0403, idProduct=0xB4C0)
            if self.device is None:
                return False
            
            # Set configuration
            self.device.set_configuration()
            
            # Get endpoints
            cfg = self.device.get_active_configuration()
            intf = cfg[(0,0)]
            
            for ep in intf:
                if usb.util.endpoint_direction(ep.bEndpointAddress) == usb.util.ENDPOINT_OUT:
                    self.ep_out = ep
                elif usb.util.endpoint_direction(ep.bEndpointAddress) == usb.util.ENDPOINT_IN:
                    self.ep_in = ep
            
            print("✅ Connected to pump successfully!")
            return True
            
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            return False
    
    def send_command_with_response(self, cmd_str):
        """Send command and read response."""
        try:
            cmd_bytes = (cmd_str + '\r').encode('ascii')
            sent = self.ep_out.write(cmd_bytes)
            print(f"📤 Sent {sent} bytes: {cmd_str}")
            
            # Wait and read response
            time.sleep(0.2)
            try:
                response = self.ep_in.read(64, timeout=1000)
                response_bytes = bytes(response)
                print(f"📥 Response: {response_bytes} ({response_bytes.hex()})")
                return response_bytes
            except usb.core.USBTimeoutError:
                print("📥 No response (timeout)")
                return b""
        except Exception as e:
            print(f"❌ Command failed: {e}")
            return None
    
    def test_pump_commands(self):
        """Test various pump command formats."""
        print("\n🧪 Testing pump command formats...")
        
        # Test basic commands
        test_commands = [
            "?",      # Status query
            "",       # Empty (just CR)
            "VER",    # Version
            "F100",   # Frequency
            "A100",   # Amplitude  
            "MR",     # Rectangle
            "bon",    # On
            "boff",   # Off
        ]
        
        for cmd in test_commands:
            print(f"\n--- Testing: '{cmd}' ---")
            response = self.send_command_with_response(cmd)
            time.sleep(0.3)
    
    def test_pump_sequence(self):
        """Test actual pump operation sequence."""
        print("\n🌊 Testing pump operation sequence...")
        
        print("Setting up pump...")
        self.send_command_with_response("F100")  # 100 Hz
        time.sleep(0.2)
        self.send_command_with_response("A150")  # 150 Vpp
        time.sleep(0.2)
        self.send_command_with_response("MR")    # Rectangle
        time.sleep(0.2)
        
        print("\n🔛 Turning pump ON (listen for sound)...")
        self.send_command_with_response("bon")
        
        print("⏱️ Pump running for 5 seconds...")
        time.sleep(5)
        
        print("🔴 Turning pump OFF...")
        self.send_command_with_response("boff")
    
    def disconnect(self):
        """Clean disconnect."""
        if self.device:
            usb.util.dispose_resources(self.device)
            self.device = None

def main():
    """Test the working pump controller."""
    print("🔧 Working USB Pump Controller Test")
    print("=" * 40)
    
    pump = WorkingPumpController()
    
    try:
        if not pump.connect():
            return
        
        # Test command communication
        pump.test_pump_commands()
        
        # Test actual pump operation
        input("\nPress Enter to test pump operation (will make sound if working)...")
        pump.test_pump_sequence()
        
        print("\n✅ Test complete!")
        
    except KeyboardInterrupt:
        print("\n⏹️ Test interrupted")
    finally:
        pump.disconnect()

if __name__ == "__main__":
    main()
