import argparse
import json
import os
import ctypes
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

GITHUB_API_URL = "https://api.github.com/repos/dorssel/usbipd-win/releases/latest"
DEFAULT_MSI_IN_REPO = Path("tools/usbipd-win_x64.msi")  # commit an MSI here if you prefer pinning

ENV_PATH = Path(".env")
OPTIONAL_ENV_DEFAULTS = {
    "ARDUINO_VID": "9025", # 0x2341 in decimal
    "ARDUINO_PID": "67",   # 0x0043 in decimal
}


def _ensure_env_file(required_values, optional_defaults=None):
    """Update or create .env with required values and optional defaults."""
    optional_defaults = optional_defaults or {}
    if ENV_PATH.exists():
        try:
            with open(ENV_PATH, "r", encoding="utf-8") as handle:
                lines = handle.read().splitlines()
        except UnicodeDecodeError:
            with open(ENV_PATH, "r") as handle:
                lines = handle.read().splitlines()
    else:
        lines = ["# .env file for micropump_controller project"]

    existing_keys = set()
    updated_lines = []

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in line:
            updated_lines.append(line)
            continue

        key, _, _ = line.partition("=")
        key = key.strip()
        existing_keys.add(key)

        if key in required_values:
            updated_lines.append(f"{key}={required_values[key]}")
        else:
            updated_lines.append(line)

    for key, value in required_values.items():
        if key not in existing_keys:
            if updated_lines and updated_lines[-1] != "":
                updated_lines.append("")
            updated_lines.append(f"{key}={value}")
            existing_keys.add(key)

    for key, value in optional_defaults.items():
        if key not in existing_keys:
            if updated_lines and updated_lines[-1] != "":
                updated_lines.append("")
            updated_lines.append(f"{key}={value}")
            existing_keys.add(key)

    with open(ENV_PATH, "w", encoding="utf-8") as handle:
        handle.write("\n".join(updated_lines) + "\n")

def _read_env_value(key):
    """Read a single key from the local .env file."""
    if not ENV_PATH.exists():
        return None
    try:
        with open(ENV_PATH, "r", encoding="utf-8") as handle:
            lines = handle.readlines()
    except UnicodeDecodeError:
        with open(ENV_PATH, "r") as handle:
            lines = handle.readlines()
    prefix = f"{key}="
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith(prefix):
            return stripped.split("=", 1)[1]
    return None

def _prompt_for_wsl_distro():
    """Prompt the user to select an installed WSL distribution."""
    result = subprocess.run(["wsl", "-l", "-q"], capture_output=True, text=True, check=False)
    distros = []
    for raw_line in result.stdout.splitlines():
        cleaned = raw_line.replace("\x00", "").strip()
        if cleaned:
            distros.append(cleaned)
    if not distros:
        sys.exit("No WSL distributions found. Install one from the Microsoft Store and try again.")

    print("Available WSL distributions:")
    for idx, name in enumerate(distros, 1):
        print(f"  [{idx}] {name}")

    prompt = f"Select WSL distro [1-{len(distros)}]: "
    while True:
        choice = input(prompt).strip()
        if choice.isdigit():
            index = int(choice)
            if 1 <= index <= len(distros):
                return distros[index - 1]
        print("Invalid selection. Please try again by entering the list number.")

def _vidpid_to_decimal(vidpid):
    """Convert a VID:PID string to decimal strings expected in .env."""
    parts = vidpid.split(":")
    if len(parts) != 2:
        raise ValueError(f"Invalid VID:PID format: {vidpid}")
    vid_part, pid_part = parts
    try:
        vid_value = str(int(vid_part, 16))
        pid_value = str(int(pid_part, 16))
    except ValueError as exc:
        raise ValueError(f"VID:PID should be hexadecimal, got {vidpid}") from exc
    return vid_value, pid_value

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        return False

def elevate_to_admin():
    """Re-launch the script with administrator privileges"""
    if is_admin():
        return  # Already admin
    
    print("Administrator privileges required. Attempting to elevate...")
    
    # Get the current script path and arguments
    script_path = sys.argv[0]
    args = sys.argv[1:]
    
    # Prepare the command for elevation
    # Use ShellExecute with "runas" verb to trigger UAC prompt
    try:
        import ctypes
        ctypes.windll.shell32.ShellExecuteW(
            None,  # parent window handle
            "runas",  # operation - triggers UAC
            sys.executable,  # Python executable
            f'"{script_path}" {" ".join(args)}',  # script and args
            None,  # working directory
            1  # show window normally
        )
        # Exit the current non-elevated process
        sys.exit(0)
    except Exception as e:
        print(f"Failed to elevate to administrator: {e}")
        sys.exit("Please manually run this script as Administrator.")

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

def get_latest_usbipd_download_url() -> str:
    """Get the download URL for the latest usbipd-win x64 MSI from GitHub API."""
    try:
        print("Checking for latest usbipd-win release...")
        
        # Set timeout for the API request
        socket.setdefaulttimeout(30)
        
        with urllib.request.urlopen(GITHUB_API_URL) as response:
            data = json.loads(response.read().decode('utf-8'))
        
        # Look for the x64 MSI asset
        for asset in data.get('assets', []):
            name = asset.get('name', '').lower()
            if 'x64.msi' in name and 'usbipd-win' in name:
                url = asset.get('browser_download_url')
                if url:
                    print(f"Found latest release: {asset.get('name')} (v{data.get('tag_name', 'unknown')})")
                    return url
        
        # Fallback - construct URL based on tag name if assets parsing fails
        tag_name = data.get('tag_name', '')
        if tag_name:
            fallback_url = f"https://github.com/dorssel/usbipd-win/releases/download/{tag_name}/usbipd-win_{tag_name.lstrip('v')}_x64.msi"
            print(f"Using fallback URL pattern for {tag_name}")
            return fallback_url
        
        raise Exception("Could not find x64 MSI asset in release")
        
    except Exception as e:
        print(f"WARNING: Failed to get latest release info: {e}")
        # Ultimate fallback to a known working version
        fallback_url = "https://github.com/dorssel/usbipd-win/releases/download/v5.2.0/usbipd-win_5.2.0_x64.msi"
        print(f"Using hardcoded fallback: {fallback_url}")
        return fallback_url
    finally:
        socket.setdefaulttimeout(None)

def download_with_progress(url: str, destination: Path) -> bool:
    """Download file with progress indication and proper error handling."""
    try:
        print(f"Downloading from: {url}")
        print(f"Saving to: {destination}")
        print("Download progress: ", end="", flush=True)
        
        def progress_callback(block_num, block_size, total_size):
            if total_size > 0:
                percent = min(100, (block_num * block_size * 100) // total_size)
                # Show progress every 10%
                if percent % 10 == 0 and block_num * block_size < total_size:
                    print(f"{percent}%", end="", flush=True)
                    if percent < 100:
                        print("...", end="", flush=True)
        
        # Set a reasonable timeout for the download
        import socket
        socket.setdefaulttimeout(60)  # 60 second timeout
        
        urllib.request.urlretrieve(url, destination, progress_callback)
        print(" 100% - Download completed!")
        return True
        
    except Exception as e:
        print(f"\nERROR Download failed: {e}")
        return False
    finally:
        # Reset timeout
        socket.setdefaulttimeout(None)

def ensure_usbipd_available(msi_path: Path | None):
    exe = find_exe_on_path("usbipd")
    if exe:
        return exe

    if not is_admin():
        elevate_to_admin()  # This will re-launch with admin privileges

    # prefer repo-pinned MSI if present
    if msi_path and msi_path.exists():
        installer = msi_path
        print(f"Using repo MSI: {installer}")
    else:
        # download latest MSI from GitHub Releases with retry logic
        print("usbipd not found; downloading latest MSI...")
        tmpdir = Path(tempfile.mkdtemp())
        installer = tmpdir / "usbipd-win_x64.msi"
        
        # Get the latest download URL
        download_url = get_latest_usbipd_download_url()
        
        # Try downloading with retries
        max_retries = 3
        for attempt in range(max_retries):
            if attempt > 0:
                print(f"\nRetry attempt {attempt + 1}/{max_retries}...")
                time.sleep(2 * attempt)  # exponential backoff
            
            if download_with_progress(download_url, installer):
                break
        else:
            sys.exit("ERROR Failed to download usbipd-win after multiple attempts. Please check your internet connection.")

    # silent install
    print("Installing usbipd-win silently...")
    try:
        result = run(["msiexec", "/i", str(installer), "/qn", "/norestart"], check=False)
        if result.returncode != 0:
            print(f"WARNING: MSI installation returned code {result.returncode}")
            if result.stderr:
                print(f"Error details: {result.stderr}")
    except Exception as e:
        print(f"ERROR Installation error: {e}")
        sys.exit("usbipd installation failed.")
    
    # Give the installation a moment to complete
    print("Waiting for installation to complete...")
    time.sleep(3)
    
    exe = find_exe_on_path("usbipd")
    if not exe:
        sys.exit("usbipd installation appears to have failed (usbipd not on PATH).")
    
    print(f"SUCCESS: usbipd installed successfully at: {exe}")
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

def restart_wsl_distro(distro: str):
    print(f"Restarting WSL distro '{distro}'...")
    run(["wsl", "-t", distro], check=False)
    time.sleep(1)
    # Start again
    ensure_wsl_running(distro)

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
        print("\nWARNING: No serial devices found. FTDI drivers may need to be installed.")
        # Allow non-interactive behavior if PUMP_NON_INTERACTIVE=1
        if os.getenv("PUMP_NON_INTERACTIVE") == "1":
            print("Skipping interactive FTDI setup because PUMP_NON_INTERACTIVE=1")
            return False
        setup_ftdi = input("Would you like to set up FTDI drivers interactively< (y/N): ")
        if setup_ftdi.lower() in ['y', 'yes']:
            return setup_ftdi_drivers_interactive(distro)
        else:
            return False
    else:
        print(f"SUCCESS: Found {device_count} serial device(s)")
        return True

def setup_ftdi_drivers_interactive(distro: str):
    """Install FTDI drivers with proper permissions - ONE-TIME sudo setup for permanent access"""
    print(f"\n=== FTDI Driver Setup ===")
    print(f"Installing FTDI drivers and configuring permanent serial device access...")
    print(f"This is a ONE-TIME setup. After this, no sudo will be needed to run the pump.")
    print(f"You will be prompted for your sudo password once.")
    print()
    
    # Get current user for proper group assignment
    user_check = run(["wsl", "-d", distro, "-e", "whoami"], check=False)
    current_user = user_check.stdout.strip() if user_check.returncode == 0 else "user"
    print(f"Setting up permissions for user: {current_user}")
    
    # Create a comprehensive setup script that ensures permanent access
    setup_script = f'''
set -e
export DEBIAN_FRONTEND=noninteractive
echo "=== Starting FTDI driver setup ==="

# Get the actual username (not from $USER which might be wrong in sudo context)
ACTUAL_USER="{current_user}"
echo "Configuring for user: $ACTUAL_USER"

echo "Updating package list..."
apt-get update -yq

echo "Installing FTDI drivers and essential packages..."
apt-get install -yq libftdi1-2 libftdi1-dev python3-serial usbutils

echo "Adding user $ACTUAL_USER to dialout group for permanent serial port access..."
usermod -a -G dialout "$ACTUAL_USER"

echo "Creating comprehensive udev rules for FTDI devices..."
cat > /etc/udev/rules.d/99-ftdi-micropump.rules << 'EOF'
# FTDI Micropump Device Rules - Allows access without sudo
# VID:0403 PID:B4C0 - Bartels Micropump
SUBSYSTEM=="usb", ATTRS{{idVendor}}=="0403", ATTRS{{idProduct}}=="b4c0", MODE="0666", GROUP="dialout"
# Generic FTDI devices
SUBSYSTEM=="usb", ATTRS{{idVendor}}=="0403", MODE="0664", GROUP="dialout"
# TTY devices created by FTDI
KERNEL=="ttyUSB[0-9]*", ATTRS{{idVendor}}=="0403", MODE="0666", GROUP="dialout"
KERNEL=="ttyACM[0-9]*", ATTRS{{idVendor}}=="0403", MODE="0666", GROUP="dialout"
# Ensure all USB serial devices are accessible
SUBSYSTEM=="tty", KERNEL=="ttyUSB[0-9]*", MODE="0666", GROUP="dialout"
SUBSYSTEM=="tty", KERNEL=="ttyACM[0-9]*", MODE="0666", GROUP="dialout"
EOF

echo "Setting proper permissions on udev rules..."
chmod 644 /etc/udev/rules.d/99-ftdi-micropump.rules

echo "Loading FTDI kernel modules..."
modprobe usbserial 2>/dev/null || echo "usbserial module already loaded or not needed"
modprobe ftdi_sio 2>/dev/null || echo "ftdi_sio module already loaded or not needed"

echo "Adding FTDI device ID to driver..."
echo "0403 b4c0" > /sys/bus/usb-serial/drivers/ftdi_sio/new_id 2>/dev/null || echo "Device ID already registered or registration not needed"

echo "Reloading udev rules..."
udevadm control --reload-rules 2>/dev/null || echo "udev reload not available (normal in WSL)"
udevadm trigger 2>/dev/null || echo "udev trigger not available (normal in WSL)"

echo "Setting up persistent module loading..."
cat > /etc/modules-load.d/ftdi.conf << 'EOF'
# Load FTDI modules at boot
usbserial
ftdi_sio
EOF

echo "Applying immediate permissions to existing devices..."
for device in /dev/ttyUSB* /dev/ttyACM*; do
    if [ -c "$device" ]; then
        echo "Setting permissions on $device"
        chmod 666 "$device"
        chgrp dialout "$device" 2>/dev/null || true
    fi
done

echo "=== FTDI driver setup complete ==="
echo "SUCCESS: User $ACTUAL_USER added to dialout group"
echo "SUCCESS: Udev rules installed for automatic device permissions"
echo "SUCCESS: FTDI kernel modules loaded"
echo "SUCCESS: No sudo will be required for future pump operations"
'''
    
    try:
        # Run the setup script with sudo in WSL
        print("Running FTDI driver installation (sudo may prompt for password)...")
        sudo_pass = os.environ.get("PUMP_WSL_SUDO_PASS", "")
        if sudo_pass:
            # Provide password non-interactively via stdin
            result = subprocess.run(
                ["wsl", "-d", distro, "-e", "sudo", "-S", "bash", "-c", setup_script],
                input=sudo_pass + "\n",
                text=True,
                capture_output=True,
                check=False,
            )
        else:
            result = subprocess.run(
                ["wsl", "-d", distro, "-e", "sudo", "bash", "-c", setup_script],
                check=False
            )
        
        if result.returncode == 0:
            print("SUCCESS: FTDI driver installation completed successfully!")
            
            # Validate group membership and permissions 
            print("\n=== Validating Setup ===")
            
            # Force group membership refresh (newgrp simulation)
            print("Refreshing group membership...")
            group_refresh = f"""
# Check if user is in dialout group
if groups {current_user} | grep -q dialout; then
    echo "SUCCESS: User {current_user} is now in dialout group"
else
    echo "WARNING: Group membership may need WSL restart"
fi

# List current groups
echo "Current groups for {current_user}:"
groups {current_user}

# Check udev rules
if [ -f /etc/udev/rules.d/99-ftdi-micropump.rules ]; then
    echo "SUCCESS: Udev rules installed"
else
    echo "WARNING: Udev rules missing"
fi

# Check modules
if lsmod | grep -q ftdi_sio; then
    echo "SUCCESS: FTDI kernel modules loaded"
else
    echo "INFO  FTDI modules will load when device is attached"
fi
"""
            
            validation_result = run(["wsl", "-d", distro, "-e", "bash", "-c", group_refresh], check=False)
            print(validation_result.stdout)
            
            # Give a moment for udev to process
            time.sleep(2)
            
            # Check for serial devices and their permissions
            print("\nChecking for serial devices and permissions...")
            check_cmd = """
for device in /dev/ttyUSB* /dev/ttyACM*; do
    if [ -c "$device" ]; then
        echo "Device: $device"
        ls -l "$device"
        echo "Permissions: $(stat -c '%A (%a)' "$device")"
        echo "Group: $(stat -c '%G' "$device")"
        echo ""
    fi
done
if ! ls /dev/ttyUSB* /dev/ttyACM* >/dev/null 2>&1; then
    echo "No serial devices found yet - this is normal if micropump isn't attached"
fi
"""
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
                print(f"\nSUCCESS: Success! Found {final_count} serial device(s) after FTDI setup.")
                # Test permissions without sudo
                print("\n=== Testing Permissions (No Sudo Required) ===")
                test_result = test_serial_access_no_sudo(distro)
                if test_result:
                    print("Congrats Perfect! Pump can now run without sudo.")
                else:
                    print("WARNING: May need WSL restart for group changes to take full effect.")
                    print("NOTE Try: wsl --shutdown && wsl")
                return True
            else:
                print("\nWARNING: FTDI drivers installed but serial devices not yet available.")
                print("This may require:")
                print("1. Detaching and reattaching the USB device")
                print("2. Restarting WSL: wsl --shutdown && wsl")
                print("3. Logging out and back in to apply group changes")
                return False
        else:
            print(f"ERROR FTDI driver installation failed with exit code: {result.returncode}")
            return False
            
    except Exception as e:
        print(f"ERROR Failed to install FTDI drivers: {e}")
        return False


def test_serial_access_no_sudo(distro: str) -> bool:
    """Test that serial devices can be accessed without sudo after setup"""
    test_script = '''
# Test serial access without sudo
import os
import stat
import grp
import pwd

def check_device_access(device_path):
    """Check if current user can access device without sudo"""
    if not os.path.exists(device_path):
        return False, f"Device {device_path} does not exist"
    
    try:
        # Check file permissions
        st = os.stat(device_path)
        mode = stat.filemode(st.st_mode)
        
        # Check if readable/writable by owner, group, or other
        uid = os.getuid()
        gid = os.getgid()
        
        # Get file owner and group
        file_uid = st.st_uid  
        file_gid = st.st_gid
        
        # Check permissions
        can_read = False
        can_write = False
        
        # Owner permissions
        if uid == file_uid:
            can_read = bool(st.st_mode & stat.S_IRUSR)
            can_write = bool(st.st_mode & stat.S_IWUSR)
        # Group permissions  
        elif gid == file_gid or file_gid in os.getgroups():
            can_read = bool(st.st_mode & stat.S_IRGRP)
            can_write = bool(st.st_mode & stat.S_IWGRP)
        # Other permissions
        else:
            can_read = bool(st.st_mode & stat.S_IROTH)
            can_write = bool(st.st_mode & stat.S_IWOTH)
        
        if can_read and can_write:
            # Try to actually open the device
            try:
                with open(device_path, 'r+b', 0):
                    pass
                return True, f"SUCCESS: {device_path}: Full access confirmed"
            except PermissionError:
                return False, f"ERROR {device_path}: Permission denied despite file mode {mode}"
            except Exception as e:
                return True, f"WARNING: {device_path}: Accessible but device busy ({e})"
        else:
            return False, f"ERROR {device_path}: Insufficient permissions {mode}"
            
    except Exception as e:
        return False, f"ERROR {device_path}: Error checking access - {e}"

# Find and test all serial devices
devices_tested = 0
devices_accessible = 0

import glob
for device_pattern in ["/dev/ttyUSB*", "/dev/ttyACM*"]:
    for device in glob.glob(device_pattern):
        devices_tested += 1
        success, msg = check_device_access(device)
        print(msg)
        if success:
            devices_accessible += 1

if devices_tested == 0:
    print("INFO  No serial devices found to test")
elif devices_accessible == devices_tested:
    print(f"Congrats SUCCESS: All {devices_accessible}/{devices_tested} serial devices accessible without sudo")
else:
    print(f"WARNING: {devices_accessible}/{devices_tested} serial devices accessible")

# Check group membership
import subprocess
try:
    groups_result = subprocess.run(["groups"], capture_output=True, text=True)
    if "dialout" in groups_result.stdout:
        print("SUCCESS: User is in dialout group")
    else:
        print("ERROR User not in dialout group - may need WSL restart")
        print(f"Current groups: {groups_result.stdout.strip()}")
except Exception as e:
    print(f"Could not check groups: {e}")
'''
    
    print("Testing serial device access without sudo...")
    try:
        result = run(["wsl", "-d", distro, "-e", "python3", "-c", test_script], check=False)
        print(result.stdout)
        
        # Return True if we see success message
        return "SUCCESS: All" in result.stdout or "Full access confirmed" in result.stdout
        
    except Exception as e:
        print(f"Permission test failed: {e}")
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
    parser.add_argument("--vidpid", default="0403:b4c0", help="USB VID:PID to match (default: 0403:b4c0 for FTDI Micropump)")
    parser.add_argument("--distro", help="Target WSL distribution (overrides .env and interactive selection)")
    parser.add_argument("--name-hint", default="Micropump", help="Fallback device name hint")
    parser.add_argument("--msi", default=str(DEFAULT_MSI_IN_REPO), help="Path to a vendored usbipd-win MSI (optional)")
    parser.add_argument("--wsl-script", help="Path to Python script inside WSL to run after attach (optional)")
    parser.add_argument("--auto-ftdi", action="store_true", help="Attempt FTDI driver setup automatically (will prompt for sudo password in WSL)")
    parser.add_argument("--", dest="script_args", nargs=argparse.REMAINDER, help="Args after -- are passed to the WSL script")
    args = parser.parse_args()

    try:
        pump_vid_dec, pump_pid_dec = _vidpid_to_decimal(args.vidpid)
    except ValueError as exc:
        sys.exit(str(exc))

    distro = args.distro or _read_env_value("WSL_DISTRO")
    if not distro:
        distro = _prompt_for_wsl_distro()

    msi_path = Path(args.msi) if args.msi else None
    usbipd_exe = ensure_usbipd_available(msi_path if msi_path and msi_path.exists() else None)

    # List devices and find BUSID
    listing = usbipd_list(usbipd_exe)
    busid = find_busid(listing, args.vidpid, args.name_hint)
    if not busid:
        sys.exit(f"Could not find device with VID:PID {args.vidpid} or name containing '{args.name_hint}'.")

    print(f"Found device at BUSID {busid}")
    if not ensure_wsl_running(distro):
        sys.exit(f"Cannot proceed - WSL distribution '{distro}' is not available.")

    _ensure_env_file(
        {
            "WSL_DISTRO": distro,
            "PUMP_VID": pump_vid_dec,
            "PUMP_PID": pump_pid_dec,
        },
        OPTIONAL_ENV_DEFAULTS,
    )
    print("Saved WSL settings to .env")

    bind_and_attach(usbipd_exe, busid)
    
    # Check device status in WSL
    has_serial_devices = verify_in_wsl(distro, args.vidpid)

    # If no serial devices yet and auto-ftdi requested, try FTDI setup once
    if not has_serial_devices and args.auto_ftdi:
        print("\nAuto-installing FTDI support (non-interactive prompt flow)...")
        if setup_ftdi_drivers_interactive(distro):
            # Re-verify after FTDI install
            has_serial_devices = verify_in_wsl(distro, args.vidpid)
            if not has_serial_devices:
                # Try restarting the distro to apply group changes and module loads
                restart_wsl_distro(distro)
                has_serial_devices = verify_in_wsl(distro, args.vidpid)
    
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
                has_serial_devices = verify_in_wsl(distro, args.vidpid)
                # If still none and auto-ftdi requested, try FTDI install as last resort
                if not has_serial_devices and args.auto_ftdi:
                    print("\nAuto-installing FTDI support after reconnection...")
                    if setup_ftdi_drivers_interactive(distro):
                        has_serial_devices = verify_in_wsl(distro, args.vidpid)
                        if not has_serial_devices:
                            restart_wsl_distro(distro)
                            # Reattach after restart to ensure kernel binds
                            run([str(usbipd_exe), "attach", "--wsl", "--busid", busid], check=False)
                            time.sleep(2)
                            has_serial_devices = verify_in_wsl(distro, args.vidpid)
                if has_serial_devices:
                    print("SUCCESS: Serial devices now available!")
                else:
                    print("ERROR Still no serial devices after reconnection")
                    print("The device may need manual driver installation in WSL.")
            else:
                print(f"Failed to reattach device: {attach_result.stderr}")
        else:
            print(f"Failed to detach device: {detach_result.stderr}")
    else:
        print("SUCCESS: Serial devices are available in WSL!")

    # Optional: run your WSL-side controller
    if args.wsl_script:
        run_wsl_python(distro, args.wsl_script, args.script_args or [])

    print("All done.")

if __name__ == "__main__":
    main()
