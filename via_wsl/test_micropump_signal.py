#!/usr/bin/env python3
"""
Test micropump signal script for WSL environment.
Checks if micropump is available, installs if needed, then sends test pulse.
"""

import argparse
import os
import subprocess
import sys
import time
import tempfile
from pathlib import Path

# Import functionality from existing scripts
script_dir = Path(__file__).parent
attach_script = script_dir / "attach_micropump.py"

def run_cmd(cmd, check=True, capture_output=True):
    """Run a command and return the result."""
    print(f">>> {' '.join(cmd) if isinstance(cmd, list) else cmd}")
    if isinstance(cmd, str):
        cmd = cmd.split()
    return subprocess.run(cmd, check=check, capture_output=capture_output, text=True)

def check_wsl_distro_exists(distro: str):
    """Check if WSL distribution exists."""
    try:
        result = run_cmd(["wsl", "-d", distro, "-e", "true"], check=False)
        if result.returncode != 0:
            error_output = result.stderr + result.stdout
            error_output = error_output.replace('\x00', '')
            if "WSL_E_DISTRO_NOT_FOUND" in error_output or "no distribution" in error_output:
                return False
        return True
    except Exception:
        return False

def check_micropump_in_wsl(distro: str):
    """Check if micropump (serial devices) are available in WSL."""
    try:
        # Check for serial devices
        result = run_cmd([
            "wsl", "-d", distro, "-e", "bash", "-c", 
            "ls /dev/ttyUSB* /dev/ttyACM* 2>/dev/null | wc -l"
        ], check=False)
        
        if result.returncode == 0:
            device_count = int(result.stdout.strip()) if result.stdout.strip().isdigit() else 0
            
            if device_count > 0:
                # Also check for FTDI device specifically
                usb_check = run_cmd([
                    "wsl", "-d", distro, "-e", "bash", "-c",
                    "lsusb | grep -i '0403:' || echo 'NO_FTDI_FOUND'"
                ], check=False)
                
                if "NO_FTDI_FOUND" not in usb_check.stdout:
                    print(f"✅ Found {device_count} serial device(s) in WSL")
                    print(f"✅ FTDI device detected: {usb_check.stdout.strip()}")
                    return True
                else:
                    print(f"⚠️  Found {device_count} serial device(s) but no FTDI device")
                    return False
            else:
                print("❌ No serial devices found in WSL")
                return False
        else:
            print("❌ Failed to check for serial devices in WSL")
            return False
            
    except Exception as e:
        print(f"❌ Error checking micropump in WSL: {e}")
        return False

def attach_micropump_to_wsl(distro: str):
    """Use attach_micropump.py to attach the micropump to WSL."""
    print(f"🔄 Attaching micropump to WSL distribution '{distro}'...")
    
    if not attach_script.exists():
        print(f"❌ Attach script not found: {attach_script}")
        return False
    
    try:
        # Run the attach script
        result = run_cmd([
            "python", str(attach_script), 
            "--distro", distro,
            "--vidpid", "0403:b4c0",
            "--name-hint", "Micropump"
        ], check=False, capture_output=False)
        
        if result.returncode == 0:
            print("✅ Micropump attached successfully")
            # Wait a moment for devices to be recognized
            time.sleep(3)
            return True
        else:
            print(f"❌ Failed to attach micropump (exit code: {result.returncode})")
            return False
            
    except Exception as e:
        print(f"❌ Error running attach script: {e}")
        return False

def create_wsl_pump_controller():
    """Create a pump controller script for WSL environment."""
    pump_script = '''
import time
import serial
import sys
import glob
import os

class WSLPumpController:
    """Bartels micropump controller for WSL environment."""
    
    def __init__(self, port=None, baudrate=9600):
        self.baudrate = baudrate
        self.ser = None
        self.port = port or self._find_serial_port()
        
        if self.port:
            self._initialize()
        else:
            raise Exception("No serial port found for micropump")
    
    def _find_serial_port(self):
        """Find available serial ports."""
        ports = []
        # Check common serial device paths
        for pattern in ['/dev/ttyUSB*', '/dev/ttyACM*']:
            ports.extend(glob.glob(pattern))
        
        if ports:
            print(f"Found serial ports: {ports}")
            return ports[0]  # Use first available port
        return None
    
    def _initialize(self):
        """Initialize serial connection to pump."""
        try:
            self.ser = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=2,
                xonxoff=True  # XON/XOFF flow control for Bartels
            )
            print(f'Pump connection established on {self.port}')
        except serial.SerialException as e:
            print(f'No pump found on {self.port}: {e}')
            self.ser = None
            raise
    
    def close(self):
        """Close serial connection."""
        if self.ser is not None:
            try:
                self.ser.close()
                print("Pump connection closed")
            except Exception:
                pass
    
    def _send_command(self, command):
        """Send command to pump with carriage return terminator."""
        if self.ser is None:
            print("Pump is not initialized.")
            return False
        try:
            full_command = command + "\\r"
            self.ser.write(full_command.encode("utf-8"))
            self.ser.flush()
            print(f"Sent command: '{command}'")
            return True
        except Exception as e:
            print(f"Failed to send command '{command}': {e}")
            return False
    
    def set_frequency(self, freq):
        """Set pump frequency in Hz (1-300)."""
        if 1 <= freq <= 300:
            self._send_command(f"F{freq}")
            time.sleep(0.15)
            return True
        else:
            print(f"Invalid frequency: {freq} (must be 1-300)")
            return False
    
    def set_voltage(self, voltage):
        """Set pump voltage/amplitude (1-250 Vpp).""" 
        if 1 <= voltage <= 250:
            self._send_command(f"A{voltage}")
            time.sleep(0.15)
            return True
        else:
            print(f"Invalid voltage: {voltage} (must be 1-250)")
            return False
    
    def set_waveform(self, waveform):
        """Set pump waveform (RECT, SINE, etc)."""
        waveform_map = {
            "RECT": "MR",
            "RECTANGLE": "MR", 
            "SINE": "MS",
            "SIN": "MS"
        }
        cmd = waveform_map.get(waveform.upper(), waveform.upper())
        self._send_command(cmd)
        time.sleep(0.15)
        return True
    
    def start(self):
        """Start the pump."""
        self._send_command("bon")
        print("Pump started")
        return True
    
    def stop(self):
        """Stop the pump.""" 
        self._send_command("boff")
        print("Pump stopped")
        return True
    
    def test_pulse(self, duration=1.0, frequency=100, voltage=100, waveform="RECT"):
        """Send a test pulse with specified parameters."""
        print(f"Sending test pulse: {duration}s, {frequency}Hz, {voltage}Vpp, {waveform}")
        
        try:
            # Configure pump
            if not self.set_frequency(frequency):
                return False
            if not self.set_voltage(voltage):
                return False
            if not self.set_waveform(waveform):
                return False
            
            # Send pulse
            self.start()
            time.sleep(duration)
            self.stop()
            
            print("✅ Test pulse completed successfully")
            return True
            
        except Exception as e:
            print(f"❌ Error during test pulse: {e}")
            self.stop()  # Ensure pump is stopped
            return False

def main():
    """Main function to run the test."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test micropump with configurable parameters")
    parser.add_argument("--duration", type=float, default=1.0, help="Pulse duration in seconds")
    parser.add_argument("--frequency", type=int, default=100, help="Frequency in Hz")
    parser.add_argument("--voltage", type=int, default=100, help="Voltage in Vpp")
    parser.add_argument("--waveform", default="RECT", help="Waveform type")
    parser.add_argument("--port", help="Serial port (auto-detect if not specified)")
    
    args = parser.parse_args()
    
    print("=== WSL Micropump Test ===")
    
    try:
        # Check if pyserial is available
        try:
            import serial
        except ImportError:
            print("Installing pyserial...")
            os.system("pip3 install pyserial")
            import serial
        
        # Create pump controller
        pump = WSLPumpController(port=args.port)
        
        # Run test pulse
        success = pump.test_pulse(
            duration=args.duration,
            frequency=args.frequency,
            voltage=args.voltage,
            waveform=args.waveform
        )
        
        # Cleanup
        pump.close()
        
        if success:
            print("\\n✅ Micropump test completed successfully!")
            sys.exit(0)
        else:
            print("\\n❌ Micropump test failed!")
            sys.exit(1)
            
    except Exception as e:
        print(f"\\n❌ Micropump test error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
'''
    return pump_script

def run_wsl_test(distro: str, duration=1.0, frequency=100, voltage=100, waveform="RECT"):
    """Run the micropump test in WSL."""
    print(f"🧪 Running micropump test in WSL ({duration}s, {frequency}Hz, {voltage}Vpp, {waveform})")
    
    # Create the pump controller script
    pump_script_content = create_wsl_pump_controller()
    
    # Create a temporary file in WSL and ensure permissions
    try:
        # Write the script to a temporary location and run it with proper permissions
        script_command = f'''
# Check if pyserial is installed
python3 -c "import serial" 2>/dev/null || {{
    echo "Installing pyserial..."
    pip3 install pyserial --user
}}

# Try to fix permissions if possible (non-interactive)
echo "Checking serial port permissions..."
if sudo -n chmod 666 /dev/ttyUSB* /dev/ttyACM* 2>/dev/null; then
    echo "Serial port permissions updated"
else
    echo "Note: Could not update permissions automatically. If connection fails, you may need to run:"
    echo "  sudo chmod 666 /dev/ttyUSB* /dev/ttyACM*"
fi

cat > /tmp/wsl_pump_test.py << 'EOF'
{pump_script_content}
EOF

python3 /tmp/wsl_pump_test.py --duration {duration} --frequency {frequency} --voltage {voltage} --waveform {waveform}
'''
        
        result = run_cmd([
            "wsl", "-d", distro, "-e", "bash", "-c", script_command
        ], check=False, capture_output=False)
        
        if result.returncode == 0:
            print("✅ WSL micropump test completed successfully!")
            return True
        else:
            print(f"❌ WSL micropump test failed (exit code: {result.returncode})")
            return False
            
    except Exception as e:
        print(f"❌ Error running WSL test: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Test micropump signal - check WSL availability, attach if needed, send test pulse")
    parser.add_argument("--distro", default="Ubuntu", help="WSL distro name (default: Ubuntu)")
    parser.add_argument("--duration", type=float, default=1.0, help="Test pulse duration in seconds (default: 1.0)")
    parser.add_argument("--frequency", type=int, default=100, help="Frequency in Hz (default: 100)")
    parser.add_argument("--voltage", type=int, default=100, help="Voltage in Vpp (default: 100)")
    parser.add_argument("--waveform", default="RECT", help="Waveform type (default: RECT)")
    parser.add_argument("--force-attach", action="store_true", help="Force reattachment even if devices are found")
    parser.add_argument("--skip-attach", action="store_true", help="Skip attachment step and assume device is ready")
    
    args = parser.parse_args()
    
    print("🔬 Micropump Signal Test Tool")
    print("=" * 50)
    print(f"Target: WSL distribution '{args.distro}'")
    print(f"Test parameters: {args.duration}s, {args.frequency}Hz, {args.voltage}Vpp, {args.waveform}")
    print("=" * 50)
    
    # Step 1: Check if WSL distro exists
    print("\\n📋 Step 1: Checking WSL distribution...")
    if not check_wsl_distro_exists(args.distro):
        print(f"❌ WSL distribution '{args.distro}' not found!")
        print("Available distributions:")
        try:
            result = run_cmd(["wsl", "-l", "-q"], check=False)
            if result.returncode == 0:
                print(result.stdout.strip())
            else:
                print("Could not list WSL distributions.")
        except Exception:
            print("Could not list WSL distributions.")
        sys.exit(1)
    
    print(f"✅ WSL distribution '{args.distro}' is available")
    
    # Step 2: Check if micropump is available in WSL
    micropump_available = False
    if not args.skip_attach:
        print("\\n🔍 Step 2: Checking for micropump in WSL...")
        micropump_available = check_micropump_in_wsl(args.distro)
        
        if not micropump_available or args.force_attach:
            if args.force_attach:
                print("🔄 Force attachment requested...")
            print("\\n📦 Step 3: Attaching micropump to WSL...")
            if not attach_micropump_to_wsl(args.distro):
                print("❌ Failed to attach micropump to WSL!")
                sys.exit(1)
            
            # Recheck after attachment
            print("\\n🔍 Rechecking micropump availability...")
            micropump_available = check_micropump_in_wsl(args.distro)
            if not micropump_available:
                print("❌ Micropump still not available after attachment!")
                sys.exit(1)
        else:
            print("✅ Micropump is already available in WSL")
    else:
        print("\\n⏭️  Step 2: Skipping attachment check (--skip-attach specified)")
        micropump_available = True
    
    # Step 3: Run the test
    print("\\n🧪 Step 4: Running micropump test...")
    if run_wsl_test(args.distro, args.duration, args.frequency, args.voltage, args.waveform):
        print("\\n🎉 All steps completed successfully!")
        print("✅ Micropump test signal sent successfully!")
    else:
        print("\\n❌ Micropump test failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()