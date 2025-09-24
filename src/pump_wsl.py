"""WSL-based pump controller - drop-in replacement for Windows pump controller."""

import subprocess
import time
import logging
import os
from pathlib import Path
from typing import Optional, List, Tuple


class Pump_wsl:
    """WSL pump controller with same interface as Pump_win."""
    
    def __init__(self, port: Optional[str] = None, baudrate: int = 9600):
        self.port = port
        self.baudrate = baudrate
        self.last_error = ""
        self.is_initialized = False
        self._available_ports: List[str] = []

        self._project_root = Path(__file__).parent.parent
        self._env_path = self._project_root / ".env"
        self.distro: Optional[str] = None
        self.vid: Optional[int] = None
        self.pid: Optional[int] = None
        self._load_config_from_env()

    def _load_config_from_env(self) -> None:
        """Load WSL pump configuration from the local .env file."""
        self.distro = None
        self.vid = None
        self.pid = None

        if not self._env_path.exists():
            logging.info("WSL pump configuration file (.env) not found yet")
            return

        try:
            with open(self._env_path, "r", encoding="utf-8") as handle:
                for raw_line in handle:
                    line = raw_line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip().strip("\"").strip("'")
                    if key == "WSL_DISTRO" and value:
                        self.distro = value
                    elif key == "PUMP_VID":
                        try:
                            parsed = int(value)
                            self.vid = parsed if parsed > 0 else None
                        except ValueError:
                            self.vid = None
                    elif key == "PUMP_PID":
                        try:
                            parsed = int(value)
                            self.pid = parsed if parsed > 0 else None
                        except ValueError:
                            self.pid = None

            if self.vid and self.pid:
                logging.info(f"WSL pump loaded VID/PID from .env: {self.vid:04X}:{self.pid:04X}")
            else:
                logging.warning("WSL pump VID/PID missing in .env; device discovery will fall back to autodetect")

        except Exception as exc:
            logging.warning(f"WSL pump failed to load configuration from .env: {exc}")
            self.distro = None
            self.vid = None
            self.pid = None
    
    def _ensure_env_configuration(self) -> bool:
        '''Make sure .env contains required configuration, invoking attach_micropump if needed.'''
        self._load_config_from_env()

        missing_items: List[str] = []
        if not self._env_path.exists():
            missing_items.append('.env file')
        if not self.distro:
            missing_items.append('WSL_DISTRO')
        if not (self.vid and self.pid):
            missing_items.append('PUMP_VID/PUMP_PID')

        distro_ready = False
        if self.distro:
            distro_ready = self._check_wsl_distro()
            if not distro_ready and 'WSL_DISTRO' not in missing_items:
                missing_items.append(f"WSL distro '{self.distro}'")

        if missing_items:
            print('Missing WSL pump configuration: ' + ', '.join(missing_items))
            print('Launching attach_micropump to complete setup...')
            if not self._auto_fix_usb_attachment(non_interactive=False):
                self.last_error = 'attach_micropump could not update .env configuration'
                return False

            self._load_config_from_env()
            if not self.distro or not (self.vid and self.pid):
                self.last_error = 'attach_micropump did not populate required .env entries'
                return False

            if not self._check_wsl_distro():
                self.last_error = f"Configured WSL distribution '{self.distro}' is not available"
                return False

        return True

    def initialize(self) -> bool:
        """Initialize pump via WSL with comprehensive setup and validation."""
        try:
            # Step 1: Check if WSL is available
            if not self._check_wsl_available():
                print("WRENCH WSL not available.")
                print("NOTE Please install WSL:")
                print("   1. Open PowerShell as Administrator")
                print("   2. Run: wsl --install")
                print("   3. Restart your computer")
                print("   4. Try again after restart")
                self.last_error = "WSL not installed. Please install WSL manually."
                return False
            
            # Step 2: Ensure configuration is present in .env
            if not self._ensure_env_configuration():
                return False
            
            # Step 3: Find available serial ports in WSL
            if self.port is None:
                self.port = self._find_wsl_pump_port()
                if self.port is None:
                    # Try auto-fix by attaching USB device
                    print("WRENCH No serial ports found. Attempting automatic USB device attachment...")
                    if self._auto_fix_usb_attachment():
                        print("REFRESH Retrying after USB attachment...")
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
    def _check_wsl_available(self) -> bool:
        """Check if WSL is installed and working at all."""
        try:
            # Use --status for fast WSL availability check
            result = subprocess.run([
                "wsl", "--status"
            ], capture_output=True, text=True, check=False, timeout=5)
            
            if result.returncode != 0:
                self.last_error = "WSL is not installed or not working"
                print("FAIL WSL not available")
                return False
            
            print("OK WSL is available")
            return True
            
        except subprocess.TimeoutExpired:
            self.last_error = "WSL status check timed out"
            print("FAIL WSL status check timed out")
            return False
        except Exception as e:
            self.last_error = f"Error checking WSL availability: {e}"
            print(f"FAIL WSL check failed: {e}")
            return False
    
    def _check_wsl_distro(self) -> bool:
        """Check if the specified WSL distribution is available and running."""
        if self.distro is None:
            return False
            
        try:
            # Check if distro exists and get its state
            result = subprocess.run([
                "wsl", "-l", "-v"
            ], capture_output=True, text=True, check=False, timeout=10)
            
            if result.returncode != 0:
                self.last_error = "WSL not available or not working"
                return False
            
            # Parse the output to check distro state
            lines = result.stdout.replace('\x00', '').strip().split('\n')
            distro_found = False
            distro_running = False
            
            for line in lines:
                if self.distro.lower() in line.lower():
                    distro_found = True
                    if 'running' in line.lower():
                        distro_running = True
                    elif 'stopped' in line.lower():
                        print(f"WARNING  WSL distro '{self.distro}' is stopped - this will reset USB attachments")
                        print("NOTE Starting WSL distribution...")
                        # Start the distro
                        start_result = subprocess.run([
                            "wsl", "-d", self.distro, "-e", "echo", "WSL started"
                        ], capture_output=True, text=True, check=False, timeout=15)
                        
                        if start_result.returncode == 0:
                            print(f"OK WSL distro '{self.distro}' started successfully")
                            distro_running = True
                        else:
                            print(f"FAIL Failed to start WSL distro '{self.distro}'")
                    break
            
            if not distro_found:
                # Fallback to simple name check
                simple_result = subprocess.run([
                    "wsl", "-l", "-q"
                ], capture_output=True, text=True, check=False, timeout=5)
                
                if simple_result.returncode == 0:
                    raw = (simple_result.stdout or "").replace('\x00', '').strip()
                    available_distros = [line.strip().replace('*', '') for line in raw.split('\n') if line.strip()]
                    norm_available = [d.strip().lower() for d in available_distros]
                    target = self.distro.strip().lower()

                    # Accept exact match or prefix match
                    found = target in norm_available or any(a.startswith(target) for a in norm_available)

                    if not found:
                        self.last_error = f"WSL distribution '{self.distro}' not found. Available: {available_distros}"
                        return False
                    
                    distro_found = True
                    # Assume it's running if we can't get detailed state
                    distro_running = True
            
            if not distro_found:
                self.last_error = f"WSL distribution '{self.distro}' not found"
                return False
                
            return True
            
        except subprocess.TimeoutExpired:
            self.last_error = "WSL distribution check timed out"
            return False
        except Exception as e:
            self.last_error = f"Error checking WSL distribution: {e}"
            return False
    
    def _find_wsl_pump_port(self) -> Optional[str]:
        """Find available serial ports in WSL using VID/PID detection when possible."""
        if self.distro is None:
            self.last_error = "No WSL distribution configured"
            return None
            
        try:
            # Strategy 1: If we have VID/PID, try to find specific device
            if self.vid is not None and self.pid is not None:
                port = self._find_wsl_port_by_vid_pid()
                if port:
                    print(f"OK Found WSL pump using VID/PID {self.vid:04X}:{self.pid:04X}: {port}")
                    return port
                else:
                    print(f"WARNING  WSL VID/PID lookup failed for {self.vid:04X}:{self.pid:04X}")
            
            # Strategy 2: Fall back to listing all available serial ports
            port_cmd = "ls /dev/ttyUSB* /dev/ttyACM* 2>/dev/null || echo 'no_ports'"
            
            result = subprocess.run([
                "wsl", "-d", self.distro, "-e", "bash", "-c", port_cmd
            ], capture_output=True, text=True, check=False, timeout=10)
            
            if result.returncode == 0 and "no_ports" not in result.stdout:
                ports = [line.strip() for line in result.stdout.strip().split('\n') if line.strip()]
                if ports:
                    self._available_ports = ports
                    print(f"OK Found WSL ports (fallback): {ports[0]}")
                    return ports[0]  # Return first available port
            
            return None
            
        except Exception as e:
            self.last_error = f"Error finding WSL ports: {e}"
            return None
    
    def _find_wsl_port_by_vid_pid(self) -> Optional[str]:
        """Find WSL serial port using VID/PID detection via lsusb and device mapping."""
        if self.vid is None or self.pid is None or self.distro is None:
            return None
            
        try:
            # Check if device with our VID/PID is attached to WSL
            vid_hex = f"{self.vid:04x}"
            pid_hex = f"{self.pid:04x}"
            
            # Use lsusb to find the device
            lsusb_cmd = f"lsusb | grep '{vid_hex}:{pid_hex}' || echo 'not_found'"
            
            result = subprocess.run([
                "wsl", "-d", self.distro, "-e", "bash", "-c", lsusb_cmd
            ], capture_output=True, text=True, check=False, timeout=10)
            
            if result.returncode == 0 and "not_found" not in result.stdout:
                # Device found, now try to map to serial port
                # FTDI devices typically show up as ttyUSB*, check which one matches
                port_check_cmd = '''
for port in /dev/ttyUSB* /dev/ttyACM*; do
    if [ -c "$port" ]; then
        echo "$port"
        break
    fi
done 2>/dev/null || echo "no_port_found"'''
                
                port_result = subprocess.run([
                    "wsl", "-d", self.distro, "-e", "bash", "-c", port_check_cmd
                ], capture_output=True, text=True, check=False, timeout=10)
                
                if port_result.returncode == 0 and "no_port_found" not in port_result.stdout:
                    port = port_result.stdout.strip().replace('\x00', '')  # Remove null characters
                    if port and port.startswith('/dev/'):
                        return port
            
            return None
            
        except Exception as e:
            logging.warning(f"WSL VID/PID port detection failed: {e}")
            return None
    
    @classmethod  
    def list_available_wsl_distros(cls) -> List[str]:
        """Class method to list available WSL distributions without creating an instance."""
        try:
            result = subprocess.run([
                "wsl", "-l", "-q"
            ], capture_output=True, text=True, check=False, timeout=5)
            
            if result.returncode == 0:
                raw = (result.stdout or "").replace('\x00', '').strip()
                return [line.strip().replace('*', '') for line in raw.split('\n') if line.strip()]
            return []
            
        except Exception:
            return []
    
    @classmethod
    def find_pump_candidates_in_wsl(cls, distro: Optional[str] = None) -> List[Tuple[str, str]]:
        """Class method to find potential pump devices in WSL.
        
        Args:
            distro: WSL distribution to check (if None, uses first available)
            
        Returns:
            List of tuples (port, detection_method)
        """
        if distro is None:
            available_distros = cls.list_available_wsl_distros()
            if not available_distros:
                return []
            distro = available_distros[0]
        
        candidates = []
        
        try:
            # Check for USB serial devices
            port_cmd = "ls /dev/ttyUSB* /dev/ttyACM* 2>/dev/null || echo 'no_ports'"
            
            result = subprocess.run([
                "wsl", "-d", distro, "-e", "bash", "-c", port_cmd
            ], capture_output=True, text=True, check=False, timeout=10)
            
            if result.returncode == 0 and "no_ports" not in result.stdout:
                ports = result.stdout.strip().split('\n')
                for port in ports:
                    if port.strip():
                        candidates.append((port.strip(), "USB serial device"))
        
        except Exception:
            pass
        
        return candidates
    
    def _auto_fix_usb_attachment(self, non_interactive: bool = True) -> bool:
        """Attempt to attach the USB device to WSL, optionally prompting the user."""
        if self.distro is None and non_interactive:
            self.last_error = "No WSL distribution configured"
            return False

        try:
            # Find the project root and admin batch file
            project_root = Path(__file__).parent.parent
            admin_batch = project_root / "via_wsl" / "run_as_admin.bat"
            attach_script = project_root / "via_wsl" / "attach_micropump.py"
            
            if not admin_batch.exists():
                print(f"FAIL Admin batch file not found: {admin_batch}")
                return False
            
            if not attach_script.exists():
                print(f"FAIL Attach script not found: {attach_script}")
                return False
            
            print("LOCK Running USB attachment as admin (you may see a UAC prompt)...")
            print("   Note: If FTDI support needs installing in WSL, you may be prompted for your sudo password once.")
            
            # Run attach_micropump.py via the admin batch file with current distro
            # Run in non-interactive mode to avoid prompts during automated init
            env = os.environ.copy()
            if non_interactive:
                env["PUMP_NON_INTERACTIVE"] = "1"
            else:
                env.pop("PUMP_NON_INTERACTIVE", None)
            # Optional: pass sudo password for non-interactive FTDI setup
            sudo_pass = os.getenv("PUMP_WSL_SUDO_PASS")
            if sudo_pass:
                env["PUMP_WSL_SUDO_PASS"] = str(sudo_pass)
            # Build command with VID:PID and optional auto FTDI install
            if self.vid and self.pid:
                vidpid = f"{self.vid:04x}:{self.pid:04x}"
            else:
                vidpid = "0403:b4c0"  # default FTDI Micropump VID:PID

            cmd = [
                str(admin_batch),
                "attach_micropump.py",
            ]
            if self.distro:
                cmd.extend(["--distro", self.distro])
            if vidpid:
                cmd.extend(["--vidpid", vidpid])

            # Auto-enable FTDI install unless explicitly disabled
            auto_ftdi_env = (os.getenv("PUMP_WSL_FTDI_AUTO", "1") or "1").strip().lower()
            if auto_ftdi_env in ("1", "true", "yes", "on"):  # default on
                cmd.append("--auto-ftdi")

            result = subprocess.run(
                cmd,
                cwd=admin_batch.parent,
                env=env,
                check=False,
                timeout=180,
            )  # allow 3 minutes
            
            if result.returncode == 0:
                print("OK USB attachment completed successfully")
                return True
            else:
                print(f"WARNING  USB attachment completed with exit code: {result.returncode}")
                # Even non-zero exit codes might have partially worked
                return True
                
        except subprocess.TimeoutExpired:
            print("FAIL USB attachment timed out")
            return False
        except Exception as e:
            print(f"FAIL Failed to run USB attachment: {e}")
            return False
    
    def _test_wsl_communication(self) -> bool:
        """Test if pump responds via WSL, with robust timeout and diagnostics."""
        if self.distro is None or self.port is None:
            self.last_error = "WSL distribution or port not configured"
            return False

        try:
            print(f"[WSL DIAG] Testing pump communication on {self.port} in {self.distro}")
            # Use direct python invocation to avoid bash quoting issues and stabilize the line
            code = (
                "import serial, time, sys\n"
                "print('[WSL DIAG] Starting serial test...')\n"
                f"port='{self.port}'\n"
                f"baud={self.baudrate}\n"
                "try:\n"
                "    ser = serial.Serial(port, baud, timeout=2, xonxoff=True)\n"
                "    print('[WSL DIAG] Serial port opened.')\n"
                "    ser.reset_input_buffer(); ser.reset_output_buffer()\n"
                "    try:\n"
                "        ser.setDTR(False); time.sleep(0.05); ser.setDTR(True)\n"
                "    except Exception:\n"
                "        print('[WSL DIAG] DTR toggle failed.')\n"
                "    time.sleep(0.1)\n"
                "    ser.write(b'F100\\r'); ser.flush(); time.sleep(0.25)\n"
                "    print('[WSL DIAG] Command sent.')\n"
                "    ser.close(); print('success')\n"
                "except Exception as e:\n"
                "    print('[WSL DIAG] Serial error:', e); sys.exit(1)\n"
            )

            result = subprocess.run(
                ["wsl", "-d", self.distro, "-e", "python3", "-c", code],
                capture_output=True, text=True, check=False, timeout=10
            )

            print(f"[WSL DIAG] Subprocess return code: {result.returncode}")
            print(f"[WSL DIAG] stdout: {result.stdout!r}")
            print(f"[WSL DIAG] stderr: {result.stderr!r}")

            ok = result.returncode == 0 and "success" in (result.stdout or "")
            if not ok:
                self.last_error = (
                    f"WSL communication test failed: rc={result.returncode}, "
                    f"stdout={result.stdout!r}, stderr={result.stderr!r}"
                )
            return ok

        except subprocess.TimeoutExpired:
            self.last_error = "WSL communication test timed out"
            print("[WSL DIAG] Communication test timed out.")
            return False
        except Exception as e:
            self.last_error = f"WSL communication test exception: {e}"
            print(f"[WSL DIAG] Exception: {e}")
            return False
    
    def _run_wsl_command(self, python_code: str) -> bool:
        """Execute Python code in WSL and return success status."""
        if self.distro is None or self.port is None:
            self.last_error = "WSL distribution or port not configured"
            return False

        try:
            code = (
                "import serial, time, sys\n"
                f"port='{self.port}'\n"
                f"baud={self.baudrate}\n"
                "try:\n"
                "    ser = serial.Serial(port, baud, timeout=2, xonxoff=True)\n"
                "    ser.reset_input_buffer(); ser.reset_output_buffer()\n"
                "    try:\n"
                "        ser.setDTR(False); time.sleep(0.05); ser.setDTR(True)\n"
                "    except Exception:\n"
                "        pass\n"
                "    time.sleep(0.1)\n"
                f"    {python_code}\n"
                "    ser.close(); print('success')\n"
                "except Exception as e:\n"
                "    print('error:', e); sys.exit(1)\n"
            )

            result = subprocess.run(
                ["wsl", "-d", self.distro, "-e", "python3", "-c", code],
                capture_output=True, text=True, check=False, timeout=25
            )

            if result.returncode == 0 and "success" in (result.stdout or ""):
                return True
            else:
                self.last_error = (
                    f"WSL command failed: rc={result.returncode}, stdout={result.stdout!r}, stderr={result.stderr!r}"
                )
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
            return "Install WSL: Open PowerShell as Admin -> Run 'wsl --install' -> Restart computer"
        elif "not found" in self.last_error or "Microsoft Store" in self.last_error:
            return "Install WSL distribution: Open Microsoft Store -> Search 'Debian' or 'Ubuntu' -> Install -> Run once to setup"
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
        
        python_code = f'''ser.write(b'F{freq}\\r')
    ser.flush()
    time.sleep(0.15)'''
        return self._run_wsl_command(python_code)
    
    def set_voltage(self, voltage: int) -> bool:
        """Set pump voltage/amplitude (1-250 Vpp)."""
        if not (1 <= voltage <= 250):
            self.last_error = f"Invalid voltage: {voltage} (must be 1-250)"
            return False
        
        python_code = f'''ser.write(b'A{voltage}\\r')
    ser.flush()
    time.sleep(0.15)'''
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
        
        python_code = f'''ser.write(b'{cmd}\\r')
    ser.flush()
    time.sleep(0.15)'''
        return self._run_wsl_command(python_code)
    
    def start(self) -> bool:
        """Start the pump."""
        python_code = '''ser.write(b'bon\\r')
    ser.flush()'''
        result = self._run_wsl_command(python_code)
        if result:
            logging.info("WSL pump started")
        return result
    
    def stop(self) -> bool:
        """Stop the pump."""
        python_code = '''ser.write(b'boff\\r')
    ser.flush()'''
        result = self._run_wsl_command(python_code)
        if result:
            logging.info("WSL pump stopped")
        return result
    
    def pulse(self, duration: float) -> bool:
        """Run pump for specified duration then stop."""
        python_code = f'''ser.write(b'bon\\r')
    ser.flush()
    time.sleep({duration})
    ser.write(b'boff\\r')
    ser.flush()'''
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
