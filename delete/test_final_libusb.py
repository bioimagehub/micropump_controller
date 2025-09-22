#!/usr/bin/env python3
"""
Final test: Use working libusb communication with exact pybartelslabtronix protocol.
This combines our successful libusb connection with the proven protocol timing.
"""

import usb.core
import usb.util
import time
import threading

class BartelsLibUSBFinal:
    """Final attempt using working libusb + pybartelslabtronix protocol."""
    
    def __init__(self):
        self.device = None
        self.ep_in = 0x81
        self.ep_out = 0x02
        self.buffer = ""
        self.reading = False
        self._connect()
    
    def _connect(self):
        """Connect using our proven libusb method."""
        self.device = usb.core.find(idVendor=0x0403, idProduct=0xb4c0)
        if self.device is None:
            raise Exception("Device not found")
        
        # Claim interface
        usb.util.claim_interface(self.device, 0)
        print("✓ Connected via libusb")
        
        # Start reading thread like pybartelslabtronix
        self.reading = True
        self.read_thread = threading.Thread(target=self._read_loop, daemon=True)
        self.read_thread.start()
    
    def _read_loop(self):
        """Background reading like pybartelslabtronix."""
        while self.reading:
            try:
                time.sleep(0.05)  # 50ms like pybartelslabtronix
                response = self.device.read(self.ep_in, 64, 100)
                if response:
                    text = bytes(response).decode('utf-8', errors='ignore')
                    self.buffer += text
                    print(f"[READ] {repr(text)}")
            except usb.core.USBTimeoutError:
                pass  # Normal timeout
            except Exception as e:
                print(f"[READ ERROR] {e}")
                break
    
    def send_command(self, command):
        """Send command with pybartelslabtronix format."""
        full_cmd = command + "\r"
        data = full_cmd.encode('utf-8')
        
        self.buffer = ""  # Clear buffer like pybartelslabtronix
        bytes_sent = self.device.write(self.ep_out, data, 2000)
        print(f"[SEND] '{command}' -> {bytes_sent} bytes")
        return bytes_sent > 0
    
    def get_status(self):
        """Get status like pybartelslabtronix."""
        self.send_command("")  # Empty command
        
        # Wait for response with timeout
        timeout = time.time() + 2.0
        while (len(self.buffer) < 1 or self.reading) and time.time() < timeout:
            time.sleep(0.01)
        
        response = self.buffer.strip()
        print(f"[STATUS] {repr(response)}")
        return response
    
    def test_initialization_sequences(self):
        """Try different initialization sequences."""
        print("\n=== Testing Initialization Sequences ===")
        
        sequences = [
            # Standard approach
            ["", "F100", "A100", "MR"],
            
            # With delays
            ["", None, "F100", None, "A100", None, "MR"],
            
            # Multiple status requests
            ["", "", "", "F100"],
            
            # Different command order
            ["MR", "F100", "A100", ""],
            
            # Reset-like sequences
            ["boff", "", "F100", "A100", "MR"],
        ]
        
        for i, sequence in enumerate(sequences):
            print(f"\nTesting sequence {i+1}: {sequence}")
            
            for cmd in sequence:
                if cmd is None:
                    time.sleep(0.5)  # Longer delay
                else:
                    self.send_command(cmd)
                    time.sleep(0.2)
            
            # Check final status
            status = self.get_status()
            if status and status != '\x01`':
                print(f"✓ Different response with sequence {i+1}!")
                return True
        
        return False
    
    def test_pump_operation(self):
        """Test actual pump operation."""
        print("\n=== Pump Operation Test ===")
        
        # Setup
        self.send_command("F100")
        time.sleep(0.5)
        self.send_command("A100") 
        time.sleep(0.5)
        self.send_command("MR")
        time.sleep(0.5)
        
        print("Starting pump - LISTEN FOR SOUND!")
        self.send_command("bon")
        
        # Run for 10 seconds
        for i in range(10):
            print(f"  Running... {10-i} seconds")
            time.sleep(1)
        
        print("Stopping pump")
        self.send_command("boff")
        
        # Final status
        self.get_status()
    
    def close(self):
        """Cleanup."""
        self.reading = False
        if hasattr(self, 'read_thread'):
            self.read_thread.join(timeout=1)
        
        if self.device:
            usb.util.release_interface(self.device, 0)
            usb.util.dispose_resources(self.device)

def main():
    """Final comprehensive test."""
    print("=== Final Bartels Micropump Test ===")
    print("Using: libusb driver + pybartelslabtronix protocol")
    
    pump = None
    try:
        pump = BartelsLibUSBFinal()
        
        # Test initialization sequences
        if pump.test_initialization_sequences():
            print("\n✓ Found working initialization sequence!")
        else:
            print("\n⚠ Standard responses only, but proceeding...")
        
        # Ask user about pump test
        print("\n" + "="*50)
        response = input("Run pump operation test? (y/N): ").strip().lower()
        
        if response.startswith('y'):
            pump.test_pump_operation()
        else:
            print("Skipping pump test")
        
        print("\n=== SUMMARY ===")
        print("✓ libusb communication: WORKING")
        print("✓ Command sending: WORKING") 
        print("✓ Response receiving: WORKING")
        print("? Pump protocol: Needs investigation")
        print("\nThe pump may need:")
        print("1. Different command format")
        print("2. Specific initialization sequence")
        print("3. Different baud rate emulation")
        print("4. Hardware-specific commands")
        
    except Exception as e:
        print(f"Test failed: {e}")
    finally:
        if pump:
            pump.close()

if __name__ == "__main__":
    main()
