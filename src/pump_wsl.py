"""WSL-based pump controller - drop-in replacement for Windows pump controller."""

import subprocess
import time
import logging
from typing import Optional, List


class Pump_wsl:
    """WSL pump controller with same interface as Pump_win."""
    
    def __init__(self, distro: str = "Alpine", port: Optional[str] = None, baudrate: int = 9600):
        self.distro = distro
        self.port = port
        self.baudrate = baudrate
        self.last_error = ""
        self.is_initialized = False
        self._available_ports = []
    
    def initialize(self) -> bool:
        """Initialize pump via WSL with automatic port detection."""
        try:
            # Check if WSL distro is available
            if not self._check_wsl_distro():
                return False
            
            # Find available serial ports in WSL
            if self.port is None:
                self.port = self._find_wsl_pump_port()
                if self.port is None:
                    self.last_error = "No serial ports found in WSL"
                    return False
            
            # Test if pump responds
            if self._test_wsl_communication():
                self.is_initialized = True
                logging.info(f'WSL pump initialized successfully on {self.port} in {self.distro}')
                return True
            else:
                self.last_error = f"Pump found on {self.port} but not responding in WSL"
                return False
                
        except Exception as e:
            self.last_error = f'Unexpected error during WSL initialization: {e}'
            logging.error(self.last_error)
            return False
    
    def _check_wsl_distro(self) -> bool:
        """Check if the specified WSL distribution is available."""
        try:
            result = subprocess.run([
                "wsl", "-l", "-q"
            ], capture_output=True, text=True, check=False, timeout=10)
            
            if result.returncode != 0:
                self.last_error = "WSL not available or not working"
                return False
            
            available_distros = [line.strip().replace('*', '') for line in result.stdout.strip().split('\n') if line.strip()]
            
            if self.distro not in available_distros:
                self.last_error = f"WSL distribution '{self.distro}' not found. Available: {available_distros}"
                return False
            
            return True
            
        except subprocess.TimeoutExpired:
            self.last_error = "WSL command timed out"
            return False
        except Exception as e:
            self.last_error = f"Error checking WSL: {e}"
            return False
    
    def _find_wsl_pump_port(self) -> Optional[str]:
        """Find available serial ports in WSL."""
        try:
            # Look for serial ports in WSL
            port_cmd = "ls /dev/ttyUSB* /dev/ttyACM* 2>/dev/null || echo 'no_ports'"
            
            result = subprocess.run([
                "wsl", "-d", self.distro, "-e", "bash", "-c", port_cmd
            ], capture_output=True, text=True, check=False, timeout=10)
            
            if result.returncode == 0 and "no_ports" not in result.stdout:
                ports = [line.strip() for line in result.stdout.strip().split('\n') if line.strip()]
                self._available_ports = ports
                if ports:
                    logging.info(f"Found WSL serial ports: {ports}")
                    return ports[0]  # Return first available port
            
            return None
            
        except Exception as e:
            self.last_error = f"Error finding WSL ports: {e}"
            return None
    
    def _test_wsl_communication(self) -> bool:
        """Test if pump responds via WSL."""
        try:
            # Simple test command to see if we can communicate with pump
            test_script = f'''
python3 -c "
import serial, time
try:
    ser = serial.Serial('{self.port}', {self.baudrate}, timeout=2, xonxoff=True)
    ser.write(b'F100\\r')
    ser.flush()
    time.sleep(0.2)
    ser.close()
    print('success')
except Exception as e:
    print(f'error: {{e}}')
"
'''
            
            result = subprocess.run([
                "wsl", "-d", self.distro, "-e", "bash", "-c", test_script
            ], capture_output=True, text=True, check=False, timeout=15)
            
            return result.returncode == 0 and "success" in result.stdout
            
        except Exception as e:
            self.last_error = f"WSL communication test failed: {e}"
            return False
    
    def _run_wsl_command(self, python_code: str) -> bool:
        """Execute Python code in WSL and return success status."""
        try:
            script = f'''
python3 -c "
import serial, time, sys
try:
    ser = serial.Serial('{self.port}', {self.baudrate}, timeout=2, xonxoff=True)
    {python_code}
    ser.close()
    print('success')
except Exception as e:
    print(f'error: {{e}}')
    sys.exit(1)
"
'''
            
            result = subprocess.run([
                "wsl", "-d", self.distro, "-e", "bash", "-c", script
            ], capture_output=True, text=True, check=False, timeout=15)
            
            if result.returncode == 0 and "success" in result.stdout:
                return True
            else:
                self.last_error = f"WSL command failed: {result.stdout}"
                return False
                
        except subprocess.TimeoutExpired:
            self.last_error = "WSL command timed out"
            return False
        except Exception as e:
            self.last_error = f"Error running WSL command: {e}"
            return False
    
    def get_error_details(self) -> str:
        """Get detailed error information."""
        return self.last_error
    
    def get_suggested_fix(self) -> str:
        """Get suggested fix for the last error."""
        if "not found" in self.last_error:
            return "Install WSL distribution or check if it's running"
        elif "No serial ports" in self.last_error:
            return "Run attach_micropump.py as admin to attach USB devices to WSL"
        elif "not responding" in self.last_error:
            return "Check if pump is powered and USB devices are attached to WSL"
        elif "timed out" in self.last_error:
            return "WSL may be slow to start, try again or restart WSL"
        else:
            return "Check WSL status and USB device attachment"
    
    def close(self):
        """Close connection (no persistent connection in WSL mode)."""
        self.is_initialized = False
        logging.info("WSL pump connection closed")
    
    def set_frequency(self, freq: int) -> bool:
        """Set pump frequency in Hz (1-300)."""
        if not (1 <= freq <= 300):
            self.last_error = f"Invalid frequency: {freq} (must be 1-300)"
            return False
        
        python_code = f'''
ser.write(b'F{freq}\\r')
ser.flush()
time.sleep(0.15)
'''
        return self._run_wsl_command(python_code)
    
    def set_voltage(self, voltage: int) -> bool:
        """Set pump voltage/amplitude (1-250 Vpp)."""
        if not (1 <= voltage <= 250):
            self.last_error = f"Invalid voltage: {voltage} (must be 1-250)"
            return False
        
        python_code = f'''
ser.write(b'A{voltage}\\r')
ser.flush()
time.sleep(0.15)
'''
        return self._run_wsl_command(python_code)
    
    def set_waveform(self, waveform: str) -> bool:
        """Set pump waveform (RECT, SINE, etc)."""
        waveform_map = {
            "RECT": "MR",
            "RECTANGLE": "MR", 
            "SINE": "MS",
            "SIN": "MS"
        }
        cmd = waveform_map.get(waveform.upper(), waveform.upper())
        
        python_code = f'''
ser.write(b'{cmd}\\r')
ser.flush()
time.sleep(0.15)
'''
        return self._run_wsl_command(python_code)
    
    def start(self) -> bool:
        """Start the pump."""
        python_code = '''
ser.write(b'bon\\r')
ser.flush()
'''
        result = self._run_wsl_command(python_code)
        if result:
            logging.info("WSL pump started")
        return result
    
    def stop(self) -> bool:
        """Stop the pump."""
        python_code = '''
ser.write(b'boff\\r')
ser.flush()
'''
        result = self._run_wsl_command(python_code)
        if result:
            logging.info("WSL pump stopped")
        return result
    
    def pulse(self, duration: float) -> bool:
        """Run pump for specified duration then stop."""
        python_code = f'''
ser.write(b'bon\\r')
ser.flush()
time.sleep({duration})
ser.write(b'boff\\r')
ser.flush()
'''
        return self._run_wsl_command(python_code)
    
    def test_signal(self, duration: float = 1.0, frequency: int = 100, voltage: int = 100, waveform: str = "RECT") -> bool:
        """Test pump with specified parameters."""
        if not self.is_initialized:
            self.last_error = "Pump not initialized"
            return False
        
        try:
            # Run complete test sequence in one WSL command for efficiency
            waveform_map = {
                "RECT": "MR",
                "RECTANGLE": "MR", 
                "SINE": "MS",
                "SIN": "MS"
            }
            wave_cmd = waveform_map.get(waveform.upper(), waveform.upper())
            
            python_code = f'''
# Configure pump
ser.write(b'F{frequency}\\r')
ser.flush()
time.sleep(0.15)

ser.write(b'A{voltage}\\r')
ser.flush()
time.sleep(0.15)

ser.write(b'{wave_cmd}\\r')
ser.flush()
time.sleep(0.15)

# Run test pulse
ser.write(b'bon\\r')
ser.flush()
time.sleep({duration})
ser.write(b'boff\\r')
ser.flush()
'''
            
            logging.info(f"Starting WSL test pulse: {duration}s, {frequency}Hz, {voltage}Vpp, {waveform}")
            return self._run_wsl_command(python_code)
            
        except Exception as e:
            self.last_error = f"WSL test signal failed: {e}"
            logging.error(self.last_error)
            return False
    
    def get_last_error(self) -> str:
        """Get the last error message."""
        return self.last_error