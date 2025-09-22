# Bartels Micropump Driver-Free Setup Instructions

## Quick Start for AI Models

**CRITICAL SUCCESS FACTOR:** XON/XOFF flow control in DCB structure

### Environment Requirements
- Windows 10/11
- Python 3.x (tested with 3.12)
- No external dependencies (uses built-in ctypes)

### Working Implementation
```python
# Use working_controller.py in this directory
from working_controller import BartelsDriverFreePumpController

controller = BartelsDriverFreePumpController("COM4", 9600)
controller.run_test_sequence()  # Will start pump and verify audio response
controller.close()
```

### Key Technical Points
1. **XON/XOFF Flow Control:** Essential for communication
2. **Command Termination:** Use `\r` (carriage return)
3. **Timing:** 150ms delays between commands
4. **Port Format:** `\\\\.\\COM4` for Windows API
5. **DCB Configuration:** fOutX=1, fInX=1, XonChar=0x11, XoffChar=0x13

### Validation
- Pump produces audible sound when started
- Commands return successful byte counts
- COM port shows as "USB Micropump Control"

### Common Failures
- Missing flow control → WriteFile succeeds but no pump response
- Wrong termination → Commands ignored
- Incorrect timing → Commands overlap/conflict

See `DRIVER_FREE_PROTOCOL_COMPLETE.md` for full technical documentation.