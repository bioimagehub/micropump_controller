#!/usr/bin/env python3
"""
SAFE DOCKER-BASED DRIVER TESTING
================================
Test driver-free pump communication in isolated Docker containers
without risking the host system's working drivers.
"""

import subprocess
import os
import time

class DockerDriverTester:
    """Safe Docker-based testing of driver alternatives."""
    
    def __init__(self):
        self.pump_vid = "0403"
        self.pump_pid = "b4c0"
        
    def check_docker_available(self):
        """Check if Docker is available."""
        try:
            result = subprocess.run(["docker", "--version"], capture_output=True, text=True)
            if result.returncode == 0:
                print(f"✅ Docker available: {result.stdout.strip()}")
                return True
            else:
                print("❌ Docker not available")
                return False
        except FileNotFoundError:
            print("❌ Docker not installed")
            return False
    
    def check_wsl2_usb_support(self):
        """Check if WSL2 with USB support is available."""
        try:
            # Check if usbipd is installed
            result = subprocess.run(["usbipd", "wsl", "list"], capture_output=True, text=True)
            if result.returncode == 0:
                print("✅ usbipd-win available for WSL2 USB forwarding")
                print("USB devices that can be forwarded:")
                print(result.stdout)
                return True
            else:
                print("❌ usbipd-win not available")
                return False
        except FileNotFoundError:
            print("❌ usbipd-win not installed")
            return False
    
    def create_docker_test_environment(self):
        """Create Docker containers for safe driver testing."""
        print("\\n🐳 CREATING DOCKER TEST ENVIRONMENTS")
        print("=" * 50)
        
        # Create Dockerfile for Ubuntu with USB tools
        dockerfile_ubuntu = '''
FROM ubuntu:22.04

# Install USB and serial tools
RUN apt-get update && apt-get install -y \\
    python3 \\
    python3-pip \\
    usbutils \\
    libusb-1.0-0-dev \\
    libusb-dev \\
    minicom \\
    screen \\
    stty \\
    && rm -rf /var/lib/apt/lists/*

# Install Python USB libraries
RUN pip3 install pyusb pyserial

# Create test script
COPY pump_test.py /app/pump_test.py
WORKDIR /app

CMD ["python3", "pump_test.py"]
'''
        
        # Create Python test script for container
        pump_test_script = f'''
#!/usr/bin/env python3
import usb.core
import usb.util
import serial
import time
import sys

def test_pyusb_direct():
    """Test direct PyUSB communication."""
    print("🔍 Testing PyUSB direct communication...")
    
    try:
        # Find pump device
        dev = usb.core.find(idVendor=0x{self.pump_vid}, idProduct=0x{self.pump_pid})
        if dev is None:
            print("❌ Pump device not found via PyUSB")
            return False
        
        print(f"✅ Found device: {{dev}}")
        
        # Get device info
        try:
            manufacturer = usb.util.get_string(dev, dev.iManufacturer)
            product = usb.util.get_string(dev, dev.iProduct)
            print(f"   Manufacturer: {{manufacturer}}")
            print(f"   Product: {{product}}")
        except:
            print("   (Could not read device strings)")
        
        # Set configuration
        dev.set_configuration()
        print("   Configuration set")
        
        # Get endpoints
        cfg = dev.get_active_configuration()
        intf = cfg[(0,0)]
        
        ep_out = usb.util.find_descriptor(
            intf, custom_match=lambda e: usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_OUT
        )
        
        if ep_out:
            print("   Found output endpoint")
            # Send pump commands
            commands = [b'F100\\r', b'A100\\r', b'bon\\r']
            for cmd in commands:
                ep_out.write(cmd)
                print(f"   Sent: {{cmd}}")
                time.sleep(0.2)
            
            print("✅ PyUSB communication successful!")
            
            # Turn off pump
            time.sleep(1)
            ep_out.write(b'boff\\r')
            print("   Pump turned off")
            
            return True
        else:
            print("❌ No output endpoint found")
            return False
            
    except Exception as e:
        print(f"❌ PyUSB error: {{e}}")
        return False

def test_serial_direct():
    """Test direct serial communication."""
    print("\\n🔍 Testing direct serial communication...")
    
    # Try common USB serial device paths
    device_paths = ["/dev/ttyUSB0", "/dev/ttyUSB1", "/dev/ttyACM0", "/dev/ttyACM1"]
    
    for device_path in device_paths:
        try:
            print(f"   Trying {{device_path}}...")
            with serial.Serial(device_path, 9600, timeout=1) as ser:
                print(f"   ✅ Opened {{device_path}}")
                
                # Send pump commands
                commands = [b'F100\\r', b'A100\\r', b'bon\\r']
                for cmd in commands:
                    ser.write(cmd)
                    print(f"   Sent: {{cmd}}")
                    time.sleep(0.2)
                
                print("✅ Serial communication successful!")
                
                # Turn off pump
                time.sleep(1)
                ser.write(b'boff\\r')
                print("   Pump turned off")
                
                return True
                
        except Exception as e:
            print(f"   ❌ {{device_path}}: {{e}}")
            continue
    
    print("❌ No working serial device found")
    return False

def main():
    print("🚀 DOCKER CONTAINER PUMP TEST")
    print("=" * 40)
    
    # Test both methods
    pyusb_success = test_pyusb_direct()
    serial_success = test_serial_direct()
    
    print("\\n📊 RESULTS:")
    print(f"   PyUSB direct: {{'✅ SUCCESS' if pyusb_success else '❌ FAILED'}}")
    print(f"   Serial direct: {{'✅ SUCCESS' if serial_success else '❌ FAILED'}}")
    
    if pyusb_success or serial_success:
        print("\\n🎉 BREAKTHROUGH: Driver-free communication working in container!")
        sys.exit(0)
    else:
        print("\\n❌ No driver-free methods worked in container")
        sys.exit(1)

if __name__ == "__main__":
    main()
'''
        
        # Write files
        with open("Dockerfile.ubuntu", "w") as f:
            f.write(dockerfile_ubuntu)
        
        with open("pump_test.py", "w") as f:
            f.write(pump_test_script)
        
        print("✅ Docker test environment files created")
        return True
    
    def build_docker_image(self):
        """Build Docker image for testing."""
        print("\\n🔨 BUILDING DOCKER IMAGE")
        print("=" * 30)
        
        try:
            cmd = ["docker", "build", "-f", "Dockerfile.ubuntu", "-t", "pump-test-ubuntu", "."]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                print("✅ Docker image built successfully")
                return True
            else:
                print(f"❌ Docker build failed: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"❌ Docker build error: {e}")
            return False
    
    def test_with_usb_passthrough(self):
        """Test with USB device passthrough to container."""
        print("\\n🔌 TESTING WITH USB PASSTHROUGH")
        print("=" * 40)
        
        # Method 1: Direct USB device passthrough (Linux host)
        print("📍 Method 1: Direct USB device passthrough")
        try:
            cmd = [
                "docker", "run", "--rm", "--privileged",
                "--device=/dev/bus/usb",  # Pass entire USB bus
                "pump-test-ubuntu"
            ]
            
            print("   Running container with USB device access...")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            print("Container output:")
            print(result.stdout)
            if result.stderr:
                print("Errors:")
                print(result.stderr)
            
            return result.returncode == 0
            
        except subprocess.TimeoutExpired:
            print("   ⏰ Container test timed out")
            return False
        except Exception as e:
            print(f"   ❌ Container test error: {e}")
            return False
    
    def test_with_wsl2_forwarding(self):
        """Test with WSL2 USB forwarding."""
        print("\\n🐧 TESTING WITH WSL2 USB FORWARDING")
        print("=" * 40)
        
        print("📋 WSL2 USB forwarding steps:")
        print("1. List USB devices: usbipd wsl list")
        print("2. Attach pump device: usbipd wsl attach --busid <BUSID>")
        print("3. Test in WSL2: lsusb")
        print("4. Run container in WSL2 with USB access")
        
        choice = input("\\nDo you want to try WSL2 USB forwarding? (y/n): ").lower().strip()
        if choice not in ['y', 'yes']:
            return False
        
        # Step 1: List devices
        print("\\n📍 Step 1: Listing USB devices...")
        try:
            result = subprocess.run(["usbipd", "wsl", "list"], capture_output=True, text=True)
            print(result.stdout)
            
            # Look for pump device
            if f"{self.pump_vid}:{self.pump_pid}" in result.stdout:
                print(f"✅ Found pump device in USB list")
                
                # Extract BUSID
                lines = result.stdout.split('\\n')
                busid = None
                for line in lines:
                    if f"{self.pump_vid}:{self.pump_pid}" in line:
                        busid = line.split()[0]
                        break
                
                if busid:
                    print(f"   BUSID: {busid}")
                    
                    # Step 2: Attach device
                    print(f"\\n📍 Step 2: Attaching device {busid} to WSL2...")
                    attach_cmd = ["usbipd", "wsl", "attach", "--busid", busid]
                    attach_result = subprocess.run(attach_cmd, capture_output=True, text=True)
                    
                    if attach_result.returncode == 0:
                        print("✅ Device attached to WSL2")
                        
                        # Step 3: Test in WSL2
                        print("\\n📍 Step 3: Testing device in WSL2...")
                        wsl_cmd = ["wsl", "lsusb"]
                        wsl_result = subprocess.run(wsl_cmd, capture_output=True, text=True)
                        print("WSL2 USB devices:")
                        print(wsl_result.stdout)
                        
                        # Step 4: Run container in WSL2
                        print("\\n📍 Step 4: Running container in WSL2...")
                        container_cmd = ["wsl", "docker", "run", "--rm", "--privileged", "--device=/dev/bus/usb", "pump-test-ubuntu"]
                        container_result = subprocess.run(container_cmd, capture_output=True, text=True, timeout=30)
                        
                        print("Container output:")
                        print(container_result.stdout)
                        
                        return container_result.returncode == 0
                    else:
                        print(f"❌ Failed to attach device: {attach_result.stderr}")
                        return False
                else:
                    print("❌ Could not extract BUSID")
                    return False
            else:
                print("❌ Pump device not found in USB list")
                return False
                
        except Exception as e:
            print(f"❌ WSL2 forwarding error: {e}")
            return False
    
    def run_safe_tests(self):
        """Run all safe Docker-based tests."""
        print("🚀 SAFE DOCKER-BASED DRIVER TESTING")
        print("=" * 50)
        print("Testing driver-free pump communication without risking host drivers")
        print("=" * 50)
        
        # Check prerequisites
        if not self.check_docker_available():
            print("\\n❌ Docker required for safe testing")
            print("💡 Install Docker Desktop: winget install Docker.DockerDesktop")
            return False
        
        # Check WSL2 USB support
        wsl2_available = self.check_wsl2_usb_support()
        
        # Create test environment
        if not self.create_docker_test_environment():
            return False
        
        # Build Docker image
        if not self.build_docker_image():
            return False
        
        # Test methods
        results = {}
        
        # Test USB passthrough (if on Linux or WSL2)
        if os.name == 'posix':  # Linux environment
            results['usb_passthrough'] = self.test_with_usb_passthrough()
        
        # Test WSL2 forwarding
        if wsl2_available:
            results['wsl2_forwarding'] = self.test_with_wsl2_forwarding()
        
        # Print final results
        self.print_safe_test_results(results)
        
        return any(results.values())
    
    def print_safe_test_results(self, results):
        """Print results of safe testing."""
        print("\\n\\n🎯 SAFE TESTING RESULTS")
        print("=" * 40)
        
        if results:
            for method, success in results.items():
                status = "✅ SUCCESS" if success else "❌ FAILED"
                print(f"{method}: {status}")
            
            if any(results.values()):
                print("\\n🎉 BREAKTHROUGH: Found working driver-free method in container!")
                print("💡 You can safely implement this on your host system")
            else:
                print("\\n❌ No methods worked in containers")
                print("💡 May need to try different approaches or driver replacement")
        else:
            print("❌ No container tests could be executed")
            print("💡 Check Docker and WSL2 setup")
        
        print("\\n📋 NEXT STEPS:")
        print("1. If tests succeeded: Implement the working method on host")
        print("2. If tests failed: Consider other approaches or careful driver replacement")
        print("3. Alternative: Test on a different computer/VM first")

def main():
    """Main safe testing workflow."""
    tester = DockerDriverTester()
    tester.run_safe_tests()

if __name__ == "__main__":
    main()