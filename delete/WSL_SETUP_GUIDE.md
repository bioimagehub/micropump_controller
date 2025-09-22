# Micropump WSL Setup Guide

This guide helps you connect the Bartels micropump to Ubuntu/WSL.

## Current Status

✅ **Completed Setup Steps:**
1. ✅ Conda environment `pump-ctrl` created and activated
2. ✅ USB system libraries installed (`libusb-1.0-0-dev`, `libudev-dev`)
3. ✅ Python libraries installed (`usbx`, `pyusb`, `pyserial`, `python-dotenv`, `pyyaml`)
4. ✅ USB permissions configured (user added to dialout group, udev rules created)
5. ✅ Test script ready (`test_connection.py`)
6. ✅ PowerShell USB forwarding script ready (`setup_usb_forwarding.ps1`)

## Next Steps (to complete the setup)

### Step 1: Forward USB Device from Windows to WSL

**In Windows (as Administrator):**

1. Open PowerShell as Administrator
2. Navigate to your project directory
3. Run the setup script:
   ```powershell
   .\setup_usb_forwarding.ps1
   ```

**OR manually:**

1. Install usbipd-win:
   ```powershell
   winget install usbipd
   ```

2. List USB devices:
   ```powershell
   usbipd list
   ```

3. Find your micropump (look for VID 0403, should be FTDI device)

4. Bind and attach the device (replace X-X with actual bus ID):
   ```powershell
   usbipd bind --busid X-X
   usbipd attach --wsl --busid X-X
   ```

### Step 2: Verify Connection in WSL

**In WSL/Ubuntu:**

1. Check if device is visible:
   ```bash
   lsusb | grep 0403
   ```

2. Run the connection test:
   ```bash
   conda activate pump-ctrl
   python test_connection.py
   ```

### Step 3: Test Micropump Control

Once the device is detected, you can test the pump:

```python
from src.controllers.pump_control import UsbPumpController

# Connect to the pump
pump = UsbPumpController()

# Set parameters
pump.set_frequency(50)  # 50 Hz
pump.set_amplitude(100) # Amplitude 100
pump.set_waveform("SINE")

# Run for 5 seconds
pump.pulse(5.0)

# Or manual control
pump.start()
# ... do something ...
pump.stop()
```

## Troubleshooting

### If the device is not found:

1. **Check physical connection:**
   - USB cable connected
   - Micropump powered on
   - Try different USB port

2. **Check Windows Device Manager:**
   - Device should appear as FTDI device
   - Install FTDI drivers if needed (see `hardware/drivers/` folder)

3. **WSL USB forwarding issues:**
   - Make sure WSL is running when attaching
   - Try detaching and reattaching:
     ```powershell
     usbipd detach --busid X-X
     usbipd attach --wsl --busid X-X
     ```

### If device found but connection fails:

1. **Permission issues:**
   ```bash
   sudo chmod 666 /dev/bus/usb/*/*  # Temporary fix
   ```

2. **Device in use:**
   - Close any other programs using the device
   - Restart WSL

3. **Driver issues:**
   - Check if the device needs specific drivers
   - Try different VID/PID if your device uses different IDs

## Files Overview

- `test_connection.py` - Connection diagnostic tool
- `setup_usb_forwarding.ps1` - Windows USB forwarding script
- `src/controllers/pump_control.py` - Main pump controller
- `environment.yml` - Conda environment with all dependencies
- `/etc/udev/rules.d/99-micropump.rules` - USB permissions rule

## Environment Details

- **Environment:** `pump-ctrl` (Conda)
- **Python:** 3.12.11
- **Key Libraries:** usbx, pyusb, pyserial
- **USB Libraries:** libusb-1.0-0-dev, libudev-dev
- **Permissions:** User in dialout group, udev rules configured
