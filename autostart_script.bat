@echo off
REM Batch Script for Running Python Script in Virtual Environment
REM =====================================================

REM Set colors for different statuses
setlocal enabledelayedexpansion
set COLOR_RESET=^[[0m
set COLOR_GREEN=^[[32m
set COLOR_RED=^[[31m
set COLOR_YELLOW=^[[33m
set COLOR_CYAN=^[[36m
set COLOR_BLUE=^[[34m

echo !COLOR_CYAN!=====================================================
echo Welcome to the Project Runner!
echo =====================================================

REM Verify if Python 3.10 is installed
echo !COLOR_BLUE!Checking if Python 3.10 is installed...

python --version >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo !COLOR_RED!ERROR: Python is not installed or not in the system PATH.
    echo Trying to install Python 3.10...

    REM Download Python 3.10 installer (Windows x64 executable)
    set PYTHON_INSTALLER=https://www.python.org/ftp/python/3.10.10/python-3.10.10-amd64.exe
    set INSTALLER_PATH=%TEMP%\python_installer.exe

    REM Download the installer using PowerShell 
    powershell -Command "Invoke-WebRequest -Uri '%PYTHON_INSTALLER%' -OutFile '%INSTALLER_PATH%'"

    REM Install Python 3.10 silently and add to PATH
    "%INSTALLER_PATH%" /quiet InstallAllUsers=1 PrependPath=1

    REM Clean up the installer
    del "%INSTALLER_PATH%"

    REM Verify Python installation
    python --version >nul 2>nul
    if %ERRORLEVEL% NEQ 0 (
        echo !COLOR_RED!ERROR: Python 3.10 installation failed.
        pause
        exit /b 1
    )
    echo !COLOR_GREEN!Python 3.10 installed successfully.
) else (
    echo !COLOR_GREEN!Python found successfully.
)

REM Create a virtual environment
echo !COLOR_YELLOW!====================================================
echo Step 1: Creating virtual environment...
echo ====================================================
python -m venv venv
if %ERRORLEVEL% NEQ 0 (
    echo !COLOR_RED!ERROR: Failed to create virtual environment.
    pause
    exit /b 1
)
echo !COLOR_GREEN!Virtual environment created successfully.

REM Activate the virtual environment
echo !COLOR_YELLOW!====================================================
echo Step 2: Activating virtual environment...
echo ====================================================
call venv\Scripts\activate
if %ERRORLEVEL% NEQ 0 (
    echo !COLOR_RED!ERROR: Failed to activate virtual environment.
    pause
    exit /b 1
)
echo !COLOR_GREEN!Virtual environment activated.

REM Check if pip is installed in the virtual environment
echo !COLOR_BLUE!Checking if pip is installed in the virtual environment...
python -m pip --version >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo !COLOR_RED!ERROR: pip not found in the virtual environment. Installing pip...
    python -m ensurepip --upgrade
    if %ERRORLEVEL% NEQ 0 (
        echo !COLOR_RED!ERROR: Failed to install pip in the virtual environment.
        pause
        exit /b 1
    )
    echo !COLOR_GREEN!pip installed successfully in the virtual environment.
) else (
    echo !COLOR_GREEN!pip is already installed in the virtual environment.
)

REM Install dependencies (check if requirements.txt exists)
echo !COLOR_YELLOW!====================================================
echo Step 3: Installing dependencies...
echo ====================================================
if exist "requirements.txt" (
    echo !COLOR_BLUE!Found requirements.txt. Installing dependencies...
    pip install -r requirements.txt --extra-index-url https://download.pytorch.org/whl/cu113
    if %ERRORLEVEL% NEQ 0 (
        echo !COLOR_RED!ERROR: Failed to install dependencies from requirements.txt.
        pause
        exit /b 1
    )
    echo !COLOR_GREEN!Dependencies installed successfully.
) else (
    echo !COLOR_RED!ERROR: requirements.txt not found. Cannot proceed with dependency installation.
    pause
    exit /b 1
)

REM Run the generator.py script
echo !COLOR_YELLOW!====================================================
echo Step 6: Running generator.py script...
echo ====================================================
python generator.py
if %ERRORLEVEL% NEQ 0 (
    echo !COLOR_RED!ERROR: Failed to run generator.py script.
    pause
    exit /b 1
)
echo !COLOR_GREEN!generator.py script ran successfully.

REM Final message
echo !COLOR_YELLOW!====================================================
echo All tasks completed! The batch script will now close.
echo =====================================================
pause
exit
