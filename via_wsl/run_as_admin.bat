@echo off
cd /d "%~dp0"

REM Check if a Python script was provided as argument
if "%1"=="" (
    echo Usage: run_as_admin.bat ^<python_script^> [script_arguments...]
    echo.
    echo Examples:
    echo   run_as_admin.bat attach_micropump.py --distro Ubuntu
    echo   run_as_admin.bat detach_micropump.py --dry-run
    echo   run_as_admin.bat attach_micropump.py
    echo.
    pause
    goto :eof
)

REM Check if the specified Python script exists
if not exist "%1" (
    echo Error: Python script "%1" not found in current directory.
    echo Current directory: %CD%
    echo.
    dir *.py
    echo.
    pause
    goto :eof
)

REM Run the Python script with all arguments
echo Running: python %*
python %*

REM Show results and pause so user can see output
echo.
echo Script execution completed.
echo Exit Code: %ERRORLEVEL%
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo *** ERROR DETECTED ***
    echo The script exited with error code: %ERRORLEVEL%
    echo Please review the output above for error details.
    echo.
) else (
    echo.
    echo *** SUCCESS ***
    echo Script completed successfully.
    echo.
)

echo Window will close in 2 seconds...
timeout /t 2 /nobreak >nul 2>&1