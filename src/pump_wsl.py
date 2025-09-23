"""WSL-based pump controller - drop-in replacement for Windows pump controller."""

import subprocess
import time
import logging
import os
from pathlib import Path
from typing import Optional, List


class Pump_wsl:
    """WSL pump controller with same interface as Pump_win."""
    
    def __init__(self, port: Optional[str] = None, baudrate: int = 9600):
        self.distro: Optional[str] = None
        self.port = port
        self.baudrate = baudrate
        self.last_error = ""
        self.is_initialized = False
        self._available_ports: List[str] = []
       
    def initialize(self) -> bool:
        """Initialize pump via WSL with comprehensive setup and validation."""
        try:
            # Step 1: Check if WSL is available
            if not self._check_wsl_available():
                print("🔧 WSL not available.")
                print("💡 Please install WSL:")
                print("   1. Open PowerShell as Administrator")
                print("   2. Run: wsl --install")
                print("   3. Restart your computer")
                print("   4. Try again after restart")
                self.last_error = "WSL not installed. Please install WSL manually."
                return False
            
            # Step 2: Load or configure WSL distribution
            if not self._setup_wsl_distribution():
                return False
            
            # Step 3: Find available serial ports in WSL
            if self.port is None:
                self.port = self._find_wsl_pump_port()
                if self.port is None:
                    # Try auto-fix by attaching USB device
                    print("🔧 No serial ports found. Attempting automatic USB device attachment...")
                    if self._auto_fix_usb_attachment():
                        print("🔄 Retrying after USB attachment...")
                        time.sleep(2)  # Give devices time to appear
                        self.port = self._find_wsl_pump_port()
                        if self.port is None:
                            self.last_error = "No serial ports found in WSL even after USB attachment"
                            return False
                    else:
                        self.last_error = "No serial ports found in WSL and auto-fix failed"
                        return False
            
            # Step 4: Test if pump responds
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
    def _setup_wsl_distribution(self) -> bool:
        """Setup WSL distribution - load from .env or help user configure one."""
        # Try to load from .env file
        self.distro = self._load_wsl_distro_from_env()
        
        if self.distro is not None:
            # We have a distro name from .env, check if it's installed
            if self._check_wsl_distro():
                print(f"✅ Using WSL distribution '{self.distro}' from .env file")
                return True
            else:
                print(f"❌ WSL distribution '{self.distro}' from .env file is not installed")
                return self._handle_missing_distro()
        else:
            # No distro in .env file, help user choose one
            return self._handle_missing_distro()
    
    def _handle_missing_distro(self) -> bool:
        """Handle case where WSL distro is missing or not configured."""
        available_distros = self._get_available_distros()
        
        if available_distros:
            print("🔍 Available WSL distributions:")
            for i, distro in enumerate(available_distros, 1):
                print(f"   {i}. {distro}")
            
            print("\n📋 Options:")
            print("   • Choose one of the above distributions")
            print("   • Install a new distribution from Microsoft Store")
            print("\n💡 Recommended distributions:")
            print("   - Debian (lightweight)")
            print("   - Ubuntu 24.04 LTS (popular)")
            print("   - Ubuntu 22.04 LTS (stable)")
            
            # For now, auto-select the first available or suggest Debian
            if "Debian" in available_distros:
                self.distro = "Debian"
                print(f"🔧 Auto-selecting: {self.distro}")
            elif available_distros:
                self.distro = available_distros[0]
                print(f"🔧 Auto-selecting: {self.distro}")
            else:
                print("❌ No WSL distributions found")
                return False
            
            # Save to .env file
            self._save_distro_to_env(self.distro)
            return True
        else:
            print("❌ No WSL distributions installed")
            print("📋 Please install a WSL distribution:")
            print("   1. Open Microsoft Store")
            print("   2. Search for 'Debian' or 'Ubuntu'")
            print("   3. Install and run it once to complete setup")
            self.last_error = "No WSL distributions installed"
            return False
    def _load_wsl_distro_from_env(self) -> Optional[str]:
        """Load WSL distribution name from .env file, with fallback to None."""
        try:
            # Find project root (where .env should be located)
            project_root = Path(__file__).parent.parent
            env_file = project_root / ".env"
            
            if not env_file.exists():
                print(f"⚠️  .env file not found at {env_file}")
                return None
            
            # Read .env file and look for WSL_DISTRO
            with open(env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('WSL_DISTRO=') and not line.startswith('#'):
                        distro = line.split('=', 1)[1].strip().strip('"\'')
                        if distro:
                            return distro
            
            # WSL_DISTRO not found in .env file
            print("⚠️  WSL_DISTRO not found in .env file")
            return None
            
        except Exception as e:
            print(f"⚠️  Error reading .env file: {e}")
            return None
    
    def _get_available_distros(self) -> List[str]:
        """Get list of installed WSL distributions."""
        try:
            result = subprocess.run([
                "wsl", "-l", "-q"
            ], capture_output=True, text=True, check=False, timeout=5)
            
            if result.returncode == 0:
                distros = [line.strip().replace('*', '') for line in result.stdout.strip().split('\n') if line.strip()]
                return [d for d in distros if d]  # Filter out empty strings
            return []
            
        except Exception:
            return []
    
    def _save_distro_to_env(self, distro: str) -> bool:
        """Save WSL distribution name to .env file."""
        try:
            project_root = Path(__file__).parent.parent
            env_file = project_root / ".env"
            
            # Read existing .env content
            existing_lines = []
            if env_file.exists():
                with open(env_file, 'r') as f:
                    existing_lines = f.readlines()
            
            # Update or add WSL_DISTRO line
            wsl_distro_found = False
            for i, line in enumerate(existing_lines):
                if line.strip().startswith('WSL_DISTRO='):
                    existing_lines[i] = f"WSL_DISTRO={distro}\n"
                    wsl_distro_found = True
                    break
            
            if not wsl_distro_found:
                existing_lines.append(f"WSL_DISTRO={distro}\n")
            
            # Write back to file
            with open(env_file, 'w') as f:
                f.writelines(existing_lines)
            
            print(f"✅ Saved WSL_DISTRO={distro} to .env file")
            return True
            
        except Exception as e:
            print(f"⚠️  Failed to save to .env file: {e}")
            return False
         
    def _check_wsl_available(self) -> bool:
        """Check if WSL is installed and working at all."""
        try:
            # Use --status for fast WSL availability check
            result = subprocess.run([
                "wsl", "--status"
            ], capture_output=True, text=True, check=False, timeout=5)
            
            if result.returncode != 0:
                self.last_error = "WSL is not installed or not working"
                print("❌ WSL not available")
                return False
            
            print("✅ WSL is available")
            return True
            
        except subprocess.TimeoutExpired:
            self.last_error = "WSL status check timed out"
            print("❌ WSL status check timed out")
            return False
        except Exception as e:
            self.last_error = f"Error checking WSL availability: {e}"
            print(f"❌ WSL check failed: {e}")
            return False
    
    def _check_wsl_distro(self) -> bool:
        """Check if the specified WSL distribution is available."""
        if self.distro is None:
            return False
            
        try:
            result = subprocess.run([
                "wsl", "-l", "-q"
            ], capture_output=True, text=True, check=False, timeout=5)
            
            if result.returncode != 0:
                self.last_error = "WSL not available or not working"
                return False
            
            available_distros = [line.strip().replace('*', '') for line in result.stdout.strip().split('\n') if line.strip()]
            
            if self.distro not in available_distros:
                self.last_error = f"WSL distribution '{self.distro}' not found. Available: {available_distros}"
                return False
            
            return True
            
        except subprocess.TimeoutExpired:
            self.last_error = "WSL distribution check timed out"
            return False
        except Exception as e:
            self.last_error = f"Error checking WSL distribution: {e}"
            return False
    
    def _find_wsl_pump_port(self) -> Optional[str]:
        """Find available serial ports in WSL."""
        if self.distro is None:
            self.last_error = "No WSL distribution configured"
            return None
            
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
    
    def _auto_fix_usb_attachment(self) -> bool:
        """Attempt to automatically attach USB devices to WSL using admin tools."""
        if self.distro is None:
            self.last_error = "No WSL distribution configured"
            return False
            
        try:
            # Find the project root and admin batch file
            project_root = Path(__file__).parent.parent
            admin_batch = project_root / "via_wsl" / "run_as_admin.bat"
            attach_script = project_root / "via_wsl" / "attach_micropump.py"
            
            if not admin_batch.exists():
                print(f"❌ Admin batch file not found: {admin_batch}")
                return False
            
            if not attach_script.exists():
                print(f"❌ Attach script not found: {attach_script}")
                return False
            
            print("🔒 Running USB attachment as admin (you may see a UAC prompt)...")
            
            # Run attach_micropump.py via the admin batch file with current distro
            result = subprocess.run([
                str(admin_batch), "attach_micropump.py", "--distro", self.distro
            ], cwd=admin_batch.parent, check=False, timeout=120)  # 2 minute timeout
            
            if result.returncode == 0:
                print("✅ USB attachment completed successfully")
                return True
            else:
                print(f"⚠️  USB attachment completed with exit code: {result.returncode}")
                # Even non-zero exit codes might have partially worked
                return True
                
        except subprocess.TimeoutExpired:
            print("❌ USB attachment timed out")
            return False
        except Exception as e:
            print(f"❌ Failed to run USB attachment: {e}")
            return False
    
    def _test_wsl_communication(self) -> bool:
        """Test if pump responds via WSL."""
        if self.distro is None or self.port is None:
            self.last_error = "WSL distribution or port not configured"
            return False
            
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
        if self.distro is None or self.port is None:
            self.last_error = "WSL distribution or port not configured"
            return False
            
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
        if "not installed" in self.last_error or "WSL not available" in self.last_error:
            return "Install WSL: Open PowerShell as Admin → Run 'wsl --install' → Restart computer"
        elif "not found" in self.last_error or "Microsoft Store" in self.last_error:
            return "Install WSL distribution: Open Microsoft Store → Search 'Debian' or 'Ubuntu' → Install → Run once to setup"
        elif "No serial ports" in self.last_error:
            return "USB device auto-attachment attempted. Check if pump is connected and powered"
        elif "not responding" in self.last_error:
            return "Check if pump is powered and USB devices are attached to WSL"
        elif "timed out" in self.last_error:
            return "Operation timed out, try again or restart WSL"
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
    
    # Legacy method aliases for compatibility
    def bartels_set_freq(self, freq: int) -> bool:
        """Legacy alias for set_frequency."""
        return self.set_frequency(freq)
    
    def bartels_set_voltage(self, voltage: int) -> bool:
        """Legacy alias for set_voltage."""
        return self.set_voltage(voltage)
    
    def bartels_set_waveform(self, waveform: str) -> bool:
        """Legacy alias for set_waveform."""
        return self.set_waveform(waveform)
    
    def bartels_start(self) -> bool:
        """Legacy alias for start."""
        return self.start()
    
    def bartels_stop(self) -> bool:
        """Legacy alias for stop."""
        return self.stop()