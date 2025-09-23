# Micropump Test Signal Scripts

This directory contains scripts for testing the Bartels micropump in WSL environment.

## Scripts Created

### 1. `test_micropump_signal.py` - Comprehensive Test Script
A full-featured script that:
- Checks if WSL distribution exists
- Detects if micropump is available in WSL
- Automatically attaches micropump using `attach_micropump.py` if needed
- Handles permission setup
- Sends configurable test signals

**Usage:**
```bash
python test_micropump_signal.py [options]

Options:
  --distro DISTRO       WSL distro name (default: Ubuntu)
  --duration DURATION   Test pulse duration in seconds (default: 1.0)
  --frequency FREQUENCY Frequency in Hz (default: 100)
  --voltage VOLTAGE     Voltage in Vpp (default: 100)
  --waveform WAVEFORM   Waveform type (default: RECT)
  --force-attach        Force reattachment even if devices are found
  --skip-attach         Skip attachment step and assume device is ready
```

### 2. `simple_test.py` - Direct Test Script
A simplified script that directly tests the micropump without complex setup:
- Assumes micropump is already attached to WSL
- Focuses purely on sending test signals
- Minimal dependencies and setup

**Usage:**
```bash
python simple_test.py [options]

Options:
  --distro DISTRO       WSL distro (default: Ubuntu)
  --duration DURATION   Duration in seconds (default: 1.0)
  --frequency FREQUENCY Frequency in Hz (default: 100)
  --voltage VOLTAGE     Voltage in Vpp (default: 100)
  --waveform WAVEFORM   Waveform type (default: RECT)
```

## Test Examples

### Basic Test (as requested)
```bash
# 1 second, 100Hz, 100Vpp, rectangular waveform
python simple_test.py --duration 1.0 --frequency 100 --voltage 100 --waveform RECT
```

### Custom Tests
```bash
# Short pulse test
python simple_test.py --duration 0.5 --frequency 200 --voltage 150 --waveform SINE

# Low power test
python simple_test.py --duration 2.0 --frequency 50 --voltage 75 --waveform RECT
```

## Integration with Existing Scripts

The test scripts integrate with:
- `attach_micropump.py` - For automatic device attachment
- `detach_micropump.py` - For cleanup
- `../src/pump.py` - Uses the same command protocol

## Test Results

✅ Successfully tested:
- Basic connection to micropump via WSL
- Command sending (frequency, voltage, waveform)
- Start/stop control
- Variable duration pulses
- Different waveform types (RECT, SINE)
- Different frequencies and voltages

The micropump responds correctly to:
- `F{freq}` - Set frequency (1-300 Hz)
- `A{voltage}` - Set voltage (1-250 Vpp)
- `MR` - Set rectangular waveform
- `MS` - Set sine waveform
- `bon` - Start pump
- `boff` - Stop pump

## Notes

- The micropump uses XON/XOFF flow control
- Commands are terminated with carriage return (`\r`)
- Brief delays (0.15s) are needed between commands
- Serial port auto-detection works for `/dev/ttyUSB*` and `/dev/ttyACM*`
- The pump is detected as "Future Technology Devices International, Ltd USB Micropump Control" (VID:PID 0403:b4c0)