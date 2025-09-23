#!/usr/bin/env python3
"""
Simple micropump test that directly runs the test in WSL without permission setup.
"""

import subprocess
import sys

def run_direct_wsl_test(distro="Ubuntu", duration=1.0, frequency=100, voltage=100, waveform="RECT"):
    """Run micropump test directly in WSL."""
    
    # Create the pump test script content
    pump_script = f'''
import time
import serial
import glob
import sys

print("=== Direct WSL Micropump Test ===")

# Find serial ports
ports = glob.glob('/dev/ttyUSB*') + glob.glob('/dev/ttyACM*')
if not ports:
    print("❌ No serial ports found")
    sys.exit(1)

port = ports[0]
print(f"Using serial port: {{port}}")

try:
    # Try to connect
    ser = serial.Serial(
        port=port,
        baudrate=9600,
        timeout=2,
        xonxoff=True
    )
    print(f"✅ Connected to pump on {{port}}")
    
    # Configure pump
    commands = [
        f"F{frequency}",  # Set frequency
        f"A{voltage}",    # Set voltage  
        "MR",             # Set rectangular waveform
    ]
    
    for cmd in commands:
        full_cmd = cmd + "\\r"
        ser.write(full_cmd.encode("utf-8"))
        ser.flush()
        print(f"Sent: {{cmd}}")
        time.sleep(0.15)
    
    # Start pump
    ser.write(b"bon\\r")
    ser.flush()
    print(f"🚀 Pump started - running for {duration} seconds")
    print(f"Parameters: {frequency}Hz, {voltage}Vpp, {waveform}")
    
    # Wait for duration
    time.sleep({duration})
    
    # Stop pump
    ser.write(b"boff\\r")
    ser.flush()
    print("⏹️  Pump stopped")
    
    # Close connection
    ser.close()
    print("✅ Test completed successfully!")
    
except PermissionError:
    print("❌ Permission denied accessing serial port")
    print("Try running: sudo chmod 666 /dev/ttyUSB* /dev/ttyACM*")
    sys.exit(1)
except Exception as e:
    print(f"❌ Error: {{e}}")
    sys.exit(1)
'''
    
    # Run the script in WSL
    try:
        print(f"🧪 Running direct micropump test in WSL...")
        print(f"Parameters: {duration}s, {frequency}Hz, {voltage}Vpp, {waveform}")
        
        # First check if pyserial is available and install if needed
        check_cmd = [
            "wsl", "-d", distro, "-e", "bash", "-c",
            "python3 -c 'import serial' 2>/dev/null || pip3 install pyserial --user"
        ]
        subprocess.run(check_cmd, check=False)
        
        # Run the test
        test_cmd = [
            "wsl", "-d", distro, "-e", "python3", "-c", pump_script
        ]
        
        result = subprocess.run(test_cmd, check=False, text=True)
        
        if result.returncode == 0:
            print("🎉 Test completed successfully!")
            return True
        else:
            print(f"❌ Test failed with exit code: {result.returncode}")
            return False
            
    except Exception as e:
        print(f"❌ Error running test: {e}")
        return False

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Direct WSL micropump test")
    parser.add_argument("--distro", default="Ubuntu", help="WSL distro")
    parser.add_argument("--duration", type=float, default=1.0, help="Duration in seconds")
    parser.add_argument("--frequency", type=int, default=100, help="Frequency in Hz")
    parser.add_argument("--voltage", type=int, default=100, help="Voltage in Vpp")
    parser.add_argument("--waveform", default="RECT", help="Waveform type")
    
    args = parser.parse_args()
    
    success = run_direct_wsl_test(
        args.distro, args.duration, args.frequency, args.voltage, args.waveform
    )
    
    sys.exit(0 if success else 1)