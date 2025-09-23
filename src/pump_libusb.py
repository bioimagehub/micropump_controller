"""
Bartels Micropump Controller using libusb-win32 driver.

This version works with the libusb-win32 driver installed via Zadig.
It uses the PyUSB library to communicate directly with the USB device.
"""

import time
import logging

try:
    import usb.core
    import usb.util
    USB_AVAILABLE = True
except ImportError:
    USB_AVAILABLE = False
    print("❌ PyUSB not available - install with: pip install pyusb")

class PumpController:
    """
    Bartels micropump controller using libusb-win32 driver.
    
    This version uses PyUSB to communicate with the device after 
    installing libusb-win32 driver via Zadig.
    """
    
    def __init__(self, vid=0x0403, pid=0xB4C0):
        """
        Initialize pump controller for libusb device.
        
        Args:
            vid: Vendor ID (default: 0x0403 for FTDI)
            pid: Product ID (default: 0xB4C0 for Bartels)
        """
        self.vid = vid
        self.pid = pid
        self.device = None
        self.endpoint_out = None
        self.endpoint_in = None
        self._initialize()
    
    def _initialize(self):
        """Initialize USB connection using PyUSB."""
        if not USB_AVAILABLE:
            logging.error("PyUSB not available - cannot initialize USB device")
            return
            
        try:
            # Find the device
            self.device = usb.core.find(idVendor=self.vid, idProduct=self.pid)
            
            if self.device is None:
                logging.error(f"No device found with VID={self.vid:04X} PID={self.pid:04X}")
                return
            
            logging.info(f"Found USB device: VID={self.vid:04X} PID={self.pid:04X}")
            
            # Try to detach kernel driver if it exists (Linux)
            try:
                if self.device.is_kernel_driver_active(0):
                    self.device.detach_kernel_driver(0)
            except:
                pass  # Windows doesn't have kernel drivers to detach
            
            # Set configuration
            try:
                self.device.set_configuration()
            except usb.core.USBError as e:
                logging.warning(f"Could not set configuration: {e}")
            
            # Get endpoints
            cfg = self.device.get_active_configuration()
            intf = cfg[(0, 0)]
            
            # Find bulk endpoints
            self.endpoint_out = usb.util.find_descriptor(
                intf,
                custom_match=lambda e: usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_OUT
            )
            
            self.endpoint_in = usb.util.find_descriptor(
                intf,
                custom_match=lambda e: usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_IN
            )
            
            if self.endpoint_out is None:
                logging.error("Could not find output endpoint")
                return
            
            logging.info("USB pump connection established (libusb-win32)")
            
        except Exception as e:
            logging.error(f"Failed to initialize USB pump: {e}")
            self.device = None
    
    def close(self):
        """Close USB connection."""
        if self.device:
            try:
                usb.util.dispose_resources(self.device)
                self.device = None
                logging.info("USB pump connection closed")
            except Exception:
                pass
    
    def _send_command(self, command: str):
        """
        Send command to pump via USB.
        
        Args:
            command: Command string (without termination)
            
        Returns:
            bool: True if command sent successfully
        """
        if self.device is None or self.endpoint_out is None:
            logging.error("USB pump is not initialized.")
            return False
        
        try:
            # Add carriage return terminator (same as COM port version)
            full_command = command + "\r"
            command_bytes = full_command.encode("utf-8")
            
            # Write to the USB device
            bytes_written = self.endpoint_out.write(command_bytes, timeout=1000)
            
            if bytes_written == len(command_bytes):
                logging.info(f"Sent USB command: '{command}'")
                return True
            else:
                logging.error(f"Failed to send USB command '{command}': incomplete write")
                return False
                
        except Exception as e:
            logging.error(f"Failed to send USB command '{command}': {e}")
            return False
    
    def set_frequency(self, freq: int):
        """Set pump frequency in Hz (1-300)."""
        if 1 <= freq <= 300:
            self._send_command(f"F{freq}")
            time.sleep(0.15)  # Allow processing time
        else:
            logging.error(f"Frequency {freq} out of range (1-300 Hz)")
    
    def set_amplitude(self, amp: int):
        """Set pump amplitude (1-300)."""
        if 1 <= amp <= 300:
            self._send_command(f"A{amp}")
            time.sleep(0.15)  # Allow processing time
        else:
            logging.error(f"Amplitude {amp} out of range (1-300)")
    
    def set_voltage(self, voltage: int):
        """Set pump voltage/amplitude (1-250 Vpp) - alias for compatibility."""
        if 1 <= voltage <= 250:
            self._send_command(f"A{voltage}")
            time.sleep(0.15)
        else:
            logging.error(f"Invalid voltage: {voltage} (must be 1-250)")
    
    def start(self):
        """Start the pump."""
        self._send_command("bon")
        time.sleep(0.15)  # Allow processing time
        logging.info("USB pump started")
    
    def stop(self):
        """Stop the pump."""
        self._send_command("boff")
        time.sleep(0.15)  # Allow processing time
        logging.info("USB pump stopped")
    
    def start_pump(self):
        """Start pumping operation (alias for start)."""
        self.start()
    
    def stop_pump(self):
        """Stop pumping operation (alias for stop)."""
        self.stop()
    
    def pulse(self, duration: float):
        """Run pump for specified duration then stop."""
        self.start()
        time.sleep(duration)
        self.stop()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


# Test the controller
if __name__ == "__main__":
    # Configure logging to see what's happening
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    
    print("libusb-win32 Bartels Micropump Controller")
    print("========================================")
    print("Direct USB access with libusb-win32 driver")
    
    if not USB_AVAILABLE:
        print("\n❌ PyUSB not installed!")
        print("Install with: pip install pyusb")
        exit(1)
    
    # Initialize pump controller
    pump = PumpController()
    
    if pump.device is None:
        print("❌ Failed to initialize USB pump controller")
        print("Check that libusb-win32 driver is installed correctly")
    else:
        try:
            print("\n🧪 Running USB pump test...")
            
            # Test sequence
            print("1. Setting frequency to 100 Hz...")
            pump.set_frequency(100)
            
            print("2. Setting amplitude to 50...")
            pump.set_amplitude(50)
            
            print("3. Starting pump...")
            pump.start()
            
            print("4. Running for 2 seconds...")
            time.sleep(2)
            
            print("5. Stopping pump...")
            pump.stop()
            
            print("\n✅ USB pump control test completed!")
            print("libusb-win32 driver working correctly!")
            
        except KeyboardInterrupt:
            print("\n⏹️  Test interrupted")
        except Exception as e:
            print(f"\n❌ Error during test: {e}")
        finally:
            pump.close()
