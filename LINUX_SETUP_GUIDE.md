# Linux-First Micropump Setup Guide

## Problem
You're having issues with unsigned FTDI drivers on Windows and need to install them via DOS every time. Linux typically has much better built-in FTDI support.

## Solution: Use Linux Directly

### Option 1: Native Linux Installation
The best solution is to run this on a native Linux system where USB devices work without Windows driver complications.

**Advantages:**
- No driver signing issues
- Built-in FTDI support
- No USB forwarding complexity
- Better real-time performance
- Direct hardware access

### Option 2: Dual Boot Linux
If you need Windows for other tasks, consider dual-booting with Ubuntu.

### Option 3: Linux Live USB/VM with USB Passthrough
You can use a Linux live USB or VM with direct USB access.

## Current Status in WSL

Your WSL environment is properly set up with:
- ✅ FTDI kernel modules loaded (`ftdi_sio`, `usbserial`)
- ✅ Python environment with all libraries
- ✅ USB permissions configured
- ✅ Test scripts ready

**The only missing piece:** The device needs to be visible to Linux.

## Immediate Solutions for WSL

### Solution A: Manual USB Forwarding (if device briefly appears)

If the device appears in Windows Device Manager (even without proper drivers):

1. **In Windows PowerShell as Administrator:**
   ```powershell
   # Install usbipd if not already done
   winget install usbipd
   
   # List devices (look for any device with VID 0403)
   usbipd list
   
   # Bind and attach (replace 1-2 with actual bus-device ID)
   usbipd bind --busid 1-2
   usbipd attach --wsl --busid 1-2
   ```

2. **In WSL:**
   ```bash
   # Check if device appears
   lsusb | grep 0403
   
   # Test with our script
   python test_linux_direct.py
   ```

### Solution B: Force Device Recognition

If the device shows up in Windows but with wrong/missing drivers:

1. **In WSL, try to manually bind the device:**
   ```bash
   # Add the device ID to FTDI driver
   echo "0403 b4c0" | sudo tee /sys/bus/usb-serial/drivers/ftdi_sio/new_id
   
   # Check if ttyUSB device appears
   ls -la /dev/ttyUSB*
   
   # Set permissions
   sudo chmod 666 /dev/ttyUSB*
   ```

### Solution C: Use Different VID/PID

Your pump might have a different Product ID. In Windows Device Manager:

1. Right-click the device → Properties → Details
2. Select "Hardware Ids" 
3. Look for VID_XXXX&PID_XXXX
4. Update the test scripts with the correct IDs

## Long-term Solution: Native Linux

### Recommended Hardware Setup:
1. **Raspberry Pi 4** - Perfect for this application
   - Native Linux
   - Multiple USB ports
   - Can run headless
   - Excellent Python support
   - Cost: ~$50-75

2. **Mini PC with Linux** - More powerful option
   - Intel NUC or similar
   - Native Ubuntu installation
   - Better performance

3. **Laptop/Desktop with Linux** - Full development environment

### Setting up on Native Linux:

```bash
# 1. Update system
sudo apt update && sudo apt upgrade

# 2. Install Python and dependencies
sudo apt install python3 python3-pip python3-venv git

# 3. Install USB libraries
sudo apt install libusb-1.0-0-dev libudev-dev

# 4. Clone your project
git clone https://github.com/oodegard/micropump_controller.git
cd micropump_controller

# 5. Create environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt  # or use conda

# 6. Connect device and test
python test_linux_direct.py
```

## Testing Your Current Setup

Run these commands to test if device forwarding works:

```bash
# 1. Check current USB status
python test_linux_direct.py

# 2. Monitor USB events (in another terminal)
sudo dmesg -w

# 3. Connect your device in Windows and try forwarding
# Watch for USB connection messages in dmesg
```

## Alternative: Windows with WSL USB Binding

If you must stay with WSL, try this PowerShell script to force device sharing:

```powershell
# Find any FTDI device and force attach
$devices = usbipd list | Select-String "0403"
foreach ($device in $devices) {
    $busid = ($device -split '\s+')[0]
    Write-Host "Trying to attach device $busid"
    try {
        usbipd bind --busid $busid --force
        usbipd attach --wsl --busid $busid
        Write-Host "Success with $busid"
        break
    } catch {
        Write-Host "Failed with $busid"
    }
}
```

## Debugging Checklist

1. **Physical Connection**
   - [ ] USB cable working (try different cable)
   - [ ] Device powered on
   - [ ] Different USB port

2. **Windows Detection**
   - [ ] Device appears in Device Manager
   - [ ] Note the VID/PID from Device Manager
   - [ ] Try installing FTDI VCP drivers

3. **WSL Forwarding**
   - [ ] usbipd-win installed
   - [ ] Running PowerShell as Administrator
   - [ ] WSL is running when attaching

4. **Linux Recognition**
   - [ ] FTDI modules loaded (`lsmod | grep ftdi`)
   - [ ] Device appears in `lsusb`
   - [ ] Serial port created (`ls /dev/ttyUSB*`)

## Next Steps

1. **Immediate:** Try the USB forwarding solutions above
2. **Short-term:** Consider a Linux live USB for testing
3. **Long-term:** Set up native Linux environment for reliable operation

Your Python environment and code are ready - you just need the device to be visible to Linux!
