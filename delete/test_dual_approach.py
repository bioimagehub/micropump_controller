"""
Dual-mode pump controller demonstration script.
Shows how to connect to the micropump on both Windows and Linux/WSL.
"""

import sys
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_dual_approach():
    """Test the dual approach pump controller."""
    print("Micropump Dual Approach Test")
    print("=" * 40)
    
    try:
        # Import the original controller
        from controllers.pump_control import UsbPumpController, PumpCommunicationError
        
        print("✓ Pump controller imported successfully")
        
        # Try to create a controller with auto-detection
        print("\nAttempting to connect to pump...")
        print("This will try USB first on Windows, Serial first on Linux/WSL")
        
        try:
            pump = UsbPumpController(auto_connect=True)
            print("✓ Successfully connected to pump!")
            
            # Get connection info
            connection_info = getattr(pump, 'get_connection_info', lambda: {})()
            if connection_info:
                print(f"Connection details: {connection_info}")
            
            # Test basic commands
            print("\nTesting basic pump operations...")
            try:
                pump.set_frequency(50)
                print("✓ Set frequency to 50 Hz")
                
                pump.set_amplitude(100)
                print("✓ Set amplitude to 100")
                
                pump.set_waveform("SINE")
                print("✓ Set waveform to SINE")
                
                print("\nPump is ready for use!")
                print("Example usage:")
                print("  pump.pulse(5.0)  # Run for 5 seconds")
                print("  pump.start()     # Start manually")
                print("  pump.stop()      # Stop manually")
                
            except Exception as e:
                print(f"⚠ Command test failed (might be normal): {e}")
                
            pump.disconnect()
            print("✓ Disconnected successfully")
            
        except PumpCommunicationError as e:
            print(f"✗ Connection failed: {e}")
            print("\nTroubleshooting:")
            print("1. Windows users: Install FTDI VCP drivers")
            print("2. WSL users: Forward USB device from Windows")
            print("3. Linux users: Check USB permissions")
            print("4. Run: python test_connection.py for detailed diagnostics")
            
    except ImportError as e:
        print(f"✗ Failed to import pump controller: {e}")
        print("Make sure you're in the correct environment:")
        print("  conda activate pump-ctrl")

def show_connection_methods():
    """Show available connection methods."""
    print("\nConnection Methods Available:")
    print("=" * 40)
    
    try:
        import usbx
        print("✓ USB (usbx) - Direct USB communication")
        print("  - Best for Windows with proper FTDI drivers")
        print("  - Fastest communication")
        print("  - No serial port needed")
    except ImportError:
        print("✗ USB (usbx) - Not available")
        print("  - Install: pip install usbx")
    
    try:
        import serial
        print("✓ Serial (pyserial) - Serial port communication")
        print("  - Best for Linux/WSL")
        print("  - Works with FTDI USB-to-serial")
        print("  - More universal compatibility")
    except ImportError:
        print("✗ Serial (pyserial) - Not available")
        print("  - Install: pip install pyserial")

def main():
    """Main function."""
    show_connection_methods()
    print()
    test_dual_approach()
    
    print("\n" + "=" * 60)
    print("SETUP GUIDE FOR DUAL APPROACH")
    print("=" * 60)
    print("""
WINDOWS USERS (with driver installation capability):
1. Install FTDI VCP drivers from FTDI website
2. Connect micropump via USB
3. Device should appear in Device Manager as COM port
4. Use: pump = UsbPumpController()  # Will try USB first, fallback to serial

WINDOWS USERS (without driver installation capability):
1. Use WSL (Windows Subsystem for Linux)
2. Follow WSL setup instructions below

WSL/LINUX USERS:
1. Install usbipd-win on Windows: winget install usbipd
2. Forward USB device to WSL:
   usbipd list
   usbipd bind --busid X-X
   usbipd attach --wsl --busid X-X
3. In WSL: python test_linux_direct.py
4. Use: pump = UsbPumpController()  # Will try serial first, fallback to USB

NATIVE LINUX USERS:
1. Connect micropump via USB
2. Device should appear as /dev/ttyUSB* automatically
3. Set permissions: sudo usermod -a -G dialout $USER
4. Use: pump = UsbPumpController()  # Will use serial automatically

The controller automatically detects your platform and chooses the best method!
""")

if __name__ == "__main__":
    main()
