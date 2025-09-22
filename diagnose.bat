@echo off
echo === Diagnostic Test Sequence ===
echo.

echo 1. Checking current device status...
powershell -Command "Get-PnpDevice | Where-Object {$_.FriendlyName -like '*Micropump*'} | Format-Table FriendlyName, Status, ProblemCode"

echo.
echo 2. Checking for driver conflicts...
powershell -Command "Get-PnpDevice | Where-Object {$_.HardwareID -like '*0403:B4C0*'} | Format-List"

echo.
echo 3. Testing basic Windows serial communication...
powershell -Command "try { $port = new-Object System.IO.Ports.SerialPort COM4,9600,None,8,one; $port.Open(); Write-Host 'Windows serial: SUCCESS'; $port.Close() } catch { Write-Host 'Windows serial: FAILED -' $_.Exception.Message }"

echo.
echo === Diagnostic Complete ===
echo.
echo Please check if:
echo - The pump has a power LED that's on
echo - The USB cable is securely connected
echo - You're using the original USB cable
echo.
pause
