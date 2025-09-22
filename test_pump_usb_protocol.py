#!/usr/bin/env python3
"""
Driver-free Bartels micropump control using USB with pybartelslabtronix protocol.

This solution:
1. Uses direct USB communication (no drivers needed)
2. Implements the proven pybartelslabtronix command protocol
3. Emulates XON/XOFF flow control at the application level
4. Uses proper command timing and formatting
"""

import usb.core
import usb.util
import time
import threading
import logging
from typing import Optional, Dict, Any

class BartelsUSBProtocol:
    """
    Bartels micropump control using USB with serial-like protocol.
    Based on pybartelslabtronix but without needing COM port drivers.
    """
    
    def __init__(self, vid=0x0403, pid=0xb4c0):
        self.vid = vid
        self.pid = pid
        self.device = None
        self.ep_in = None
        self.ep_out = None
        self.buffer = ""
        self.reading = False
        self.read_thread = None
        
        # XON/XOFF flow control characters
        self.XON = 0x11
        self.XOFF = 0x13
        self.flow_control_enabled = True
        
        # Setup logging
        logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
        self.log = logging.getLogger(__name__)
        
        self._connect()
    
    def _connect(self):
        """Connect to the USB device and configure endpoints."""
        try:
            # Find the device
            self.device = usb.core.find(idVendor=self.vid, idProduct=self.pid)
            
            if self.device is None:
                raise Exception("Bartels micropump not found")
            
            self.log.info(f"Found Bartels device: VID:{hex(self.vid)} PID:{hex(self.pid)}")
            
            # Set configuration (required for USB communication)
            try:
                self.device.set_configuration()
            except usb.core.USBError as e:
                self.log.warning(f"Could not set configuration: {e}")
            
            # Get the interface
            interface = self.device.get_active_configuration()[(0,0)]
            
            # Find bulk endpoints
            self.ep_out = usb.util.find_descriptor(
                interface,
                custom_match=lambda e: usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_OUT
            )
            
            self.ep_in = usb.util.find_descriptor(
                interface,
                custom_match=lambda e: usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_IN
            )
            
            if self.ep_out is None or self.ep_in is None:
                raise Exception("Could not find bulk endpoints")
            
            self.log.info(f"USB endpoints: OUT=0x{self.ep_out.bEndpointAddress:02x}, IN=0x{self.ep_in.bEndpointAddress:02x}")
            
            # Start background reading thread (like pybartelslabtronix)
            self.reading = True
            self.read_thread = threading.Thread(target=self._read_continuously, daemon=True)
            self.read_thread.start()
            
            # Send initial XON to enable flow
            self._send_flow_control(self.XON)
            
            self.log.info("Connected to Bartels micropump via USB")
            
        except Exception as e:
            self.log.error(f"Failed to connect: {e}")
            self.device = None
            raise
    
    def _send_flow_control(self, control_char):
        """Send XON/XOFF flow control character."""
        if not self.flow_control_enabled:
            return
        
        try:
            self.ep_out.write([control_char], timeout=1000)
        except Exception as e:
            self.log.debug(f"Flow control send failed: {e}")
    
    def _read_continuously(self):
        """Continuously read from USB device (background thread like pybartelslabtronix)."""
        while self.reading and self.device:
            try:
                time.sleep(0.05)  # 50ms polling like pybartelslabtronix
                
                # Try to read data
                try:
                    data = self.ep_in.read(64, timeout=100)  # 100ms timeout
                    if data:
                        # Convert bytes to string, filtering out control characters
                        text = ''.join(chr(b) for b in data if 32 <= b <= 126 or b in [10, 13])
                        if text:
                            self.buffer += text
                            self.log.debug(f"Received: {repr(text)}")
                except usb.core.USBTimeoutError:
                    # Normal timeout, continue
                    pass
                except Exception as e:
                    self.log.debug(f"Read error: {e}")
                    
            except Exception as e:
                self.log.error(f"Read thread error: {e}")
                break
    
    def _send_command(self, command: str) -> bool:
        """Send a command using pybartelslabtronix protocol."""
        if not self.device:
            self.log.error("No USB connection")
            return False
        
        try:
            # Format command exactly like pybartelslabtronix
            full_command = command + "\r"
            
            # Send XOFF to pause any incoming data
            self._send_flow_control(self.XOFF)
            time.sleep(0.01)
            
            # Send the command
            data = full_command.encode('utf-8')
            bytes_written = self.ep_out.write(data, timeout=2000)
            
            # Send XON to resume flow
            time.sleep(0.01)
            self._send_flow_control(self.XON)
            
            self.log.info(f"Sent command: '{command}' ({bytes_written} bytes)")
            return True
            
        except Exception as e:
            self.log.error(f"Failed to send command '{command}': {e}")
            return False
    
    def get_status(self) -> Optional[str]:
        """Get pump status by sending empty command (pybartelslabtronix method)."""
        self.buffer = ""  # Clear buffer
        
        if not self._send_command(""):  # Empty command requests status
            return None
        
        # Wait for response with timeout
        timeout = time.time() + 3.0
        while (len(self.buffer) < 5 or self.reading) and time.time() < timeout:
            time.sleep(0.01)
        
        if self.buffer:
            response = self.buffer.strip()
            self.log.info(f"Status response: {repr(response)}")
            return response
        else:
            self.log.warning("No status response received")
            return None
    
    def parse_status(self, status_text: str) -> Dict[str, Any]:
        """Parse status response like pybartelslabtronix."""
        result = {}
        if not status_text:
            return result
        
        lines = status_text.split('\r\n')
        for line in lines:
            line = line.strip()
            if ':' in line:
                key, value = line.split(':', 1)
                result[key.strip()] = value.strip()
            elif ' ' in line:
                parts = line.split(' ', 1)
                if len(parts) == 2:
                    result[parts[0].strip()] = parts[1].strip()
        
        return result
    
    def turn_on(self) -> bool:
        """Turn pump on using pybartelslabtronix command."""
        return self._send_command("bon")
    
    def turn_off(self) -> bool:
        """Turn pump off using pybartelslabtronix command."""
        return self._send_command("boff")
    
    def set_frequency(self, freq: int) -> bool:
        """Set frequency (1-300 Hz) using pybartelslabtronix format."""
        if not (1 <= freq <= 300):
            self.log.error(f"Invalid frequency: {freq} (must be 1-300)")
            return False
        return self._send_command(f"F{freq}")
    
    def set_amplitude(self, amp: int) -> bool:
        """Set amplitude (1-250 Vpp) using pybartelslabtronix format."""
        if not (1 <= amp <= 250):
            self.log.error(f"Invalid amplitude: {amp} (must be 1-250)")
            return False
        return self._send_command(f"A{amp}")
    
    def set_waveform_rectangular(self) -> bool:
        """Set rectangular waveform using pybartelslabtronix command."""
        return self._send_command("MR")
    
    def set_waveform_sine(self) -> bool:
        """Set sine waveform using pybartelslabtronix command."""
        return self._send_command("MS")
    
    def set_waveform_srs(self) -> bool:
        """Set SRS waveform using pybartelslabtronix command."""
        return self._send_command("MC")
    
    def close(self):
        """Close the USB connection."""
        self.reading = False
        if self.read_thread:
            self.read_thread.join(timeout=1.0)
        
        if self.device:
            # Send XOFF to stop any communication
            self._send_flow_control(self.XOFF)
            usb.util.dispose_resources(self.device)
            self.device = None
        
        self.log.info("USB connection closed")


def main():
    """Test the driver-free Bartels pump communication."""
    print("=== Driver-Free Bartels Micropump Test ===")
    print("Using pybartelslabtronix protocol over direct USB")
    
    try:
        # Create pump controller
        pump = BartelsUSBProtocol()
        
        print("\n1. Getting initial status...")
        status = pump.get_status()
        if status:
            print(f"Status: {status}")
            parsed = pump.parse_status(status)
            print(f"Parsed: {parsed}")
        
        print("\n2. Setting pump parameters (pybartelslabtronix protocol)...")
        pump.set_frequency(100)
        time.sleep(0.5)
        pump.set_amplitude(100)
        time.sleep(0.5)
        pump.set_waveform_rectangular()
        time.sleep(0.5)
        
        print("\n3. Getting updated status...")
        status = pump.get_status()
        if status:
            print(f"Updated status: {status}")
        
        print("\n4. Turning pump ON for 10 seconds...")
        pump.turn_on()
        print("*** LISTEN FOR PUMP SOUND ***")
        
        # Run for 10 seconds
        for i in range(10):
            print(f"Running... {10-i} seconds remaining")
            time.sleep(1)
        
        print("\n5. Turning pump OFF...")
        pump.turn_off()
        print("*** PUMP SHOULD BE QUIET NOW ***")
        
        print("\n6. Getting final status...")
        status = pump.get_status()
        if status:
            print(f"Final status: {status}")
        
        print("\n✓ Test completed successfully!")
        
    except Exception as e:
        print(f"✗ Test failed: {e}")
        print("\nThis might happen if:")
        print("1. Device is not connected")
        print("2. Device is in use by another application")
        print("3. USB permissions issue")
        
    finally:
        try:
            pump.close()
        except:
            pass


if __name__ == "__main__":
    main()
