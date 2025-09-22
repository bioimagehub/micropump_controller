#!/usr/bin/env python3
"""
Driver-free Bartels micropump using working USB bulk transfers with pybartelslabtronix commands.

This combines:
1. Our working USB bulk transfer code (that successfully communicates)
2. The proven pybartelslabtronix command protocol and timing
3. No drivers required
"""

import usb.core
import time
import logging

class BartelsUSBSimple:
    """
    Simple USB communication using proven command protocol.
    Uses the USB bulk transfer method that we know works.
    """
    
    def __init__(self, vid=0x0403, pid=0xb4c0):
        self.vid = vid
        self.pid = pid
        self.device = None
        
        # Setup logging
        logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
        self.log = logging.getLogger(__name__)
        
        self._connect()
    
    def _connect(self):
        """Connect to USB device using our proven method."""
        try:
            self.device = usb.core.find(idVendor=self.vid, idProduct=self.pid)
            
            if self.device is None:
                raise Exception("Bartels micropump not found")
            
            self.log.info(f"Found Bartels device: VID:{hex(self.vid)} PID:{hex(self.pid)}")
            
            # Don't set configuration - use device as-is (this worked before)
            self.log.info("Connected to Bartels micropump via USB")
            
        except Exception as e:
            self.log.error(f"Failed to connect: {e}")
            self.device = None
            raise
    
    def send_raw_command(self, command: str) -> bytes:
        """
        Send command using USB bulk transfer with pybartelslabtronix format.
        Uses the transfer method that we know works.
        """
        if not self.device:
            raise Exception("Not connected")
        
        # Format command exactly like pybartelslabtronix: command + \r
        full_command = command + "\r"
        data = full_command.encode('utf-8')
        
        self.log.info(f"Sending command: '{command}' -> {data}")
        
        try:
            # Send using bulk transfer to endpoint 0x02 (OUT) - this worked before
            bytes_sent = self.device.write(0x02, data, timeout=2000)
            self.log.info(f"Sent {bytes_sent} bytes")
            
            # Small delay like pybartelslabtronix
            time.sleep(0.2)
            
            # Try to read response from endpoint 0x81 (IN) - this also worked before
            try:
                response = self.device.read(0x81, 64, timeout=1000)
                self.log.info(f"Response: {response} -> {response.hex()}")
                return response
            except Exception as e:
                self.log.warning(f"No response or read error: {e}")
                return b''
                
        except Exception as e:
            self.log.error(f"Command failed: {e}")
            return b''
    
    def test_pybartelslabtronix_commands(self):
        """Test all the pybartelslabtronix commands systematically."""
        commands = [
            ("", "Get Status"),
            ("F100", "Set Frequency 100 Hz"),
            ("A100", "Set Amplitude 100 Vpp"), 
            ("MR", "Set Rectangular Waveform"),
            ("bon", "Turn Pump ON"),
            ("", "Get Status After ON"),
            ("boff", "Turn Pump OFF"),
            ("", "Get Status After OFF"),
        ]
        
        print("\n=== Testing pybartelslabtronix Commands ===")
        
        for command, description in commands:
            print(f"\n{description}: '{command}'")
            response = self.send_raw_command(command)
            
            if response:
                # Try to decode response
                try:
                    text = response.decode('utf-8', errors='ignore').strip()
                    if text:
                        print(f"  Text response: '{text}'")
                    else:
                        print(f"  Binary response: {response.hex()}")
                except:
                    print(f"  Raw response: {response.hex()}")
            else:
                print("  No response")
            
            # Wait between commands like pybartelslabtronix
            time.sleep(0.5)
    
    def pump_operation_test(self):
        """Full pump operation test with audio feedback."""
        print("\n=== Full Pump Operation Test ===")
        
        try:
            print("1. Setting frequency to 100 Hz...")
            self.send_raw_command("F100")
            time.sleep(0.5)
            
            print("2. Setting amplitude to 100 Vpp...")
            self.send_raw_command("A100")
            time.sleep(0.5)
            
            print("3. Setting rectangular waveform...")
            self.send_raw_command("MR")
            time.sleep(0.5)
            
            print("4. Getting status before operation...")
            self.send_raw_command("")
            time.sleep(0.5)
            
            print("5. *** TURNING PUMP ON - LISTEN FOR SOUND ***")
            self.send_raw_command("bon")
            
            # Run for 10 seconds
            for i in range(10):
                print(f"   Pump running... {10-i} seconds remaining")
                time.sleep(1)
            
            print("6. *** TURNING PUMP OFF ***")
            self.send_raw_command("boff")
            
            print("7. Getting final status...")
            self.send_raw_command("")
            
            print("\n✓ Pump operation test completed")
            
        except Exception as e:
            print(f"✗ Pump test failed: {e}")
    
    def close(self):
        """Close USB connection."""
        if self.device:
            usb.util.dispose_resources(self.device)
            self.device = None
            self.log.info("USB connection closed")


def main():
    """Test driver-free communication with pybartelslabtronix protocol."""
    print("=== Driver-Free Bartels Test with pybartelslabtronix Protocol ===")
    
    try:
        pump = BartelsUSBSimple()
        
        # Test individual commands first
        pump.test_pybartelslabtronix_commands()
        
        # Ask user if they want to do full pump test
        print("\n" + "="*50)
        response = input("Do you want to run the full pump operation test? (y/N): ")
        
        if response.lower().startswith('y'):
            pump.pump_operation_test()
        else:
            print("Skipping pump operation test")
        
    except Exception as e:
        print(f"Test failed: {e}")
    finally:
        try:
            pump.close()
        except:
            pass


if __name__ == "__main__":
    main()
