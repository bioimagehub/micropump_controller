# AI Assistant Instructions: Windows USB Forwarding Setup for Bartels Micropump

## Context for AI Assistant

You are helping a user set up USB forwarding from Windows to WSL for a **Bartels micropump controller**. The device uses FTDI USB-to-serial conversion and needs to be forwarded to WSL where a Python controller is waiting.

**Target Device:**
- **Vendor ID (VID):** 0x0403 (FTDI)
- **Product ID (PID):** 0xB4C0 (Default for Bartels, may vary)
- **Device Type:** USB-to-Serial converter for micropump control
- **Expected Names:** May appear as "USB Serial Port", "FTDI", "Bartels", or "Unknown Device"

## Step-by-Step Instructions to Give the User

### Step 1: Install USB/IP Tools (if not already installed)

```powershell
# Open PowerShell as Administrator and run:
winget install --id usbipd-win --source winget

# Alternative if winget fails:
# Download from: https://github.com/dorssel/usbipd-win/releases
# Install the .msi file manually
```

### Step 2: Connect and Identify the Device

1. **Physically connect** the Bartels micropump to a USB port
2. **Open PowerShell as Administrator** (CRITICAL - must be Admin!)
3. **List all USB devices:**

```powershell
usbipd list
```

**Help user identify their device:** Look for:
- Devices with VID `0403` (FTDI vendor)
- Names containing "FTDI", "Serial", "Bartels", or "USB Serial Port"
- Devices marked as "Not shared" 
- Unknown devices that appeared when plugging in the pump

**Example output:**
```
BUSID  VID:PID    DEVICE                                STATE
1-1    0403:b4c0  USB Serial Port (COM3)               Not shared
2-3    0403:6001  FTDI USB Serial Device               Not shared
```

### Step 3: Bind the Device

Replace `X-X` with the actual BUSID from step 2:

```powershell
# Bind the device (makes it shareable)
usbipd bind --busid X-X

# Example:
# usbipd bind --busid 1-1
```

**Expected result:** Device state should change from "Not shared" to "Shared"

### Step 4: Attach to WSL

```powershell
# Attach device to WSL
usbipd attach --wsl --busid X-X

# Example:
# usbipd attach --wsl --busid 1-1
```

**Expected result:** Device state should change to "Attached"

### Step 5: Verify in WSL

Have the user switch to their WSL terminal and run:

```bash
# Check if device appears in USB list
lsusb | grep 0403

# Check if serial device was created
ls -la /dev/ttyUSB*

# Expected output:
# Bus 001 Device 002: ID 0403:b4c0 Future Technology Devices International, Ltd
# /dev/ttyUSB0
```

### Step 6: Test the Connection

In WSL, run the pump test:

```bash
conda activate pump-ctrl
python test_pulse.py
```

## Troubleshooting Guide for AI Assistant

### Problem: "Access denied" or permission errors
**Solution:**
```powershell
# Ensure PowerShell is running as Administrator
# Right-click PowerShell → "Run as Administrator"
```

### Problem: Device not found in `usbipd list`
**Solutions:**
1. **Check Device Manager:**
   ```
   Win + X → Device Manager
   Look under "Ports (COM & LPT)" or "Universal Serial Bus controllers"
   ```
2. **Try different USB port**
3. **Replug the device**
4. **Check if Windows needs drivers**

### Problem: `usbipd` command not found
**Solution:**
```powershell
# Reinstall usbipd-win
winget uninstall usbipd-win
winget install usbipd-win
# Restart PowerShell as Administrator
```

### Problem: Device shows as "Unknown Device" 
**This is often normal!** Proceed with binding anyway:
```powershell
# Unknown devices may work fine - try binding the BUSID
usbipd bind --busid X-X
usbipd attach --wsl --busid X-X
```

### Problem: "bind" command fails
**Solutions:**
1. **Stop any programs that might be using the device:**
   - Close Device Manager
   - Close any serial terminal programs
   - Check Task Manager for programs using COM ports

2. **Force unbind first:**
   ```powershell
   usbipd unbind --busid X-X
   usbipd bind --busid X-X
   ```

### Problem: Device attaches but doesn't appear in WSL
**Solutions:**
1. **Detach and reattach:**
   ```powershell
   usbipd detach --busid X-X
   usbipd attach --wsl --busid X-X
   ```

2. **Check WSL is running:**
   ```powershell
   wsl --status
   ```

3. **Try attaching to specific WSL distribution:**
   ```powershell
   usbipd attach --wsl --distribution Ubuntu --busid X-X
   ```

## Commands Reference for AI

### Essential Commands:
```powershell
# List devices
usbipd list

# Bind device (make shareable)
usbipd bind --busid X-X

# Attach to WSL
usbipd attach --wsl --busid X-X

# Detach from WSL
usbipd detach --busid X-X

# Unbind device
usbipd unbind --busid X-X
```

### Verification Commands (WSL side):
```bash
# Check USB devices
lsusb

# Look for FTDI device specifically
lsusb | grep 0403

# Check serial devices
ls -la /dev/ttyUSB* /dev/ttyACM*

# Check device permissions
ls -la /dev/ttyUSB0

# Test communication
python test_pulse.py
```

## Success Indicators

✅ **Device appears in `usbipd list`**  
✅ **Bind command succeeds (device shows "Shared")**  
✅ **Attach command succeeds (device shows "Attached")**  
✅ **Device appears in WSL `lsusb` output**  
✅ **Serial device `/dev/ttyUSB0` (or similar) created in WSL**  
✅ **Python test script connects and runs pulse**  

## Important Notes for AI

1. **Administrator privileges are REQUIRED** - emphasize this strongly
2. **The device may appear as "Unknown Device"** - this is often normal
3. **BUSID format is like `1-1`, `2-3`, etc.** - not just numbers
4. **Different PID values are common** - not all Bartels devices use 0xB4C0
5. **USB 2.0 vs 3.0 ports may behave differently** - try both if issues occur
6. **Device names vary** - could be "USB Serial", "FTDI", "Bartels", or "Unknown"

The goal is to get the device from Windows Device Manager into WSL where it appears as `/dev/ttyUSB0` and can be used by the Python controller.
