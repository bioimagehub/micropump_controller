import argparse
import ctypes
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        return False

def run(cmd, check=True):
    print(">>>", " ".join(cmd))
    return subprocess.run(cmd, check=check, text=True, capture_output=True)

def find_exe_on_path(name):
    p = shutil.which(name)
    if p:
        return Path(p)
    # try common install location
    guess = Path(r"C:\Program Files\usbipd-win\usbipd.exe")
    return guess if guess.exists() else None

def detach_all_usb_devices(dry_run=False):
    """Detach all USB devices from WSL"""
    usbipd_exe = find_exe_on_path("usbipd")
    if not usbipd_exe:
        print("usbipd not found - no USB devices to detach.")
        return True
    
    if dry_run:
        print("DRY RUN: Would detach and unbind all USB devices from WSL")
        # Still run list to show current status
        result = run([str(usbipd_exe), "list"], check=False)
        if result.returncode == 0:
            print("Current USB device status:")
            print(result.stdout)
        return True
    
    try:
        # List all devices
        result = run([str(usbipd_exe), "list"], check=False)
        if result.returncode != 0:
            print("Failed to list USB devices.")
            return False
        
        print("Current USB device status:")
        print(result.stdout)
        
        # Find all attached devices
        attached_devices = []
        for line in result.stdout.splitlines():
            if "Attached" in line:
                match = re.match(r"\s*(\d+-\d+)", line)
                if match:
                    attached_devices.append(match.group(1))
        
        # Detach each attached device
        for busid in attached_devices:
            print(f"Detaching device {busid}...")
            result = run([str(usbipd_exe), "detach", "--busid", busid], check=False)
            if result.returncode == 0:
                print(f"Successfully detached device {busid}")
            else:
                print(f"Failed to detach device {busid}: {result.stderr}")
        
        if not attached_devices:
            print("No USB devices are currently attached to WSL.")
        
        # Always check for shared devices to unbind
        result = run([str(usbipd_exe), "list"], check=False)
        if result.returncode == 0:
            shared_devices = []
            for line in result.stdout.splitlines():
                if "Shared" in line:
                    match = re.match(r"\s*(\d+-\d+)", line)
                    if match:
                        shared_devices.append(match.group(1))
            
            for busid in shared_devices:
                print(f"Unbinding shared device {busid}...")
                result = run([str(usbipd_exe), "unbind", "--busid", busid], check=False)
                if result.returncode == 0:
                    print(f"Successfully unbound device {busid}")
                else:
                    print(f"Failed to unbind device {busid}: {result.stderr}")
            
            if not shared_devices:
                print("No USB devices are currently shared.")
        
        return True
        
    except Exception as e:
        print(f"Error during USB device detachment: {e}")
        return False

def cleanup_wsl_environment(distro: str, dry_run=False):
    """Clean up WSL environment - remove drivers and packages"""
    print(f"Cleaning up WSL environment in distribution '{distro}'...")
    
    if dry_run:
        print("DRY RUN: Would clean up WSL environment:")
        print("  - Remove FTDI kernel modules")
        print("  - Remove custom udev rules")
        print("  - Uninstall Python serial/USB packages")
        print("  - Remove development packages")
        print("  - Clean package cache")
        return True
    
    # Check if distro exists
    result = run(["wsl", "-d", distro, "-e", "true"], check=False)
    if result.returncode != 0:
        error_output = result.stderr + result.stdout
        error_output = error_output.replace('\x00', '')
        if "WSL_E_DISTRO_NOT_FOUND" in error_output or "There is no distribution with the supplied name" in error_output:
            print(f"WSL distribution '{distro}' not found - skipping WSL cleanup.")
            return True
    
    # First check if we can run sudo without password (for non-interactive cleanup)
    sudo_check = run(["wsl", "-d", distro, "-e", "bash", "-c", "sudo -n true 2>/dev/null && echo 'SUDO_OK' || echo 'SUDO_NEEDS_PASSWORD'"], check=False)
    needs_password = "SUDO_NEEDS_PASSWORD" in sudo_check.stdout
    
    if needs_password:
        print("Note: Some cleanup operations require sudo privileges in WSL.")
        print("You may be prompted for your WSL password during cleanup.")
    
    # Create a more robust cleanup script that handles both sudo and non-sudo cases
    cleanup_script = f'''
set +e  # Don't exit on errors, just report them
echo "=== WSL Cleanup Started ==="

# Function to run sudo commands with better error handling
run_sudo() {{
    if sudo -n true 2>/dev/null; then
        sudo "$@"
    else
        echo "Skipping sudo command (no privileges): $*"
        return 0
    fi
}}

# Remove FTDI kernel modules if loaded (non-critical)
echo "Checking FTDI kernel modules..."
if lsmod | grep -q ftdi_sio; then
    echo "Unloading ftdi_sio module..."
    run_sudo rmmod ftdi_sio 2>/dev/null || echo "Could not unload ftdi_sio module"
else
    echo "ftdi_sio module not loaded"
fi

if lsmod | grep -q usbserial; then
    echo "Unloading usbserial module..."
    run_sudo rmmod usbserial 2>/dev/null || echo "Could not unload usbserial module"
else
    echo "usbserial module not loaded"
fi

# Remove any custom udev rules for micropump
echo "Removing custom udev rules..."
run_sudo rm -f /etc/udev/rules.d/*micropump* 2>/dev/null || echo "No micropump udev rules found"
run_sudo rm -f /etc/udev/rules.d/*ftdi* 2>/dev/null || echo "No FTDI udev rules found"
run_sudo rm -f /etc/udev/rules.d/*0403* 2>/dev/null || echo "No 0403 VID udev rules found"

# Remove Python packages related to serial/USB communication (user-level)
echo "Removing Python packages..."
pip3 uninstall -y pyserial 2>/dev/null || echo "pyserial was not installed"
pip3 uninstall -y pyusb 2>/dev/null || echo "pyusb was not installed"
pip3 uninstall -y ftd2xx 2>/dev/null || echo "ftd2xx was not installed"

# Remove development packages that might have been installed
echo "Checking for development packages to remove..."
if dpkg -l | grep -q libftdi-dev; then
    echo "Removing libftdi-dev..."
    run_sudo apt-get remove -y libftdi-dev || echo "Could not remove libftdi-dev"
fi

if dpkg -l | grep -q libusb-1.0-0-dev; then
    echo "Removing libusb-1.0-0-dev..."
    run_sudo apt-get remove -y libusb-1.0-0-dev || echo "Could not remove libusb-1.0-0-dev"
fi

# Clean package cache (if we have sudo)
echo "Cleaning package cache..."
run_sudo apt-get autoremove -y 2>/dev/null || echo "Could not run autoremove"
run_sudo apt-get autoclean 2>/dev/null || echo "Could not run autoclean"

# Reload udev rules (if we have sudo)
echo "Reloading udev rules..."
run_sudo udevadm control --reload-rules 2>/dev/null || echo "Could not reload udev rules"
run_sudo udevadm trigger 2>/dev/null || echo "Could not trigger udev"

echo "=== WSL Cleanup Completed ==="
'''
    
    try:
        result = run(["wsl", "-d", distro, "-e", "bash", "-c", cleanup_script], check=False)
        print(result.stdout)
        if result.stderr:
            print("Cleanup warnings/errors:", result.stderr)
        return True  # Always return True since we handle errors gracefully
    except Exception as e:
        print(f"Error during WSL cleanup: {e}")
        return False

def uninstall_usbipd(dry_run=False):
    """Uninstall usbipd-win from Windows"""
    if not is_admin() and not dry_run:
        print("Administrator privileges required to uninstall usbipd-win.")
        print("Please run this script as Administrator to complete full uninstallation.")
        return False
    
    if dry_run:
        print("DRY RUN: Would uninstall usbipd-win from Windows")
        return True
    
    print("Uninstalling usbipd-win...")
    
    # Try to find the product code for usbipd-win
    try:
        # First try the standard uninstall method
        result = run(["wmic", "product", "where", "name like '%usbipd%'", "get", "IdentifyingNumber,Name"], check=False)
        if result.returncode == 0 and "usbipd" in result.stdout.lower():
            print("Found usbipd-win installation:")
            print(result.stdout)
            
            # Extract the product code
            lines = result.stdout.strip().split('\n')
            product_code = None
            for line in lines:
                if "usbipd" in line.lower() and "{" in line:
                    parts = line.split()
                    for part in parts:
                        if part.startswith("{") and part.endswith("}"):
                            product_code = part
                            break
            
            if product_code:
                print(f"Uninstalling using product code: {product_code}")
                result = run(["msiexec", "/x", product_code, "/qn"], check=False)
                if result.returncode == 0:
                    print("Successfully uninstalled usbipd-win")
                    return True
                else:
                    print(f"Failed to uninstall usbipd-win: {result.stderr}")
        
        # Fallback: try to uninstall by searching for MSI files
        print("Trying alternative uninstall method...")
        common_locations = [
            r"C:\Program Files\usbipd-win",
            r"C:\Program Files (x86)\usbipd-win"
        ]
        
        for location in common_locations:
            path = Path(location)
            if path.exists():
                print(f"Removing directory: {path}")
                try:
                    shutil.rmtree(path)
                    print(f"Successfully removed {path}")
                except Exception as e:
                    print(f"Failed to remove {path}: {e}")
        
        # Remove from PATH if present
        print("Checking PATH environment variable...")
        # Note: This would require registry editing for permanent removal
        # For now, just inform the user
        print("Note: You may need to manually remove usbipd-win from your PATH environment variable")
        
        return True
        
    except Exception as e:
        print(f"Error during usbipd-win uninstallation: {e}")
        return False

def cleanup_windows_drivers(dry_run=False):
    """Clean up Windows-side drivers and registry entries"""
    if not is_admin() and not dry_run:
        print("Note: Administrator privileges required for complete Windows driver cleanup.")
        print("Skipping driver cleanup. Run as Administrator for full cleanup.")
        return True  # Don't fail the entire process
    
    if dry_run:
        print("DRY RUN: Would clean up Windows drivers and registry entries")
        print("  - Scan for FTDI and micropump-related drivers")
        print("  - Remove custom driver installations")
        print("  - Check Device Manager for related devices")
        return True
    
    print("Cleaning up Windows drivers and registry entries...")
    
    try:
        # Remove any custom driver installations
        print("Scanning for FTDI and micropump-related drivers...")
        
        # Use pnputil to list and remove any custom FTDI drivers
        result = run(["pnputil", "/enum-drivers"], check=False)
        if result.returncode == 0:
            lines = result.stdout.split('\n')
            drivers_to_remove = []
            current_inf = None
            current_provider = None
            
            for line in lines:
                line = line.strip()
                if "Published Name:" in line:
                    current_inf = line.split(":")[-1].strip()
                    current_provider = None
                elif "Provider Name:" in line:
                    current_provider = line.split(":")[-1].strip().lower()
                    # Check if this is a driver we might want to remove
                    if current_inf and current_provider and any(keyword in current_provider for keyword in ["ftdi", "micropump", "bami"]):
                        drivers_to_remove.append((current_inf, current_provider))
            
            if drivers_to_remove:
                print(f"Found {len(drivers_to_remove)} potentially related driver(s):")
                for inf, provider in drivers_to_remove:
                    print(f"  - {inf} (Provider: {provider})")
                
                for inf, provider in drivers_to_remove:
                    print(f"Removing driver: {inf} (Provider: {provider})")
                    result = run(["pnputil", "/delete-driver", inf, "/uninstall", "/force"], check=False)
                    if result.returncode == 0:
                        print(f"Successfully removed driver {inf}")
                    else:
                        print(f"Failed to remove driver {inf}: {result.stderr}")
            else:
                print("No FTDI or micropump-related drivers found to remove.")
        else:
            print("Could not enumerate drivers - pnputil failed")
        
        # Check for devices in Device Manager that might need manual removal
        print("\nChecking for devices that might need manual removal...")
        try:
            # Use wmic to find USB devices with FTDI VID
            result = run(["wmic", "path", "Win32_PnPEntity", "where", "DeviceID like '%USB\\\\VID_0403%'", "get", "Name,DeviceID"], check=False)
            if result.returncode == 0 and "VID_0403" in result.stdout:
                print("Found FTDI devices in Device Manager:")
                print(result.stdout)
                print("Note: You may need to manually remove these devices from Device Manager if they are no longer needed.")
        except Exception as e:
            print(f"Could not check Device Manager: {e}")
        
        return True
        
    except Exception as e:
        print(f"Error during Windows driver cleanup: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Detach micropump and uninstall all related components from both WSL and Windows.")
    parser.add_argument("--distro", default="Ubuntu", help="WSL distro name to clean up (default: Ubuntu)")
    parser.add_argument("--keep-usbipd", action="store_true", help="Keep usbipd-win installed (only detach devices)")
    parser.add_argument("--wsl-only", action="store_true", help="Only clean up WSL environment, don't touch Windows")
    parser.add_argument("--windows-only", action="store_true", help="Only clean up Windows, don't touch WSL")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without actually doing it")
    parser.add_argument("--force", action="store_true", help="Don't ask for confirmation")
    args = parser.parse_args()
    
    if args.wsl_only and args.windows_only:
        sys.exit("Error: Cannot specify both --wsl-only and --windows-only")
    
    print("Micropump Detach and Cleanup Tool")
    print("=" * 40)
    
    if args.dry_run:
        print("DRY RUN MODE - No changes will be made")
        print("=" * 40)
    
    if not args.force and not args.dry_run:
        print("\nThis will:")
        if not args.windows_only:
            print(f"  - Clean up WSL environment in '{args.distro}'")
            print("  - Remove FTDI drivers and Python packages from WSL")
        if not args.wsl_only:
            print("  - Detach all USB devices from WSL")
            if not args.keep_usbipd:
                print("  - Uninstall usbipd-win from Windows")
            print("  - Clean up Windows drivers")
        
        response = input("\nDo you want to continue? (y/N): ")
        if response.lower() not in ['y', 'yes']:
            print("Operation cancelled.")
            return
    
    success = True
    
    # Step 1: Detach USB devices (unless WSL-only)
    if not args.wsl_only:
        print("\n" + "=" * 50)
        print("STEP 1: Detaching USB devices from WSL")
        print("=" * 50)
        if not detach_all_usb_devices(args.dry_run):
            success = False
            print("Warning: Failed to detach all USB devices")
    
    # Step 2: Clean up WSL environment (unless Windows-only)
    if not args.windows_only:
        print("\n" + "=" * 50)
        print("STEP 2: Cleaning up WSL environment")
        print("=" * 50)
        if not cleanup_wsl_environment(args.distro, args.dry_run):
            success = False
            print("Warning: WSL cleanup had some issues")
    
    # Step 3: Clean up Windows (unless WSL-only)
    if not args.wsl_only:
        print("\n" + "=" * 50)
        print("STEP 3: Cleaning up Windows")
        print("=" * 50)
        
        # Clean up drivers
        if not cleanup_windows_drivers(args.dry_run):
            success = False
            print("Warning: Windows driver cleanup had some issues")
        
        # Uninstall usbipd-win (unless --keep-usbipd)
        if not args.keep_usbipd:
            print("\nUninstalling usbipd-win...")
            if not uninstall_usbipd(args.dry_run):
                success = False
                print("Warning: usbipd-win uninstallation had some issues")
        else:
            print("Keeping usbipd-win installed as requested.")
    
    print("\n" + "=" * 50)
    if args.dry_run:
        print("✓ Dry run completed successfully!")
        print("Use without --dry-run to perform actual cleanup.")
    elif success:
        print("✓ Cleanup completed successfully!")
    else:
        print("⚠ Cleanup completed with some warnings/errors.")
        print("Some manual cleanup may be required.")
    
    if not args.dry_run:
        print("\nRecommendations:")
        print("  - Restart your computer to ensure all changes take effect")
        print("  - Check Device Manager for any remaining FTDI devices")
        if not args.wsl_only:
            print("  - Verify usbipd-win is removed from your PATH environment variable")
    print("=" * 50)

if __name__ == "__main__":
    main()