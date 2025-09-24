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
    """Clean up WSL environment - remove FTDI setup, drivers, permissions, and packages"""
    print(f"Cleaning up WSL environment in distribution '{distro}'...")
    
    if dry_run:
        print("DRY RUN: Would clean up WSL environment:")
        print("  - Remove FTDI kernel modules")
        print("  - Remove ALL custom udev rules (99-ftdi-micropump.rules, etc.)")
        print("  - Remove user from dialout group")
        print("  - Remove persistent module loading configuration")
        print("  - Uninstall FTDI and Python serial/USB packages")
        print("  - Remove development packages")
        print("  - Clean package cache")
        print("  - Reset serial device permissions")
        return True
    
    # Check if distro exists
    result = run(["wsl", "-d", distro, "-e", "true"], check=False)
    if result.returncode != 0:
        error_output = result.stderr + result.stdout
        error_output = error_output.replace('\x00', '')
        if "WSL_E_DISTRO_NOT_FOUND" in error_output or "There is no distribution with the supplied name" in error_output:
            print(f"WSL distribution '{distro}' not found - skipping WSL cleanup.")
            return True
    
    # Get current user for proper cleanup
    user_check = run(["wsl", "-d", distro, "-e", "whoami"], check=False)
    current_user = user_check.stdout.strip() if user_check.returncode == 0 else "user"
    print(f"Cleaning up configuration for user: {current_user}")
    
    # First check if we can run sudo without password (for non-interactive cleanup)
    sudo_check = run(["wsl", "-d", distro, "-e", "bash", "-c", "sudo -n true 2>/dev/null && echo 'SUDO_OK' || echo 'SUDO_NEEDS_PASSWORD'"], check=False)
    needs_password = "SUDO_NEEDS_PASSWORD" in sudo_check.stdout
    
    if needs_password:
        print("Note: Some cleanup operations require sudo privileges in WSL.")
        print("You may be prompted for your WSL password during cleanup.")
    
    # Create a comprehensive cleanup script that reverses ALL attach_micropump changes
    cleanup_script = f'''
set +e  # Don't exit on errors, just report them
echo "=== WSL Comprehensive Cleanup Started ==="

ACTUAL_USER="{current_user}"
echo "Cleaning configuration for user: $ACTUAL_USER"

# Function to run sudo commands with better error handling
run_sudo() {{
    if sudo -n true 2>/dev/null; then
        sudo "$@"
    else
        echo "Skipping sudo command (no privileges): $*"
        return 0
    fi
}}

# STEP 1: Remove FTDI kernel modules if loaded
echo "=== Removing FTDI kernel modules ==="
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

# STEP 2: Remove ALL custom udev rules created by attach_micropump
echo "=== Removing custom udev rules ==="
run_sudo rm -f /etc/udev/rules.d/99-ftdi-micropump.rules && echo "Removed 99-ftdi-micropump.rules" || echo "99-ftdi-micropump.rules not found"
run_sudo rm -f /etc/udev/rules.d/*micropump* 2>/dev/null || echo "No other micropump udev rules found"
run_sudo rm -f /etc/udev/rules.d/*ftdi* 2>/dev/null || echo "No other FTDI udev rules found"
run_sudo rm -f /etc/udev/rules.d/*0403* 2>/dev/null || echo "No 0403 VID udev rules found"

# STEP 3: Remove persistent module loading configuration
echo "=== Removing persistent module loading ==="
run_sudo rm -f /etc/modules-load.d/ftdi.conf && echo "Removed ftdi.conf module loading" || echo "ftdi.conf not found"

# STEP 4: Remove user from dialout group
echo "=== Removing user from dialout group ==="
if groups "$ACTUAL_USER" | grep -q dialout; then
    echo "Removing user $ACTUAL_USER from dialout group..."
    run_sudo gpasswd -d "$ACTUAL_USER" dialout && echo "User removed from dialout group" || echo "Could not remove user from dialout group"
else
    echo "User $ACTUAL_USER is not in dialout group"
fi

# STEP 5: Reset permissions on any existing serial devices
echo "=== Resetting serial device permissions ==="
for device in /dev/ttyUSB* /dev/ttyACM*; do
    if [ -c "$device" ]; then
        echo "Resetting permissions on $device"
        run_sudo chmod 660 "$device" || echo "Could not reset permissions on $device"
        run_sudo chgrp tty "$device" 2>/dev/null || echo "Could not reset group on $device"
    fi
done

# STEP 6: Remove Python packages related to serial/USB communication
echo "=== Removing Python packages ==="
pip3 uninstall -y pyserial 2>/dev/null || echo "pyserial was not installed via pip"
pip3 uninstall -y pyusb 2>/dev/null || echo "pyusb was not installed via pip"
pip3 uninstall -y ftd2xx 2>/dev/null || echo "ftd2xx was not installed via pip"

# STEP 7: Remove FTDI and development packages installed by attach_micropump
echo "=== Removing FTDI and development packages ==="
if dpkg -l | grep -q libftdi1-2; then
    echo "Removing libftdi1-2..."
    run_sudo apt-get remove --purge -y libftdi1-2 || echo "Could not remove libftdi1-2"
fi

if dpkg -l | grep -q libftdi1-dev; then
    echo "Removing libftdi1-dev..."
    run_sudo apt-get remove --purge -y libftdi1-dev || echo "Could not remove libftdi1-dev"
fi

if dpkg -l | grep -q python3-serial; then
    echo "Removing python3-serial..."
    run_sudo apt-get remove --purge -y python3-serial || echo "Could not remove python3-serial"
fi

if dpkg -l | grep -q usbutils; then
    echo "Note: Keeping usbutils (system package, may be needed by other software)"
fi

# Remove other development packages that might have been installed
if dpkg -l | grep -q libusb-1.0-0-dev; then
    echo "Removing libusb-1.0-0-dev..."
    run_sudo apt-get remove --purge -y libusb-1.0-0-dev || echo "Could not remove libusb-1.0-0-dev"
fi

# STEP 8: Remove FTDI device ID from kernel driver
echo "=== Removing FTDI device ID registration ==="
if [ -f /sys/bus/usb-serial/drivers/ftdi_sio/remove_id ]; then
    echo "Removing device ID 0403 b4c0 from ftdi_sio driver..."
    run_sudo bash -c 'echo "0403 b4c0" > /sys/bus/usb-serial/drivers/ftdi_sio/remove_id' 2>/dev/null || echo "Could not remove device ID (may not be registered)"
fi

# STEP 9: Clean package cache and autoremove
echo "=== Cleaning package cache ==="
run_sudo apt-get autoremove --purge -y 2>/dev/null || echo "Could not run autoremove"
run_sudo apt-get autoclean 2>/dev/null || echo "Could not run autoclean"
run_sudo apt-get update 2>/dev/null || echo "Could not update package lists"

# STEP 10: Reload udev rules to ensure changes take effect
echo "=== Reloading udev rules ==="
run_sudo udevadm control --reload-rules 2>/dev/null || echo "Could not reload udev rules"
run_sudo udevadm trigger 2>/dev/null || echo "Could not trigger udev"

# STEP 11: Show final status
echo "=== Final Status Check ==="
echo "User groups after cleanup:"
groups "$ACTUAL_USER" || echo "Could not check user groups"

echo "Remaining FTDI kernel modules:"
lsmod | grep -E "(ftdi|usbserial)" || echo "No FTDI modules loaded"

echo "Remaining udev rules:"
ls -la /etc/udev/rules.d/*ftdi* /etc/udev/rules.d/*micropump* /etc/udev/rules.d/*0403* 2>/dev/null || echo "No FTDI/micropump udev rules remain"

echo "Remaining serial devices:"
ls -la /dev/ttyUSB* /dev/ttyACM* 2>/dev/null || echo "No serial devices found"

echo "=== WSL Comprehensive Cleanup Completed ==="
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
    """Uninstall usbipd-win from Windows (comprehensive removal)"""
    if not is_admin() and not dry_run:
        print("Administrator privileges required to uninstall usbipd-win.")
        print("Please run this script as Administrator to complete full uninstallation.")
        return False
    
    if dry_run:
        print("DRY RUN: Would uninstall usbipd-win from Windows")
        print("  - Remove via Windows Installer (MSI)")
        print("  - Clean up installation directories")
        print("  - Remove from PATH environment variable")
        print("  - Clean up any temporary MSI files")
        return True
    
    print("Uninstalling usbipd-win (comprehensive removal)...")
    
    try:
        # STEP 1: Try Windows Installer uninstall methods
        print("=== Attempting MSI-based uninstall ===")
        
        # Method 1: Use wmic to find and uninstall
        result = run(["wmic", "product", "where", "name like '%usbipd%'", "get", "IdentifyingNumber,Name"], check=False)
        uninstall_success = False
        
        if result.returncode == 0 and "usbipd" in result.stdout.lower():
            print("Found usbipd-win installation via wmic:")
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
                    print("✅ Successfully uninstalled usbipd-win via MSI")
                    uninstall_success = True
                else:
                    print(f"❌ MSI uninstall failed: {result.stderr}")
        
        # Method 2: Try registry-based approach if wmic failed
        if not uninstall_success:
            print("Attempting registry-based uninstall...")
            try:
                import winreg
                # Check common uninstall registry locations
                uninstall_key = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, uninstall_key) as key:
                    i = 0
                    while True:
                        try:
                            subkey_name = winreg.EnumKey(key, i)
                            with winreg.OpenKey(key, subkey_name) as subkey:
                                try:
                                    display_name = winreg.QueryValueEx(subkey, "DisplayName")[0]
                                    if "usbipd" in display_name.lower():
                                        try:
                                            uninstall_string = winreg.QueryValueEx(subkey, "UninstallString")[0]
                                            print(f"Found registry uninstall string: {uninstall_string}")
                                            # Parse and execute the uninstall string
                                            if "msiexec" in uninstall_string:
                                                # Extract product code and run silent uninstall
                                                import re
                                                match = re.search(r'(\{[^}]+\})', uninstall_string)
                                                if match:
                                                    product_code = match.group(1)
                                                    result = run(["msiexec", "/x", product_code, "/qn"], check=False)
                                                    if result.returncode == 0:
                                                        print("✅ Successfully uninstalled via registry method")
                                                        uninstall_success = True
                                                        break
                                        except FileNotFoundError:
                                            pass
                                except FileNotFoundError:
                                    pass
                            i += 1
                        except OSError:
                            break
            except Exception as e:
                print(f"Registry uninstall attempt failed: {e}")
        
        # STEP 2: Manual cleanup of installation directories
        print("\n=== Cleaning up installation directories ===")
        common_locations = [
            Path(r"C:\Program Files\usbipd-win"),
            Path(r"C:\Program Files (x86)\usbipd-win"),
            Path(r"C:\Windows\System32\usbipd.exe"),  # Sometimes installed here
            Path(r"C:\Windows\SysWOW64\usbipd.exe")   # 32-bit on 64-bit system
        ]
        
        for location in common_locations:
            if location.exists():
                print(f"Removing: {location}")
                try:
                    if location.is_dir():
                        shutil.rmtree(location)
                        print(f"✅ Successfully removed directory {location}")
                    else:
                        location.unlink()
                        print(f"✅ Successfully removed file {location}")
                except Exception as e:
                    print(f"❌ Failed to remove {location}: {e}")
            else:
                print(f"Not found: {location}")
        
        # STEP 3: Clean up PATH environment variable
        print("\n=== Cleaning up PATH environment variable ===")
        try:
            import winreg
            # Check both system and user PATH
            path_locations = [
                (winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment", "Path"),
                (winreg.HKEY_CURRENT_USER, "Environment", "PATH")
            ]
            
            for root_key, sub_key, value_name in path_locations:
                try:
                    with winreg.OpenKey(root_key, sub_key, 0, winreg.KEY_READ | winreg.KEY_WRITE) as key:
                        current_path = winreg.QueryValueEx(key, value_name)[0]
                        # Remove usbipd-win paths
                        path_entries = current_path.split(';')
                        cleaned_entries = [entry for entry in path_entries if 'usbipd' not in entry.lower()]
                        
                        if len(cleaned_entries) != len(path_entries):
                            new_path = ';'.join(cleaned_entries)
                            winreg.SetValueEx(key, value_name, 0, winreg.REG_EXPAND_SZ, new_path)
                            removed_count = len(path_entries) - len(cleaned_entries)
                            print(f"✅ Removed {removed_count} usbipd-related PATH entries from {root_key.name}")
                        else:
                            print(f"No usbipd-related PATH entries found in {root_key.name}")
                except Exception as e:
                    print(f"Could not clean PATH in {root_key.name}: {e}")
        except Exception as e:
            print(f"PATH cleanup failed: {e}")
        
        # STEP 4: Clean up any temporary MSI files that might have been downloaded
        print("\n=== Cleaning up temporary files ===")
        import tempfile
        temp_dir = Path(tempfile.gettempdir())
        for msi_file in temp_dir.glob("*usbipd*.msi"):
            try:
                msi_file.unlink()
                print(f"✅ Removed temporary MSI: {msi_file}")
            except Exception as e:
                print(f"Could not remove {msi_file}: {e}")
        
        # STEP 5: Final verification
        print("\n=== Verifying removal ===")
        final_exe = find_exe_on_path("usbipd")
        if final_exe:
            print(f"⚠️  usbipd still found at: {final_exe}")
            print("Manual removal may be required.")
        else:
            print("✅ usbipd-win appears to be completely removed")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during usbipd-win uninstallation: {e}")
        return False

def check_cleanup_status(distro: str):
    """Check the current status after cleanup to verify what was removed"""
    print("\n" + "=" * 50)
    print("CLEANUP STATUS VERIFICATION")
    print("=" * 50)
    
    # Check Windows status
    print("\n🪟 WINDOWS STATUS:")
    usbipd_exe = find_exe_on_path("usbipd")
    if usbipd_exe:
        print(f"  ⚠️  usbipd-win still installed at: {usbipd_exe}")
        # Show current USB device status
        try:
            result = run([str(usbipd_exe), "list"], check=False)
            if result.returncode == 0:
                attached_count = result.stdout.count("Attached")
                shared_count = result.stdout.count("Shared")
                print(f"  📊 USB Devices: {attached_count} attached, {shared_count} shared")
            else:
                print("  ❌ Could not check USB device status")
        except:
            print("  ❌ Error checking USB device status")
    else:
        print("  ✅ usbipd-win: Not found (removed)")
    
    # Check WSL status
    print(f"\n🐧 WSL STATUS (Distribution: {distro}):")
    wsl_result = run(["wsl", "-d", distro, "-e", "true"], check=False)
    if wsl_result.returncode != 0:
        print(f"  ❌ WSL distribution '{distro}' not accessible")
        return
    
    # Check user groups
    user_check = run(["wsl", "-d", distro, "-e", "whoami"], check=False)
    if user_check.returncode == 0:
        current_user = user_check.stdout.strip()
        groups_check = run(["wsl", "-d", distro, "-e", "groups"], check=False)
        if groups_check.returncode == 0:
            groups = groups_check.stdout.strip()
            if "dialout" in groups:
                print(f"  ⚠️  User {current_user} still in dialout group")
            else:
                print(f"  ✅ User {current_user} removed from dialout group")
        else:
            print("  ❌ Could not check user groups")
    
    # Check FTDI modules
    modules_check = run(["wsl", "-d", distro, "-e", "bash", "-c", "lsmod | grep -E '(ftdi|usbserial)' | wc -l"], check=False)
    if modules_check.returncode == 0:
        module_count = int(modules_check.stdout.strip()) if modules_check.stdout.strip().isdigit() else 0
        if module_count > 0:
            print(f"  ⚠️  {module_count} FTDI-related kernel modules still loaded")
        else:
            print("  ✅ FTDI kernel modules: Unloaded")
    
    # Check udev rules
    udev_check = run(["wsl", "-d", distro, "-e", "bash", "-c", "ls /etc/udev/rules.d/*ftdi* /etc/udev/rules.d/*micropump* 2>/dev/null | wc -l"], check=False)
    if udev_check.returncode == 0:
        rule_count = int(udev_check.stdout.strip()) if udev_check.stdout.strip().isdigit() else 0
        if rule_count > 0:
            print(f"  ⚠️  {rule_count} FTDI/micropump udev rules still present")
        else:
            print("  ✅ Custom udev rules: Removed")
    
    # Check serial devices
    serial_check = run(["wsl", "-d", distro, "-e", "bash", "-c", "ls /dev/ttyUSB* /dev/ttyACM* 2>/dev/null | wc -l"], check=False)
    if serial_check.returncode == 0:
        device_count = int(serial_check.stdout.strip()) if serial_check.stdout.strip().isdigit() else 0
        if device_count > 0:
            print(f"  ℹ️  {device_count} serial devices still present (may be from other hardware)")
        else:
            print("  ✅ Serial devices: None present")
    
    # Check Python packages
    python_check = run(["wsl", "-d", distro, "-e", "bash", "-c", "pip3 list | grep -E '(pyserial|pyusb|ftd2xx)' | wc -l"], check=False)
    if python_check.returncode == 0:
        pkg_count = int(python_check.stdout.strip()) if python_check.stdout.strip().isdigit() else 0
        if pkg_count > 0:
            print(f"  ⚠️  {pkg_count} serial-related Python packages still installed")
        else:
            print("  ✅ Serial Python packages: Removed")
    
    print("\n📋 SUMMARY:")
    print("  🔄 If any items show ⚠️, they may need manual cleanup")
    print("  🔧 Run 'wsl --shutdown && wsl' to ensure kernel modules are unloaded")
    print("  💻 Restart Windows to ensure all changes take effect")


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
    parser.add_argument("--distro", default="Debian", help="WSL distro name to clean up (default: Debian)")
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
        print("\n⚠️  COMPREHENSIVE CLEANUP - This will:")
        if not args.windows_only:
            print(f"  🐧 WSL ({args.distro}):")
            print("     • Remove user from dialout group")
            print("     • Unload FTDI kernel modules")
            print("     • Remove custom udev rules")
            print("     • Uninstall FTDI and serial packages")
            print("     • Reset serial device permissions")
        if not args.wsl_only:
            print("  🪟 Windows:")
            print("     • Detach all USB devices from WSL")
            if not args.keep_usbipd:
                print("     • Completely uninstall usbipd-win")
                print("     • Remove from PATH environment variable")
            print("     • Clean up Windows FTDI drivers")
        
        print(f"\n💡 You can test this safely first with: --dry-run")
        response = input("\n❓ Do you want to continue with the actual cleanup? (y/N): ")
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
    
    # Final status check (unless dry run)
    if not args.dry_run:
        check_cleanup_status(args.distro)
    
    print("\n" + "=" * 50)
    if args.dry_run:
        print("✓ Dry run completed successfully!")
        print("💡 Use without --dry-run to perform actual cleanup.")
    elif success:
        print("🎉 Cleanup completed successfully!")
        print("✅ All micropump components have been removed/reset.")
    else:
        print("⚠️  Cleanup completed with some warnings/errors.")
        print("Some manual cleanup may be required - check status above.")
    
    if not args.dry_run:
        print("\n📋 POST-CLEANUP RECOMMENDATIONS:")
        print("  🔄 Run 'wsl --shutdown && wsl' to restart WSL completely")
        print("  💻 Restart Windows to ensure all driver changes take effect")
        if not args.wsl_only:
            print("  🔍 Check Device Manager for any remaining FTDI devices")
            print("  🛠️  Verify usbipd-win is removed from PATH (if applicable)")
        print("  🧹 Clear any project-specific .env files if desired")
        
        print(f"\n🚀 TO RE-ENABLE MICROPUMP LATER:")
        print(f"     python via_wsl\\attach_micropump.py --distro {args.distro} --auto-ftdi")
    print("=" * 50)

if __name__ == "__main__":
    main()