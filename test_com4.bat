@echo off
echo Testing Bartels pump on COM4...
echo.

REM Test 1: Check if COM4 exists
python -c "import serial.tools.list_ports; ports = list(serial.tools.list_ports.comports()); print('Available ports:'); [print(f'  {p.device}: {p.description}') for p in ports]; com4_found = any('COM4' in p.device for p in ports); print(f'COM4 found: {com4_found}')"

echo.
echo Testing pybartelslabtronix connection...

REM Test 2: Try to connect to COM4
python -c "from pybartelslabtronix import BartelsLabtronix; print('Connecting to COM4...'); blt = BartelsLabtronix(port='COM4'); print('SUCCESS: Connected!'); print('Testing basic operations...'); blt.setfrequency(50); print('Set frequency to 50 Hz'); blt.setamplitude(100); print('Set amplitude to 100V'); print('Connection test complete.'); blt.ser.close() if hasattr(blt, 'ser') else None"

echo.
echo Test completed!
pause
