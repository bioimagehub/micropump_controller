@echo off
REM =====================================================
REM AUTOMATIC BARTELS PUMP DRIVER INSTALLER
REM Uses Windows Startup Settings Option 7 bypass
REM =====================================================

echo ========================================
echo BARTELS PUMP DRIVER INSTALLER
echo ========================================
echo.
echo This will install unsigned Bartels pump drivers
echo using Windows built-in Startup Settings bypass.
echo.
echo NO BIOS CHANGES REQUIRED!
echo Maximum complexity: GUI navigation + clicking OK
echo.

REM Check if running as administrator
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo Requesting administrator privileges...
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

echo [ADMIN] Running with administrator privileges
echo.

REM Find the INF files
set "INF_DIR=%~dp0delete\legacy\temp_extract"
set "FTDIBUS_INF=%INF_DIR%\ftdibus.inf"
set "FTDIPORT_INF=%INF_DIR%\ftdiport.inf"

if not exist "%FTDIBUS_INF%" (
    echo ERROR: ftdibus.inf not found at %FTDIBUS_INF%
    echo Please ensure this script is in the micropump_controller root directory
    pause
    exit /b 1
)

echo [STEP 1] Setting up automated installer task...

REM Create the Stage 2 installer script
set "STAGE2_DIR=%ProgramData%\BartelsInstaller"
set "STAGE2_SCRIPT=%STAGE2_DIR%\install_drivers.cmd"

if not exist "%STAGE2_DIR%" mkdir "%STAGE2_DIR%"

> "%STAGE2_SCRIPT%" (
    echo @echo off
    echo echo [STAGE2] Installing Bartels pump drivers...
    echo pnputil /add-driver "%FTDIBUS_INF%" /install
    echo pnputil /add-driver "%FTDIPORT_INF%" /install
    echo echo [STAGE2] Driver installation complete!
    echo echo [STAGE2] Cleaning up task...
    echo schtasks /Delete /TN "InstallBartelsDrivers" /F
    echo echo [STAGE2] Pump should now be available as COM port
    echo pause
)

echo [STEP 2] Creating startup task...
schtasks /Create /TN "InstallBartelsDrivers" /SC ONSTART /RL HIGHEST /RU "SYSTEM" /TR "cmd.exe /c \"%STAGE2_SCRIPT%\"" /F

if %errorlevel% neq 0 (
    echo ERROR: Failed to create startup task
    pause
    exit /b 1
)

echo [STEP 3] Task created successfully!
echo.
echo ========================================
echo NEXT: ACCESS STARTUP SETTINGS
echo ========================================
echo.
echo I will now guide you to Windows Startup Settings.
echo This is a BUILT-IN Windows feature - no BIOS required!
echo.
echo When the blue Startup Settings screen appears:
echo   Press 7 - "Disable driver signature enforcement"
echo.
echo After Windows starts, drivers will install automatically.
echo.
echo Press any key to open Windows Recovery...
pause

echo [LAUNCHING] Opening Windows Recovery Environment...
shutdown /r /o /t 5 /c "Opening Startup Settings for driver installation. Press 7 when prompted."

echo.
echo Recovery boot initiated.
echo When Windows restarts, look for the blue Startup Settings screen.
echo Press 7 for "Disable driver signature enforcement"
echo.
echo After installation, your pump will be available as a COM port!