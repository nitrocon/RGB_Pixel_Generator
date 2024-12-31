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

REM Verify if Python is installed
echo !COLOR_BLUE!Checking if Python is installed...
python --version >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo !COLOR_RED!ERROR: Python is not installed or not in the system PATH.
    echo Please install Python and ensure it is added to your PATH.
    pause
    exit /b 1
)
echo !COLOR_GREEN!Python found successfully.

REM Create a virtual environment
echo !COLOR_YELLOW!====================================================
echo Step 1: Creating virtual environment...
echo ====================================================
C:/Users/offic/AppData/Local/Programs/Python/Python312/python.exe -m venv venv
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

REM Display the Python version in the activated environment
echo !COLOR_BLUE!Python version in the virtual environment:
python --version

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
