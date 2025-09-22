#!/usr/bin/env python3
"""
Advanced pump protocol testing - try different command formats and initialization.
"""

import time
import usb.core
import usb.util

class AdvancedPumpTester:
    def __init__(self):
        self.device = None
        self.ep_in = None
        self.ep_out = None
        
    def connect(self):
        """Connect to pump."""
        try:
            self.device = usb.core.find(idVendor=0x0403, idProduct=0xB4C0)
            if self.device is None:
                return False
            
            self.device.set_configuration()
            cfg = self.device.get_active_configuration()
            intf = cfg[(0,0)]
            
            for ep in intf:
                if usb.util.endpoint_direction(ep.bEndpointAddress) == usb.util.ENDPOINT_OUT:
                    self.ep_out = ep
                elif usb.util.endpoint_direction(ep.bEndpointAddress) == usb.util.ENDPOINT_IN:
                    self.ep_in = ep
            
            return True
        except Exception as e:
            print(f"Connection failed: {e}")
            return False
    
    def send_raw_command(self, cmd_bytes):
        """Send raw bytes and get response."""
        try:
            sent = self.ep_out.write(cmd_bytes)
            print(f"📤 Sent {sent} bytes: {cmd_bytes} ({cmd_bytes.hex()})")
            
            time.sleep(0.2)
            try:
                response = self.ep_in.read(64, timeout=1000)
                response_bytes = bytes(response)
                print(f"📥 Response: {response_bytes} ({response_bytes.hex()})")
                return response_bytes
            except usb.core.USBTimeoutError:
                print("📥 No response")
                return b""
        except Exception as e:
            print(f"❌ Send failed: {e}")
            return None
    
    def test_different_protocols(self):
        """Test different command protocols."""
        print("🧪 Testing different command protocols...")
        
        # Test 1: Standard ASCII commands
        print("\n--- ASCII Commands ---")
        ascii_commands = [
            b"F100\r",
            b"F100\n", 
            b"F100\r\n",
            b"f100\r",  # lowercase
        ]
        
        for cmd in ascii_commands:
            self.send_raw_command(cmd)
            time.sleep(0.1)
        
        # Test 2: Binary commands (maybe it expects hex values?)
        print("\n--- Binary Commands ---")
        # Frequency 100 as binary (different formats)
        binary_commands = [
            b"\x46\x64\r",      # F(0x46) + 100(0x64) + CR
            b"\x01\x64",        # Binary frequency command
            b"\x66\x64\x00",    # Different binary format
            bytes([0x46, 100, 13]),  # Another format
        ]
        
        for cmd in binary_commands:
            self.send_raw_command(cmd)
            time.sleep(0.1)
        
        # Test 3: Control characters
        print("\n--- Control Characters ---")
        control_commands = [
            b"\x01",           # Start of text
            b"\x02",           # Start of transmission  
            b"\x04",           # End of transmission
            b"\x06",           # Acknowledge
            b"\x15",           # Negative acknowledge
            b"\x1b",           # Escape
        ]
        
        for cmd in control_commands:
            self.send_raw_command(cmd)
            time.sleep(0.1)
    
    def test_initialization_sequences(self):
        """Test possible initialization sequences."""
        print("\n🔧 Testing initialization sequences...")
        
        # Common device initialization patterns
        init_sequences = [
            [b"\x1b", b"*RST\r"],           # SCPI reset
            [b"*IDN?\r"],                   # Identification query
            [b"INIT\r", b"F100\r", b"ON\r"], # Initialize then command
            [b"\x02", b"F100\r", b"\x03"],  # STX + command + ETX
            [b"RESET\r", b"F100\r"],        # Reset first
            [b"MODE 1\r", b"F100\r"],       # Set mode first
        ]
        
        for i, sequence in enumerate(init_sequences):
            print(f"\n--- Init Sequence {i+1} ---")
            for cmd in sequence:
                self.send_raw_command(cmd)
                time.sleep(0.3)
    
    def analyze_response_pattern(self):
        """Analyze what the 0x01 0x60 response means."""
        print("\n🔍 Analyzing response pattern...")
        
        # The response is always 0x01 0x60
        # 0x01 = 1 decimal (might be status OK)
        # 0x60 = 96 decimal = 0110 0000 binary
        
        print("Response analysis:")
        print("  0x01 = 1 (possibly status: OK/ACK)")
        print("  0x60 = 96 decimal = 0110 0000 binary")
        print("  Bit pattern: 01100000")
        print("    Bit 7: 0")
        print("    Bit 6: 1 (could indicate error or mode)")
        print("    Bit 5: 1")
        print("    Bits 4-0: 00000")
        
        # Try interpreting as error codes
        if 0x60 == 96:
            print("  Possible meanings:")
            print("    - Error code 96")
            print("    - Parameter out of range")
            print("    - Command not recognized")
            print("    - Device not initialized")
    
    def test_ftdi_specific_commands(self):
        """Test FTDI-specific protocols."""
        print("\n🔌 Testing FTDI-specific protocols...")
        
        # FTDI devices sometimes need special handling
        ftdi_commands = [
            b"\xff\xff\xff",    # FTDI reset sequence
            b"\xaa",            # FTDI sync byte
            b"\x00\x00",        # FTDI null command
        ]
        
        for cmd in ftdi_commands:
            self.send_raw_command(cmd)
            time.sleep(0.1)

def main():
    """Run advanced pump testing."""
    print("🔬 Advanced Pump Protocol Testing")
    print("=" * 50)
    
    tester = AdvancedPumpTester()
    
    if not tester.connect():
        print("❌ Failed to connect")
        return
    
    print("✅ Connected successfully")
    
    try:
        tester.analyze_response_pattern()
        tester.test_different_protocols()
        tester.test_initialization_sequences()
        tester.test_ftdi_specific_commands()
        
        print("\n📊 Summary:")
        print("- USB communication: ✅ Working")
        print("- Device responses: ✅ Consistent (0x01 0x60)")
        print("- Pump operation: ❌ Not working")
        print("\n💡 Possible issues:")
        print("1. Wrong command protocol/format")
        print("2. Missing initialization sequence")
        print("3. Hardware fault in pump")
        print("4. Needs FTDI D2XX driver instead of libusb")
        
    except KeyboardInterrupt:
        print("\n⏹️ Test interrupted")
    finally:
        if tester.device:
            usb.util.dispose_resources(tester.device)

if __name__ == "__main__":
    main()
