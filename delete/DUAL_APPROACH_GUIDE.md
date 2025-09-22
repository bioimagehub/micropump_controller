# Dual Approach Setup Guide for Bartels Micropump

This project supports a **dual approach** to handle different user scenarios:

1. **Windows Users with Driver Installation Access** → Direct USB
2. **Windows Users without Driver Installation Access** → WSL + Serial
3. **Linux Users** → Native Serial/USB

## Environment Setup

Your environment is already configured with all necessary libraries:

```yaml
# environment.yml includes:
- usbx      # For direct USB communication (Windows)
- pyserial  # For serial communication (Linux/WSL)
- pyusb     # Alternative USB library
```

## Usage Examples

### Basic Usage (Platform Agnostic)

```python
from src.controllers.pump_control import UsbPumpController

# Auto-detects best connection method
pump = UsbPumpController()

# Use the pump
pump.set_frequency(50)    # 50 Hz
pump.set_amplitude(100)   # Amplitude 100
pump.set_waveform("SINE") # Sine wave
pump.pulse(5.0)          # Run for 5 seconds
```

### Advanced Usage (Force Connection Method)

```python
# Force USB connection (Windows with drivers)
pump = UsbPumpController(connection_method="usb_only")

# Force serial connection (Linux/WSL)
pump = UsbPumpController(connection_method="serial_only")

# Specify exact serial port
pump = UsbPumpController(port="COM3")  # Windows
pump = UsbPumpController(port="/dev/ttyUSB0")  # Linux
```

## Platform-Specific Setup

### Windows (with Admin Rights) - USB Method

✅ **Recommended for Windows users who can install drivers**

1. **Install FTDI VCP Drivers:**
   ```
   Download from: https://ftdichip.com/drivers/vcp-drivers/
   Or use the drivers in: hardware/drivers/
   ```

2. **Test Connection:**
   ```bash
   conda activate pump-ctrl
   python test_dual_approach.py
   ```

3. **Verify in Device Manager:**
   - Device should appear as "USB Serial Port (COMx)"
   - Note the COM port number

### Windows (without Admin Rights) - WSL Method

✅ **Recommended for Windows users with BIOS restrictions**

1. **Install WSL:**
   ```powershell
   wsl --install
   ```

2. **Set up USB forwarding:**
   ```powershell
   # As Administrator
   winget install usbipd
   usbipd list
   usbipd bind --busid X-X
   usbipd attach --wsl --busid X-X
   ```

3. **In WSL:**
   ```bash
   # Clone project and setup environment
   git clone <repo_url>
   cd micropump_controller
   conda env create -f environment.yml
   conda activate pump-ctrl
   
   # Force Linux driver recognition
   sudo ./force_ftdi_recognition.sh
   
   # Test connection
   python test_dual_approach.py
   ```

### Linux (Native) - Serial Method

✅ **Best performance and reliability**

1. **Install dependencies:**
   ```bash
   sudo apt update
   sudo apt install libusb-1.0-0-dev libudev-dev
   ```

2. **Set up environment:**
   ```bash
   conda env create -f environment.yml
   conda activate pump-ctrl
   ```

3. **Configure permissions:**
   ```bash
   sudo usermod -a -G dialout $USER
   sudo udevadm control --reload-rules
   # Logout and login again
   ```

4. **Test connection:**
   ```bash
   python test_dual_approach.py
   ```

## Testing Scripts

| Script | Purpose |
|--------|---------|
| `test_dual_approach.py` | Main test for dual approach |
| `test_connection.py` | Original connection test |
| `test_linux_direct.py` | Linux-specific testing |
| `force_ftdi_recognition.sh` | Force Linux driver recognition |

## Troubleshooting

### Windows USB Issues
```bash
# Check Device Manager for:
# - Unknown devices
# - Devices with yellow warning icons
# - FTDI devices

# Try installing unsigned drivers:
# 1. Download Zadig (hardware/external_software/libusb/win/)
# 2. Replace driver with WinUSB or libusb
```

### WSL USB Issues
```bash
# In Windows PowerShell (as Admin):
usbipd list                    # Check device visibility
usbipd detach --busid X-X      # Detach if stuck
usbipd attach --wsl --busid X-X # Reattach

# In WSL:
lsusb | grep 0403              # Check device visibility
dmesg | tail -20               # Check kernel messages
```

### Linux USB Issues
```bash
# Check device detection:
lsusb | grep 0403
ls -la /dev/ttyUSB*

# Fix permissions:
sudo chmod 666 /dev/ttyUSB*
sudo usermod -a -G dialout $USER

# Force driver binding:
sudo ./force_ftdi_recognition.sh
```

## Hardware Requirements

- **Bartels mp-x Micropump Controller**
- **USB Cable** (A to B or A to Mini-B, depending on controller model)
- **Power Supply** for the pump controller (if not USB-powered)

## Expected Device IDs

- **Vendor ID (VID):** 0x0403 (FTDI)
- **Product ID (PID):** 0xB4C0 (Default for Bartels)
- **Note:** Your device might have a different PID

## Connection Flow

```
Start
  ↓
Platform Detection
  ↓
Windows? → Try USB → Success? → Use USB
  ↓           ↓         No
  No       Try Serial → Success? → Use Serial
  ↓                       ↓
Linux?                  Error
  ↓
Try Serial → Success? → Use Serial
  ↓           ↓
              No
           Try USB → Success? → Use USB
                        ↓
                      Error
```

## Performance Comparison

| Method | Platform | Speed | Reliability | Setup Complexity |
|--------|----------|-------|-------------|------------------|
| USB Direct | Windows | Fast | High | Medium (drivers) |
| Serial | Linux | Medium | Very High | Low |
| Serial via WSL | Windows | Medium | High | High (forwarding) |

The controller automatically chooses the best available method for your platform!
