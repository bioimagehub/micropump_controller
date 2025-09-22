#!/bin/bash
# Force FTDI device recognition script for Linux
# Run this if your device appears in lsusb but no ttyUSB device is created

echo "FTDI Device Force Recognition Script"
echo "===================================="

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "This script needs to be run as root (use sudo)"
    exit 1
fi

echo "1. Loading FTDI modules..."
modprobe ftdi_sio
modprobe usbserial
echo "   ✓ Modules loaded"

echo ""
echo "2. Current USB devices:"
lsusb | grep -i "0403\|ftdi" || echo "   No FTDI devices found"

echo ""
echo "3. Forcing FTDI device recognition..."

# Try to add the standard Bartels pump VID/PID
echo "0403 b4c0" > /sys/bus/usb-serial/drivers/ftdi_sio/new_id 2>/dev/null && echo "   ✓ Added 0403:b4c0 to ftdi_sio" || echo "   ! Could not add to ftdi_sio"

# Also try generic USB serial
echo "0403 b4c0" > /sys/bus/usb-serial/drivers/generic/new_id 2>/dev/null && echo "   ✓ Added 0403:b4c0 to generic" || echo "   ! Could not add to generic"

# Try other common FTDI PIDs
for pid in "6001" "6010" "6011" "6014" "6015"; do
    echo "0403 $pid" > /sys/bus/usb-serial/drivers/ftdi_sio/new_id 2>/dev/null && echo "   ✓ Added 0403:$pid to ftdi_sio"
done

echo ""
echo "4. Checking for new serial devices..."
sleep 2
ls -la /dev/ttyUSB* 2>/dev/null || echo "   No ttyUSB devices found"
ls -la /dev/ttyACM* 2>/dev/null || echo "   No ttyACM devices found"

echo ""
echo "5. Setting permissions for serial devices..."
chmod 666 /dev/ttyUSB* 2>/dev/null && echo "   ✓ Set permissions for ttyUSB devices"
chmod 666 /dev/ttyACM* 2>/dev/null && echo "   ✓ Set permissions for ttyACM devices"

echo ""
echo "6. Recent kernel messages (USB related):"
dmesg | tail -10 | grep -i "usb\|tty\|ftdi" || echo "   No recent USB messages"

echo ""
echo "Script complete. Try running 'python test_linux_direct.py' now."
