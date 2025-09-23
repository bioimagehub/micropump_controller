"""Windows-specific pump controller with COM port auto-detection."""

import time
import serial
import logging
from typing import Optional
from resolve_ports import list_all_ports, find_pump_port_by_description, find_pump_port_by_vid_pid, get_port_by_id


class Pump_win:
    """Windows pump controller with automatic COM port detection."""
    
    def __init__(self, port: Optional[str] = None, baudrate: int = 9600):
        self.port = port
        self.baudrate = baudrate
        self.ser = None
        self.last_error = ""
        self.is_initialized = False
    
    def initialize(self) -> bool:
        """Initialize pump with automatic COM port detection if needed."""
        try:
            # If no port specified, try to find one automatically
            if self.port is None:
                self.port = self._find_pump_port()
                if self.port is None:
                    self.last_error = "No suitable COM ports found for pump"
                    return False
            
            # Try to connect to the pump
            self.ser = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=2,
                xonxoff=True  # XON/XOFF flow control for Bartels
            )
            
            # Test if pump responds
            if self._test_communication():
                self.is_initialized = True
                logging.info(f'Pump initialized successfully on {self.port}')
                return True
            else:
                self.ser.close()
                self.ser = None
                self.last_error = f"Pump found on {self.port} but not responding"
                return False
                
        except serial.SerialException as e:
            self.last_error = f'Failed to connect to pump on {self.port}: {e}'
            logging.error(self.last_error)
            return False
        except Exception as e:
            self.last_error = f'Unexpected error during initialization: {e}'
            logging.error(self.last_error)
            return False
    
    def _find_pump_port(self) -> Optional[str]:
        """Find a suitable COM port for the pump using resolve_ports functions."""
        # Get all available ports quickly
        all_ports = list_all_ports()
        if not all_ports:
            logging.info("No COM ports found")
            return None
        
        # Strategy 1: Try to find using .env file VID/PID (most accurate)
        try:
            port = get_port_by_id('pump')
            print(f"✅ Found pump using .env VID/PID: {port}")
            return port
        except Exception:
            print(f"⚠️  .env pump lookup failed: No pump device found with VID=1027 and PID=46272.")
        
        # Strategy 2: Try to find by description keywords
        pump_keywords = ["bartels", "ftdi", "ft232", "usb serial"]
        for keyword in pump_keywords:
            try:
                port = find_pump_port_by_description(keyword)
                print(f"✅ Found pump by description '{keyword}': {port}")
                return port
            except Exception:
                continue  # Try next keyword
        
        # Strategy 3: Try known FTDI VID/PID combinations
        ftdi_combinations = [
            (0x0403, 0xB4C0),  # Your specific pump from .env (1027, 46272)
            (0x0403, 0x6001),  # FTDI FT232R
            (0x0403, 0x6014),  # FTDI FT232H
            (0x0403, 0x6015),  # FTDI FT-X series
        ]
        
        for vid, pid in ftdi_combinations:
            try:
                port = find_pump_port_by_vid_pid(vid, pid)
                print(f"✅ Found pump by VID/PID {vid:04X}:{pid:04X}: {port}")
                return port
            except Exception:
                continue  # Try next combination
        
        print("❌ No suitable pump ports found")
        return None
    
    def _test_port_quick(self, port: str) -> bool:
        """Quick test if a port might be a pump - with fast timeout."""
        try:
            test_ser = serial.Serial(port, self.baudrate, timeout=0.1)  # Very short timeout
            test_ser.close()
            return True
        except Exception:
            return False
    
    def _test_communication(self) -> bool:
        """Test if pump responds to commands - with very short timeout."""
        try:
            # Send a simple command and see if pump accepts it
            self.ser.write(b"F100\r")
            self.ser.flush()
            time.sleep(0.05)  # Very short wait - just enough for command processing
            return True  # If no exception, assume it's working
        except Exception:
            return False
    
    def get_error_details(self) -> str:
        """Get detailed error information."""
        return self.last_error
    
    def get_suggested_fix(self) -> str:
        """Get suggested fix for the last error."""
        if "No suitable COM ports" in self.last_error or "No COM ports found" in self.last_error:
            return "Check if pump is connected via USB and drivers are installed. Try: Device Manager > Ports (COM & LPT)"
        elif "not responding" in self.last_error:
            return "Check pump power and cable connections. Verify correct COM port in Device Manager"
        elif "Failed to connect" in self.last_error:
            return "Port may be in use by another application. Close other serial programs"
        else:
            return "Try unplugging and reconnecting the pump USB cable"
    
    def close(self):
        """Close serial connection."""
        if self.ser is not None:
            try:
                self.ser.close()
                logging.info("Pump connection closed")
            except Exception:
                pass
        self.is_initialized = False
    
    def _send_command(self, command: str) -> bool:
        """Send command to pump with carriage return terminator."""
        if not self.is_initialized or self.ser is None:
            self.last_error = "Pump is not initialized"
            return False
        try:
            full_command = command + "\r"
            self.ser.write(full_command.encode("utf-8"))
            self.ser.flush()
            logging.info(f"Sent command: '{command}'")
            return True
        except Exception as e:
            self.last_error = f"Failed to send command '{command}': {e}"
            logging.error(self.last_error)
            return False
    
    def set_frequency(self, freq: int) -> bool:
        """Set pump frequency in Hz (1-300)."""
        if 1 <= freq <= 300:
            result = self._send_command(f"F{freq}")
            time.sleep(0.15)  # Allow processing time
            return result
        else:
            self.last_error = f"Invalid frequency: {freq} (must be 1-300)"
            logging.error(self.last_error)
            return False
    
    def set_voltage(self, voltage: int) -> bool:
        """Set pump voltage/amplitude (1-250 Vpp).""" 
        if 1 <= voltage <= 250:
            result = self._send_command(f"A{voltage}")
            time.sleep(0.15)
            return result
        else:
            self.last_error = f"Invalid voltage: {voltage} (must be 1-250)"
            logging.error(self.last_error)
            return False
    
    def set_waveform(self, waveform: str) -> bool:
        """Set pump waveform (RECT, SINE, etc)."""
        waveform_map = {
            "RECT": "MR",
            "RECTANGLE": "MR", 
            "SINE": "MS",
            "SIN": "MS"
        }
        cmd = waveform_map.get(waveform.upper(), waveform.upper())
        result = self._send_command(cmd)
        time.sleep(0.15)
        return result
    
    def start(self) -> bool:
        """Start the pump."""
        result = self._send_command("bon")
        if result:
            logging.info("Pump started")
        return result
    
    def stop(self) -> bool:
        """Stop the pump.""" 
        result = self._send_command("boff")
        if result:
            logging.info("Pump stopped")
        return result
    
    def pulse(self, duration: float) -> bool:
        """Run pump for specified duration then stop."""
        if not self.start():
            return False
        time.sleep(duration)
        return self.stop()
    
    def test_signal(self, duration: float = 1.0, frequency: int = 100, voltage: int = 100, waveform: str = "RECT") -> bool:
        """Test pump with specified parameters."""
        if not self.is_initialized:
            self.last_error = "Pump not initialized"
            return False
        
        try:
            # Configure pump
            if not self.set_frequency(frequency):
                return False
            if not self.set_voltage(voltage):
                return False
            if not self.set_waveform(waveform):
                return False
            
            # Run test pulse
            logging.info(f"Starting test pulse: {duration}s, {frequency}Hz, {voltage}Vpp, {waveform}")
            return self.pulse(duration)
            
        except Exception as e:
            self.last_error = f"Test signal failed: {e}"
            logging.error(self.last_error)
            return False
    
    def get_last_error(self) -> str:
        """Get the last error message."""
        return self.last_error