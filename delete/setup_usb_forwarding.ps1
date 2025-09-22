# PowerShell script to setup USB forwarding for Bartels micropump
# Run this in PowerShell as Administrator on Windows

Write-Host "Bartels Micropump USB Forwarding Setup" -ForegroundColor Green
Write-Host "======================================" -ForegroundColor Green

# Check if usbipd is installed
try {
    $usbipd_version = usbipd --version
    Write-Host "✓ usbipd-win is installed: $usbipd_version" -ForegroundColor Green
} catch {
    Write-Host "✗ usbipd-win is not installed!" -ForegroundColor Red
    Write-Host "Please download and install from: https://github.com/dorssel/usbipd-win/releases" -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "Scanning for USB devices..." -ForegroundColor Yellow
$devices = usbipd wsl list

Write-Host "Available USB devices:"
Write-Host $devices

# Look for Bartels micropump (VID:PID 0403:B4C0)
$bartels_device = $devices | Select-String -Pattern "0403:b4c0"

if ($bartels_device) {
    Write-Host "✓ Bartels micropump found!" -ForegroundColor Green
    
    # Extract the BUSID from the line
    $busid = ($bartels_device -split '\s+')[0]
    Write-Host "Device BUSID: $busid" -ForegroundColor Cyan
    
    Write-Host ""
    Write-Host "Setting up USB forwarding..." -ForegroundColor Yellow
    
    # Bind the device
    try {
        usbipd wsl bind --busid $busid
        Write-Host "✓ Device bound successfully" -ForegroundColor Green
    } catch {
        Write-Host "Warning: Device might already be bound" -ForegroundColor Yellow
    }
    
    # Attach the device to WSL
    try {
        usbipd wsl attach --busid $busid --auto-attach
        Write-Host "✓ Device attached to WSL with auto-attach" -ForegroundColor Green
        Write-Host "The device will automatically attach when WSL starts" -ForegroundColor Cyan
    } catch {
        Write-Host "✗ Failed to attach device" -ForegroundColor Red
        Write-Host "Try manually: usbipd wsl attach --busid $busid" -ForegroundColor Yellow
    }
    
} else {
    Write-Host "✗ Bartels micropump (VID:PID 0403:B4C0) not found" -ForegroundColor Red
    Write-Host "Make sure the device is:" -ForegroundColor Yellow
    Write-Host "  - Connected to USB port" -ForegroundColor Yellow
    Write-Host "  - Powered on" -ForegroundColor Yellow
    Write-Host "  - Recognized by Windows (check Device Manager)" -ForegroundColor Yellow
    
    # Check for any FTDI devices
    $ftdi_devices = $devices | Select-String -Pattern "0403:"
    if ($ftdi_devices) {
        Write-Host ""
        Write-Host "Found other FTDI devices:" -ForegroundColor Cyan
        $ftdi_devices | ForEach-Object { Write-Host "  $_" -ForegroundColor Cyan }
        Write-Host "Check if any of these is your micropump with different PID" -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "Next steps:" -ForegroundColor Green
Write-Host "1. Go back to your WSL terminal" -ForegroundColor White
Write-Host "2. Run: lsusb" -ForegroundColor White
Write-Host "3. Run: python test_connection.py" -ForegroundColor White

Read-Host "Press Enter to exit"
