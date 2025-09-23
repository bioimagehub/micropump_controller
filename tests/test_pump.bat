@echo off
cd /d "%~dp0"

echo.
echo ========================================
echo   Simple Micropump Test Launcher
echo ========================================
echo.
echo This will test the micropump signal.
echo If it fails, it will automatically run 
echo the admin setup to attach the device.
echo.

REM Run the test script
python test_micropump_signal.py %*

echo.
echo ========================================
echo Test completed. Press any key to exit.
pause > nul