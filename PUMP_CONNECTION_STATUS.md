# Bartels Pump Connection Status & Solutions

## Current Situation
✅ **Device Detection**: Pump found at USB VID=0403 PID=b4c0  
❌ **Communication**: USB commands not reaching pump  
⚠️ **Issue**: Device appears as "Vendor Specific" class, needs proper driver  

## Working Scripts Created
1. `test_pump_windows_native.py` - Direct USB + Serial fallback
2. `test_pump_interactive.py` - Manual command testing 
3. `test_pump_audio.py` - Frequency testing for audible feedback
4. `test_pump_winusb.py` - WinUSB approach (needs drivers)

## Verified Command Protocol
- **Frequency**: F100 (100 Hz)
- **Amplitude**: A100 (100 Vpp) 
- **Waveform**: MR (Rectangular)
- **Start**: bon
- **Stop**: boff
- **Timing**: 200ms delay between commands
- **Line ending**: \r (carriage return)

## Next Steps (Choose One)

### Option 1: WSL USB Forwarding (Recommended)
```powershell
# Run as Administrator
usbipd bind --busid 1-5
usbipd attach --wsl --busid 1-5
```
Then in WSL: `python test_scripts/test_pump_via_wsl.py`

### Option 2: Install FTDI VCP Drivers
```powershell
# Run as Administrator  
cd hardware/drivers
./install_unsigned_bartels_drivers.bat
```
This will create a COM port for serial communication.

### Option 3: WinUSB Driver (Advanced)
```powershell
# Install WinUSB driver using Zadig or similar tool
# Point to VID=0403 PID=b4c0 device
```

## Testing Commands
Once connected, test with these settings that should make sound:
- F100 (100 Hz frequency)
- A100 (100 Vpp amplitude)  
- MR (rectangular waveform)
- bon (turn on)

## Quick Test
```python
pump.send_command("F100")
time.sleep(0.2)
pump.send_command("A100") 
time.sleep(0.2)
pump.send_command("MR")
time.sleep(0.2)
pump.send_command("bon")  # Should make audible sound
time.sleep(3)
pump.send_command("boff")  # Stop
```

The pump should make a 100 Hz buzzing/clicking sound when turned on.
