#!/usr/bin/env python3
"""
Manual driver installation guide and helper.
"""

import subprocess
import sys
import os

def check_admin():
    """Check if running as administrator."""
    try:
        return os.getuid() == 0
    except AttributeError:
        # Windows
        import ctypes
        return ctypes.windll.shell32.IsUserAnAdmin() != 0

def install_drivers_manual():
    """Guide for manual driver installation."""
    print("=== Manual FTDI Driver Installation Guide ===")
    print()
    print("Since automatic installation requires admin privileges,")
    print("here's how to install the drivers manually:")
    print()
    print("1. Open Device Manager (devmgmt.msc)")
    print("2. Look for 'USB Micropump Control' with a yellow warning icon")
    print("3. Right-click on it and select 'Update Driver'")
    print("4. Choose 'Browse my computer for driver software'")
    print("5. Navigate to:")
    driver_path = r"C:\git\micropump_controller\hardware\drivers\Bartels_controller_XU7_USB_Driver_2.08.30_uncert\Bartels_controller_XU7_USB_Driver_2.08.30"
    print(f"   {driver_path}")
    print("6. Click 'Next' and let Windows install the driver")
    print("7. If Windows shows a security warning, click 'Install this driver anyway'")
    print()
    print("After installation, the device should appear as a COM port")
    print("Then run: python test_pump_serial_native.py")
    
    return driver_path

def try_pnputil_install():
    """Try to install using pnputil with admin check."""
    if not check_admin():
        print("Not running as administrator. Manual installation required.")
        return False
    
    driver_path = r"C:\git\micropump_controller\hardware\drivers\Bartels_controller_XU7_USB_Driver_2.08.30_uncert\Bartels_controller_XU7_USB_Driver_2.08.30"
    
    inf_files = [
        os.path.join(driver_path, "ftdibus Bami.inf"),
        os.path.join(driver_path, "ftdiport Bami.inf")
    ]
    
    for inf_file in inf_files:
        if os.path.exists(inf_file):
            try:
                print(f"Installing {inf_file}...")
                result = subprocess.run([
                    "pnputil", "/add-driver", inf_file, "/install"
                ], capture_output=True, text=True)
                
                if result.returncode == 0:
                    print(f"✓ Successfully installed {inf_file}")
                else:
                    print(f"✗ Failed to install {inf_file}")
                    print(f"Error: {result.stderr}")
                    return False
            except Exception as e:
                print(f"✗ Exception installing {inf_file}: {e}")
                return False
    
    return True

def main():
    """Main driver installation helper."""
    print("=== Bartels FTDI Driver Installation Helper ===")
    
    if check_admin():
        print("Running as administrator - attempting automatic installation...")
        if try_pnputil_install():
            print("\n✓ Drivers installed successfully!")
            print("Please run: python scan_com_ports.py")
            print("Then run: python test_pump_serial_native.py")
        else:
            print("\n✗ Automatic installation failed")
            install_drivers_manual()
    else:
        print("Not running as administrator")
        install_drivers_manual()
    
    print("\nAfter driver installation, you should see a new COM port")
    print("in Device Manager under 'Ports (COM & LPT)'")

if __name__ == "__main__":
    main()
