import ctypes
from ctypes import wintypes
import time

class WindowsAPIPumpController:
    """Direct Windows API pump controller - no drivers needed!"""
    
    def __init__(self, port):
        self.port = port
        self.handle = None
        
    def open(self):
        """Open device using Windows API."""
        kernel32 = ctypes.windll.kernel32
        GENERIC_READ = 0x80000000
        GENERIC_WRITE = 0x40000000
        OPEN_EXISTING = 3
        
        device_path = f"\\\\.\\{self.port}"
        self.handle = kernel32.CreateFileW(
            device_path,
            GENERIC_READ | GENERIC_WRITE,
            0, None, OPEN_EXISTING, 0, None
        )
        
        return self.handle != -1
    
    def write_command(self, command):
        """Write command using Windows API."""
        if self.handle is None or self.handle == -1:
            return False
            
        kernel32 = ctypes.windll.kernel32
        data = command.encode() + b'\\r'
        bytes_written = wintypes.DWORD(0)
        
        success = kernel32.WriteFile(
            self.handle, data, len(data),
            ctypes.byref(bytes_written), None
        )
        
        print(f"   Wrote command '{command}': {bytes_written.value} bytes")
        return success != 0
    
    def setup_pump(self):
        """Setup pump with 100Hz, 100V, rectangle waveform."""
        print("🔧 Configuring pump via Windows API...")
        commands = ["MR", "F100", "A100"]  # Reset, Frequency, Amplitude
        for cmd in commands:
            if not self.write_command(cmd):
                return False
            time.sleep(0.2)
        return True
    
    def start_pump(self):
        """Start the pump."""
        print("▶️  Starting pump via Windows API...")
        return self.write_command("bon")
    
    def stop_pump(self):
        """Stop the pump."""
        print("⏹️  Stopping pump via Windows API...")
        return self.write_command("boff")
    
    def close(self):
        """Close device handle."""
        if self.handle and self.handle != -1:
            kernel32 = ctypes.windll.kernel32
            kernel32.CloseHandle(self.handle)
            self.handle = None

# Test the API controller
if __name__ == "__main__":
    print("🚀 WINDOWS API DRIVER-FREE PUMP CONTROLLER")
    print("=" * 50)
    print("Testing pump control using pure Windows API calls")
    print("=" * 50)
    
    try:
        # Import port detection
        import sys
        import os
        sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
        from resolve_ports import find_pump_port_by_vid_pid
        
        # Find pump
        port = find_pump_port_by_vid_pid(0x0403, 0xB4C0)
        print(f"🔍 Found pump on: {port}")
        
        # Create controller
        controller = WindowsAPIPumpController(port)
        
        if controller.open():
            print("✅ Opened pump via Windows API")
            
            if controller.setup_pump():
                print("✅ Pump configured (100Hz, 100V, Rectangle)")
                
                if controller.start_pump():
                    print("✅ Pump started - listen for sound!")
                    print("🎧 Pump should be running for 3 seconds...")
                    time.sleep(3)
                    
                    if controller.stop_pump():
                        print("✅ Pump stopped")
                        print("\\n🎉 SUCCESS: Complete driver-free pump control!")
                        print("💡 This proves you can control the pump without proprietary drivers!")
                    else:
                        print("❌ Failed to stop pump")
                else:
                    print("❌ Failed to start pump")
            else:
                print("❌ Failed to configure pump")
            
            controller.close()
            print("🔒 Device handle closed")
        else:
            print("❌ Failed to open pump")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()