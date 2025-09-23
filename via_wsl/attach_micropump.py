import argparse
import ctypes
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

GITHUB_RELEASES = "https://github.com/dorssel/usbipd-win/releases/latest/download/usbipd-win_x64.msi"
DEFAULT_MSI_IN_REPO = Path("tools/usbipd-win_x64.msi")  # commit an MSI here if you prefer pinning

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

def ensure_usbipd_available(msi_path: Path | None):
    exe = find_exe_on_path("usbipd")
    if exe:
        return exe

    if not is_admin():
        sys.exit("usbipd not found and install required. Please re-run this script as Administrator.")

    # prefer repo-pinned MSI if present
    if msi_path and msi_path.exists():
        installer = msi_path
        print(f"Using repo MSI: {installer}")
    else:
        # download latest MSI from GitHub Releases
        print("usbipd not found; downloading latest MSI...")
        tmpdir = Path(tempfile.mkdtemp())
        installer = tmpdir / "usbipd-win_x64.msi"
        urllib.request.urlretrieve(GITHUB_RELEASES, installer)

    # silent install
    print("Installing usbipd-win silently...")
    run(["msiexec", "/i", str(installer), "/qn"])
    exe = find_exe_on_path("usbipd")
    if not exe:
        sys.exit("usbipd installation appears to have failed (usbipd not on PATH).")
    return exe

def usbipd_list(usbipd_exe: Path):
    out = run([str(usbipd_exe), "list"]).stdout
    print(out)
    return out

def find_busid(list_output: str, vidpid: str, name_hint: str | None):
    # Prefer VID:PID - exact match
    for line in list_output.splitlines():
        if vidpid.lower() in line.lower():
            m = re.match(r"\s*(\d+-\d+)", line)
            if m:
                return m.group(1)
    # Fallback: name hint (only if VID:PID not found)
    if name_hint:
        for line in list_output.splitlines():
            if name_hint.lower() in line.lower():
                m = re.match(r"\s*(\d+-\d+)", line)
                if m:
                    print(f"Note: Device found by name hint '{name_hint}' instead of VID:PID '{vidpid}'")
                    return m.group(1)
    return None

def ensure_wsl_running(distro: str):
    # Start distro so attach works even if no terminal is open
    result = run(["wsl", "-d", distro, "-e", "true"], check=False)
    if result.returncode != 0:
        error_output = result.stderr + result.stdout
        # Handle UTF-16 encoding issues by removing null bytes
        error_output = error_output.replace('\x00', '')
        # Debug: print the exact error output
        # print(f"DEBUG: error_output = '{repr(error_output)}'")
        if "WSL_E_DISTRO_NOT_FOUND" in error_output or "There is no distribution with the supplied name" in error_output or "no distribution" in error_output:
            print(f"Error: WSL distribution '{distro}' not found.")
            print("Available distributions:")
            list_result = run(["wsl", "-l", "-q"], check=False)
            if list_result.returncode == 0:
                print(list_result.stdout.strip())
            else:
                print("Could not list WSL distributions.")
            return False
        else:
            print(f"Warning: Could not start WSL distribution '{distro}': {error_output}")
            return False
    return True

def bind_and_attach(usbipd_exe: Path, busid: str):
    # Check current status first
    listing = usbipd_list(usbipd_exe)
    
    # Check if device is already attached
    for line in listing.splitlines():
        if busid in line and "Attached" in line:
            print(f"Device {busid} is already attached to WSL.")
            return
    
    # Check if device is already shared
    already_shared = False
    for line in listing.splitlines():
        if busid in line and "Shared" in line:
            already_shared = True
            break
    
    if not already_shared:
        # bind (retry with --force if needed)
        try:
            out = run([str(usbipd_exe), "bind", "--busid", busid], check=False)
            if out.returncode != 0:
                if "Access denied" in (out.stderr + out.stdout):
                    print("Bind failed due to insufficient privileges. Please run as Administrator.")
                    return
                elif "Unknown USB filter" in (out.stderr + out.stdout):
                    print("Binding may be blocked by a filter driver; retrying with --force...")
                    out = run([str(usbipd_exe), "bind", "--busid", busid, "--force"], check=False)
                    if out.returncode != 0 and "Access denied" in (out.stderr + out.stdout):
                        print("Bind with --force failed due to insufficient privileges. Please run as Administrator.")
                        return
        except subprocess.CalledProcessError as e:
            if "Access denied" in str(e):
                print("Bind failed due to insufficient privileges. Please run as Administrator.")
                return
            print("Bind failed; retrying with --force...")
            try:
                run([str(usbipd_exe), "bind", "--busid", busid, "--force"])
            except subprocess.CalledProcessError as e2:
                if "Access denied" in str(e2):
                    print("Bind with --force failed due to insufficient privileges. Please run as Administrator.")
                    return
                raise

    # attach for WSL
    try:
        run([str(usbipd_exe), "attach", "--wsl", "--busid", busid])
        print(f"Successfully attached device {busid} to WSL.")
    except subprocess.CalledProcessError as e:
        if "Access denied" in str(e):
            print("Attach failed due to insufficient privileges. Please run as Administrator.")
            return
        raise

def verify_in_wsl(distro: str, vidpid: str):
    # First, simple check without sudo
    verify_cmd = rf'''
echo "---- Checking USB device recognition ----"
lsusb | grep -i {vidpid.split(":")[0]} || echo "USB device not found in lsusb"

echo "---- Checking for existing serial devices ----"
ls -l /dev/ttyUSB* 2>/dev/null || echo "No /dev/ttyUSB* detected"
ls -l /dev/ttyACM* 2>/dev/null || echo "No /dev/ttyACM* detected"

echo "---- Checking kernel modules ----"
lsmod | grep -E "(usbserial|ftdi_sio)" || echo "FTDI modules not loaded"

echo "---- Recent kernel messages ----"
dmesg | tail -n 10 | grep -E "(usb|tty|ftdi)" || echo "No recent USB/FTDI messages"
'''
    
    print("Checking device status in WSL...")
    res = run(["wsl", "-d", distro, "-e", "bash", "-c", verify_cmd], check=False)
    
    print("WSL Setup Output:")
    print(res.stdout)
    if res.stderr:
        print("WSL Errors/Warnings:")
        print(res.stderr)
    
    # Check if we have serial devices
    serial_check = run(["wsl", "-d", distro, "-e", "bash", "-c", "ls /dev/ttyUSB* /dev/ttyACM* 2>/dev/null | wc -l"], check=False)
    device_count = int(serial_check.stdout.strip()) if serial_check.stdout.strip().isdigit() else 0
    
    if device_count == 0:
        print("\n⚠️  No serial devices found. FTDI drivers may need to be installed.")
        setup_ftdi = input("Would you like to set up FTDI drivers interactively? (y/N): ")
        if setup_ftdi.lower() in ['y', 'yes']:
            return setup_ftdi_drivers_interactive(distro)
        else:
            return False
    else:
        print(f"✅ Found {device_count} serial device(s)")
        return True

def setup_ftdi_drivers_interactive(distro: str):
    """Install FTDI drivers with a single sudo prompt"""
    print(f"\n=== FTDI Driver Setup ===")
    print(f"Installing FTDI drivers and configuring serial device access...")
    print(f"You will be prompted for your sudo password once.")
    print()
    
    # Create a comprehensive setup script
    setup_script = f'''
echo "=== Starting FTDI driver setup ==="
echo "Updating package list..."
apt update

echo "Installing FTDI drivers and development tools..."
apt install -y libftdi1-2 libftdi1-dev python3-serial

echo "Adding user to dialout group for serial port access..."
usermod -a -G dialout $USER

echo "Creating udev rule for FTDI micropump device..."
echo 'SUBSYSTEM=="usb", ATTRS{{idVendor}}=="0403", ATTRS{{idProduct}}=="b4c0", MODE="0666"' > /etc/udev/rules.d/99-ftdi-micropump.rules

echo "Reloading udev rules..."
udevadm control --reload-rules 2>/dev/null || echo "udev reload failed (this is normal in some WSL configurations)"
udevadm trigger 2>/dev/null || echo "udev trigger failed (this is normal in some WSL configurations)"

echo "Loading FTDI kernel modules..."
modprobe ftdi_sio 2>/dev/null || echo "ftdi_sio module load failed (trying alternative approach)"
modprobe usbserial 2>/dev/null || echo "usbserial module load failed (trying alternative approach)"

echo "Forcing USB device recognition..."
echo "0403 b4c0" > /sys/bus/usb-serial/drivers/ftdi_sio/new_id 2>/dev/null || echo "Manual device ID registration failed"

echo "=== FTDI driver setup complete ==="
echo "Note: You may need to log out and back in for group changes to take effect."
'''
    
    try:
        # Run the setup script with sudo in WSL
        print("Running FTDI driver installation (you'll be prompted for password)...")
        result = subprocess.run(
            ["wsl", "-d", distro, "-e", "sudo", "bash", "-c", setup_script],
            check=False
        )
        
        if result.returncode == 0:
            print("✅ FTDI driver installation completed successfully!")
            
            # Give a moment for udev to process
            time.sleep(2)
            
            # Check for serial devices
            print("\nChecking for serial devices...")
            check_cmd = "ls -l /dev/ttyUSB* /dev/ttyACM* 2>/dev/null || echo 'No serial devices found yet'"
            res = run(["wsl", "-d", distro, "-e", "bash", "-c", check_cmd], check=False)
            print(res.stdout)
            
            # Also check if modules are loaded
            print("Checking FTDI kernel modules...")
            module_cmd = "lsmod | grep -E '(usbserial|ftdi_sio)' || echo 'FTDI modules not yet loaded'"
            res = run(["wsl", "-d", distro, "-e", "bash", "-c", module_cmd], check=False)
            print(res.stdout)
            
            # Final device check
            final_check = run(["wsl", "-d", distro, "-e", "bash", "-c", "ls /dev/ttyUSB* /dev/ttyACM* 2>/dev/null | wc -l"], check=False)
            final_count = int(final_check.stdout.strip()) if final_check.stdout.strip().isdigit() else 0
            
            if final_count > 0:
                print(f"\n✅ Success! Found {final_count} serial device(s) after FTDI setup.")
                return True
            else:
                print("\n⚠️  FTDI drivers installed but serial devices not yet available.")
                print("This may require:")
                print("1. Detaching and reattaching the USB device")
                print("2. Restarting WSL: wsl --shutdown && wsl")
                print("3. Logging out and back in to apply group changes")
                return False
        else:
            print(f"❌ FTDI driver installation failed with exit code: {result.returncode}")
            return False
            
    except Exception as e:
        print(f"❌ Failed to install FTDI drivers: {e}")
        return False

def run_wsl_python(distro: str, wsl_script: str, args: list[str]):
    if not wsl_script:
        return
    # Ensure Python exists; then run user script
    cmd = ["wsl", "-d", distro, "-e", "bash", "-lc",
           "command -v python3 >/dev/null || sudo apt-get update && sudo apt-get -y install python3; " +
           "python3 " + repr(wsl_script) + (" " + " ".join(map(repr, args)) if args else "")]
    run(cmd, check=False)

def main():
    parser = argparse.ArgumentParser(description="Bind+attach a USB device to WSL2 and optionally run a WSL Python script.")
    parser.add_argument("--distro", default="Ubuntu", help="WSL distro name (default: Ubuntu)")
    parser.add_argument("--vidpid", default="0403:b4c0", help="USB VID:PID to match (default: 0403:b4c0 for FTDI Micropump)")
    parser.add_argument("--name-hint", default="Micropump", help="Fallback device name hint")
    parser.add_argument("--msi", default=str(DEFAULT_MSI_IN_REPO), help="Path to a vendored usbipd-win MSI (optional)")
    parser.add_argument("--wsl-script", help="Path to Python script inside WSL to run after attach (optional)")
    parser.add_argument("--", dest="script_args", nargs=argparse.REMAINDER, help="Args after -- are passed to the WSL script")
    args = parser.parse_args()

    msi_path = Path(args.msi) if args.msi else None
    usbipd_exe = ensure_usbipd_available(msi_path if msi_path and msi_path.exists() else None)

    # List devices and find BUSID
    listing = usbipd_list(usbipd_exe)
    busid = find_busid(listing, args.vidpid, args.name_hint)
    if not busid:
        sys.exit(f"Could not find device with VID:PID {args.vidpid} or name containing '{args.name_hint}'.")

    print(f"Found device at BUSID {busid}")
    if not ensure_wsl_running(args.distro):
        sys.exit(f"Cannot proceed - WSL distribution '{args.distro}' is not available.")
    bind_and_attach(usbipd_exe, busid)
    
    # Check device status in WSL
    has_serial_devices = verify_in_wsl(args.distro, args.vidpid)
    
    if not has_serial_devices:
        print("\nChecking if device reconnection is needed...")
        print("No serial devices found. Attempting device reconnection...")
        
        # Detach and reattach to trigger driver recognition
        detach_result = run([str(usbipd_exe), "detach", "--busid", busid], check=False)
        if detach_result.returncode == 0:
            print("Device detached. Waiting 3 seconds...")
            time.sleep(3)
            
            attach_result = run([str(usbipd_exe), "attach", "--wsl", "--busid", busid], check=False)
            if attach_result.returncode == 0:
                print("Device reattached. Checking for serial devices...")
                time.sleep(2)
                
                # Verify again after reconnection
                has_serial_devices = verify_in_wsl(args.distro, args.vidpid)
                if has_serial_devices:
                    print("✅ Serial devices now available!")
                else:
                    print("❌ Still no serial devices after reconnection")
                    print("The device may need manual driver installation in WSL.")
            else:
                print(f"Failed to reattach device: {attach_result.stderr}")
        else:
            print(f"Failed to detach device: {detach_result.stderr}")
    else:
        print("✅ Serial devices are available in WSL!")

    # Optional: run your WSL-side controller
    if args.wsl_script:
        run_wsl_python(args.distro, args.wsl_script, args.script_args or [])

    print("All done.")

if __name__ == "__main__":
    main()
