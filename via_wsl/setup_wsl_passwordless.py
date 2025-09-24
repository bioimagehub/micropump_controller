#!/usr/bin/env python3
"""Setup passwordless sudo for FTDI operations in WSL."""

import subprocess
import sys

def setup_passwordless_ftdi(distro="Debian"):
    """Set up passwordless sudo for FTDI-related operations."""
    
    print(f"🔧 Setting up passwordless sudo for FTDI operations in WSL {distro}")
    print("This will allow automatic FTDI driver installation without password prompts.")
    print()
    
    # Create a sudoers entry that allows passwordless access to specific commands
    sudoers_content = '''# Allow passwordless sudo for FTDI setup commands
%sudo ALL=(ALL) NOPASSWD: /usr/bin/apt-get update
%sudo ALL=(ALL) NOPASSWD: /usr/bin/apt-get install *
%sudo ALL=(ALL) NOPASSWD: /usr/sbin/usermod -a -G dialout *
%sudo ALL=(ALL) NOPASSWD: /usr/bin/tee /etc/udev/rules.d/*
%sudo ALL=(ALL) NOPASSWD: /usr/sbin/udevadm *
%sudo ALL=(ALL) NOPASSWD: /usr/sbin/modprobe *
%sudo ALL=(ALL) NOPASSWD: /usr/bin/tee /sys/bus/usb-serial/drivers/ftdi_sio/new_id
%sudo ALL=(ALL) NOPASSWD: /usr/bin/chmod a+rw /dev/ttyUSB*
%sudo ALL=(ALL) NOPASSWD: /usr/bin/chmod a+rw /dev/ttyACM*
'''
    
    try:
        print("Step 1: Creating sudoers configuration...")
        
        # Write the sudoers content to a temporary file in WSL
        temp_script = f'''
echo '{sudoers_content}' | sudo tee /etc/sudoers.d/90-ftdi-setup > /dev/null
sudo chmod 440 /etc/sudoers.d/90-ftdi-setup
echo "Sudoers configuration created successfully"
'''
        
        result = subprocess.run([
            "wsl", "-d", distro, "-e", "bash", "-c", temp_script
        ], capture_output=False, text=True, check=False)
        
        if result.returncode == 0:
            print("✅ Passwordless sudo configuration created successfully!")
            print()
            print("Now FTDI driver installation will work without password prompts.")
            print("You may need to restart WSL for changes to take full effect:")
            print("  wsl --shutdown")
            print("  wsl -d " + distro)
            return True
        else:
            print("❌ Failed to create sudoers configuration")
            return False
            
    except Exception as e:
        print(f"❌ Error setting up passwordless sudo: {e}")
        return False

def main():
    if len(sys.argv) > 1:
        distro = sys.argv[1]
    else:
        distro = "Debian"  # Default
    
    print("⚠️  This script requires sudo access in WSL to modify sudoers configuration.")
    print("You'll be asked for your password once to set up passwordless operation.")
    
    confirm = input("\nProceed? (y/N): ")
    if confirm.lower() not in ['y', 'yes']:
        print("Setup cancelled.")
        return
    
    if setup_passwordless_ftdi(distro):
        print("\n🎉 Setup complete! Future FTDI installations will be passwordless.")
    else:
        print("\n❌ Setup failed. You'll continue to see password prompts.")

if __name__ == "__main__":
    main()