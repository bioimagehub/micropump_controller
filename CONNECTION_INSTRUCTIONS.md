# How to Connect Your Bartels Micropump for Testing

Your dual approach pump controller is ready! However, I don't see the pump device connected. Here's how to get it working:

## If you're in WSL (like right now):

### Step 1: Connect pump in Windows
1. **Physically connect** the Bartels micropump to your Windows machine via USB
2. **Open PowerShell as Administrator** in Windows

### Step 2: List devices and forward to WSL
```powershell
# List all USB devices
usbipd list

# Look for your pump device (likely FTDI or Bartels)
# It might show as "Unknown Device" or have VID 0403

# Bind the device (replace X-X with actual bus ID)
usbipd bind --busid X-X

# Attach to WSL (replace X-X with actual bus ID)  
usbipd attach --wsl --busid X-X
```

### Step 3: Verify in WSL
```bash
# In your WSL terminal:
lsusb | grep 0403              # Should show the pump
ls -la /dev/ttyUSB*            # Should show serial device

# Then run the test:
conda activate pump-ctrl
python test_pulse.py
```

## If you're on native Linux:

### Step 1: Connect and verify
```bash
# Connect pump via USB
lsusb | grep 0403              # Should show device

# Check for serial device
ls -la /dev/ttyUSB*

# Fix permissions if needed
sudo chmod 666 /dev/ttyUSB*
sudo usermod -a -G dialout $USER
```

### Step 2: Force driver recognition (if needed)
```bash
sudo ./force_ftdi_recognition.sh
```

### Step 3: Test
```bash
conda activate pump-ctrl
python test_pulse.py
```

## If you're on Windows with drivers:

### Step 1: Install FTDI VCP Drivers
- Download from: https://ftdichip.com/drivers/vcp-drivers/
- Or use drivers in `hardware/drivers/`
- Device should appear as "USB Serial Port (COMx)" in Device Manager

### Step 2: Test
```bash
conda activate pump-ctrl
python test_pulse.py
```

## Troubleshooting:

### The device doesn't appear in `lsusb`:
- Check physical USB connection
- Try different USB port
- In WSL: Make sure device is attached with `usbipd attach --wsl --busid X-X`

### Permission denied errors:
```bash
sudo usermod -a -G dialout $USER
# Then logout and login again
```

### Different device ID:
If your pump has different VID/PID, create a `.env` file:
```bash
echo "PUMP_VID=0x0403" > .env
echo "PUMP_PID=0xYOUR_PID" >> .env
```

Once the pump is connected and showing up in `lsusb` or as a `/dev/ttyUSB*` device, the test script will work!
