# WSL USB Setup Guide for Bartels Micropump

## Problem
WSL (Windows Subsystem for Linux) doesn't have direct access to USB devices by default. You need to forward the USB device from Windows to WSL.

## Solution: USB/IP forwarding

### Step 1: Install USBIPD on Windows
1. Download and install `usbipd-win` from the Windows side:
   - Go to: https://github.com/dorssel/usbipd-win/releases
   - Download the latest `.msi` file
   - Install it on Windows

### Step 2: Install USB/IP tools in WSL (Ubuntu)
Run these commands in your WSL terminal:

```bash
sudo apt update
sudo apt install linux-tools-generic hwdata
sudo update-alternatives --install /usr/local/bin/usbip usbip /usr/lib/linux-tools/*-generic/usbip 20
```

### Step 3: Find and forward the USB device

#### On Windows (PowerShell as Administrator):
1. Open PowerShell as Administrator
2. List USB devices:
   ```
   usbipd wsl list
   ```
3. Look for your Bartels micropump (should show VID:PID 0403:B4C0)
4. Bind the device (replace BUSID with the actual bus ID):
   ```
   usbipd wsl bind --busid <BUSID>
   ```
5. Forward the device to WSL:
   ```
   usbipd wsl attach --busid <BUSID>
   ```

#### Alternative: One-time attach (doesn't persist across reboots):
```
usbipd wsl attach --busid <BUSID> --auto-attach
```

### Step 4: Verify in WSL
Back in WSL, run:
```bash
lsusb
```
You should now see the Bartels micropump listed.

### Step 5: Set up automatic permissions
Create a persistent udev rule:
```bash
echo 'SUBSYSTEM=="usb", ATTR{idVendor}=="0403", ATTR{idProduct}=="b4c0", MODE="0666", GROUP="plugdev"' | sudo tee /etc/udev/rules.d/99-bartels-pump.rules
sudo udevadm control --reload-rules
```

### Step 6: Test the connection
```bash
python test_connection.py
```

## Troubleshooting

### If the device doesn't appear in Windows PowerShell:
1. Make sure the micropump is powered on and connected
2. Check Windows Device Manager for the device
3. Install the FTDI drivers if needed (files in hardware/drivers/)

### If WSL can't see the device after forwarding:
1. Try detaching and reattaching:
   ```
   usbipd wsl detach --busid <BUSID>
   usbipd wsl attach --busid <BUSID>
   ```
2. Restart WSL:
   ```
   wsl --shutdown
   ```

### For persistent setup:
Add the `--auto-attach` flag when binding to automatically forward the device when WSL starts:
```
usbipd wsl bind --busid <BUSID> --auto-attach
```

## Alternative: Use Windows Python directly
If USB forwarding proves problematic, consider running the Python code directly on Windows:
1. Install Python on Windows
2. Install the same dependencies (usbx, etc.)
3. Run the micropump control from Windows
